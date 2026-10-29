"""Render a vertical YouTube Short (1080x1920) from a _video_scripts/*.short.yml file.

    python scripts/video/render_short.py _video_scripts/<date>-<slug>.short.yml [--out DIR]

Writes <slug>.mp4 (voiceover, word-by-word captions, the channel's navy/green/red
look and the On Air Ireland end card) and <slug>.youtube.md (title, description,
tags and upload settings, ready to paste). Needs ffmpeg, the Inter fonts and the
voice files from scripts/video/fetch_assets.sh.
"""
import argparse
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import short_spec  # noqa: E402
import tts  # noqa: E402

W, H, FPS = 1080, 1920, 30
SR = tts.SR

NAVY_TOP = (13, 31, 56)
NAVY_BOT = (5, 12, 24)
GREEN = (34, 197, 94)
RED = (220, 38, 38)
WHITE = (255, 255, 255)
MUTED = (148, 163, 184)

FONT_DIRS = ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
             "/usr/share/fonts/opentype", "/usr/share/fonts", os.path.expanduser("~/.fonts")]
FALLBACK = {"InterDisplay-Black.otf": "Inter-Black.otf"}


def _font_path(name):
    for d in FONT_DIRS:
        for root, _, files in os.walk(d):
            if name in files:
                return os.path.join(root, name)
    if name in FALLBACK:
        return _font_path(FALLBACK[name])
    raise SystemExit(f"Font {name} not found. Install the Inter fonts (apt: fonts-inter).")


def F(name, size):
    return ImageFont.truetype(_font_path(name), size)


F_HEAD = F("InterDisplay-Black.otf", 118)
F_HEAD_S = F("InterDisplay-Black.otf", 96)
F_KICK = F("Inter-Bold.otf", 34)
F_SUB = F("Inter-Medium.otf", 46)
F_PILL = F("Inter-SemiBold.otf", 44)
F_BADGE = F("Inter-Black.otf", 40)
F_CAP = F("Inter-Bold.otf", 50)
F_TOP = F("Inter-Black.otf", 34)
F_TOP2 = F("Inter-Bold.otf", 30)

MARGIN = 84
TEXT_W = W - 2 * MARGIN


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def wrap(text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_img(text, font, fill):
    l, t, r, b = font.getbbox(text)
    im = Image.new("RGBA", (int(r - l) + 8, int(b - t) + 12), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=font, fill=fill)
    return im


def pill_img(text, font, fg, bg, outline=None, pad=(34, 18)):
    l, t, r, b = font.getbbox(text)
    w, h = int(r - l) + pad[0] * 2, int(b - t) + pad[1] * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg, outline=outline,
                        width=3 if outline else 0)
    d.text((pad[0] - l, pad[1] - t), text, font=font, fill=fg)
    return im


def paste_alpha(base, im, xy, alpha):
    if alpha <= 0:
        return
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(im, (int(xy[0]), int(xy[1])))


def make_bg():
    y = np.linspace(0, 1, H)[:, None]
    grad = np.array(NAVY_TOP) * (1 - y) + np.array(NAVY_BOT) * y
    arr = np.repeat(grad[:, None, :], W, axis=1).reshape(H, W, 3)
    yy, xx = np.mgrid[0:H, 0:W]
    g = np.exp(-(((xx - W * 0.5) / 620) ** 2 + ((yy - 820) / 700) ** 2))
    arr = arr + g[..., None] * np.array([10, 30, 40])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


BG = make_bg()


def draw_rings(img, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    cx, cy = W - 150, 300
    for k in range(6):
        ph = ((t * 0.35) + k / 6) % 1.0
        r = 80 + ph * 1100
        a = int(70 * (1 - ph) ** 1.5)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GREEN + (a,), width=3)
    img.alpha_composite(ov)


def draw_topbar(img, t, progress):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 10), fill=(255, 255, 255, 25))
    d.rectangle((0, 0, int(W * progress), 10), fill=GREEN + (255,))
    x, y = MARGIN, 120
    pill = pill_img("ON AIR", F_TOP, WHITE, RED, pad=(64, 16))
    img.alpha_composite(pill, (x, y))
    blink = 0.55 + 0.45 * math.cos(t * math.pi * 1.6)
    r = 10
    cy = y + pill.height // 2
    d.ellipse((x + 26 - r, cy - r, x + 26 + r, cy + r), fill=(255, 255, 255, int(255 * blink)))
    d.text((x + pill.width + 22, y + 13), "IRELAND", font=F_TOP2, fill=WHITE)


def draw_caption(img, text, words_t, t_local):
    """Two caption lines at a time, the word being spoken in green."""
    lines = wrap(text, F_CAP, TEXT_W)
    idx = sum(1 for s, e in words_t if t_local >= s) - 1
    word_line = []
    for li, ln in enumerate(lines):
        word_line += [li] * len(ln.split())
    cur_line = word_line[max(0, min(idx, len(word_line) - 1))]
    start_line = (cur_line // 2) * 2
    show = lines[start_line:start_line + 2]
    y0 = 1400
    plate_h = 40 + 74 * len(show)
    plate = Image.new("RGBA", (TEXT_W + 60, plate_h), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle((0, 0, plate.width - 1, plate_h - 1), radius=26,
                                            fill=(3, 8, 16, 170))
    img.alpha_composite(plate, (MARGIN - 30, y0 - 20))
    d = ImageDraw.Draw(img)
    wi = sum(len(ln.split()) for ln in lines[:start_line])
    for li, ln in enumerate(show):
        x = MARGIN
        for w in ln.split():
            col = GREEN if wi == idx else (WHITE if wi < idx else (200, 210, 222))
            d.text((x, y0 + li * 74), w, font=F_CAP, fill=col)
            x += F_CAP.getlength(w + " ")
            wi += 1


def word_times(text, dur):
    """Rough per-word timing, weighted by word length plus pauses at punctuation."""
    words = text.split()
    weights = np.array([len(w.strip(",.!?")) + 2 for w in words], dtype=float)
    pause = np.array([0.6 if w[-1] in ",.!?" else 0 for w in words])
    total = weights.sum() + pause.sum() * 4
    t, out = 0.05 * dur, []
    usable = dur * 0.93
    for w, p in zip(weights, pause):
        d = usable * w / total
        out.append((t, t + d))
        t += d + usable * p * 4 / total
    return out


def scene_layers(sc):
    head_font = F_HEAD if len(sc["head"]) <= 22 else F_HEAD_S
    items = []
    y = 560
    items.append((text_img(sc["kicker"].upper(), F_KICK, GREEN), MARGIN, y, 0.0))
    items.append((Image.new("RGBA", (90, 6), GREEN + (255,)), MARGIN, y + 56, 0.05))
    y += 100
    lines = wrap(sc["head"], head_font, TEXT_W)
    for i, ln in enumerate(lines):
        items.append((text_img(ln, head_font, WHITE), MARGIN - 4, y, 0.08 + i * 0.09))
        y += int(head_font.size * 1.08)
    d = 0.08 + len(lines) * 0.09
    if sc.get("badge"):
        y += 18
        b = pill_img(sc["badge"], F_BADGE, (5, 12, 24), GREEN, pad=(30, 14))
        items.append((b, MARGIN, y, d + 0.05))
        y += b.height + 10
        d += 0.1
    if sc.get("sub"):
        y += 22
        for ln in wrap(sc["sub"], F_SUB, TEXT_W):
            items.append((text_img(ln, F_SUB, MUTED), MARGIN, y, d + 0.08))
            y += 62
        d += 0.12
    if sc.get("pills"):
        y += 36
        x = MARGIN
        for i, p in enumerate(sc["pills"]):
            im = pill_img(str(p), F_PILL, WHITE, (34, 197, 94, 28), outline=GREEN + (200,))
            if x + im.width > W - MARGIN:
                x = MARGIN
                y += im.height + 22
            items.append((im, x, y, d + 0.15 + i * 0.13))
            x += im.width + 20
    if y > 1330:
        print(f"Warning: scene '{sc['head']}' runs into the captions (bottom at {y}px).")
    return items


def draw_items(img, items, t_local, dur):
    out_fade = 1 - ease_out((t_local - (dur - 0.22)) / 0.22) if t_local > dur - 0.22 else 1
    for im, x, y, delay in items:
        p = ease_out((t_local - delay) / 0.45)
        paste_alpha(img, im, (x, y + (1 - p) * 50), p * out_fade)


def logo_img(size=520):
    s = size / 800
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    for r, w, a in [(256, 3, 120), (214, 5, 255)]:
        r *= s
        d.ellipse((c - r, c - r, c + r, c + r), outline=GREEN + (a,), width=max(2, int(w * s * 1.4)),
                  fill=(8, 19, 30, 255) if a == 255 else None)
    for rad, wd, a in [(70, 6, 255), (110, 5, 175), (150, 4, 100)]:
        rr = rad * s
        cy = 300 * s
        d.arc((c - rr, cy - rr * 0.75, c + rr, cy + rr * 0.75), 205, 335, fill=GREEN + (a,),
              width=int(wd * s * 1.6))
    d.ellipse((c - 9 * s * 1.4, 285 * s - 9 * s * 1.4, c + 9 * s * 1.4, 285 * s + 9 * s * 1.4), fill=GREEN)
    d.rounded_rectangle((252 * s, 314 * s, 548 * s, 404 * s), radius=45 * s, fill=RED)
    d.text((c, 359 * s), "ON AIR", font=F("Inter-Black.otf", int(50 * s)), fill=WHITE, anchor="mm")
    d.line((308 * s, 432 * s, 492 * s, 432 * s), fill=GREEN + (160,), width=max(2, int(3 * s)))
    d.text((c, 478 * s), "IRELAND", font=F("Inter-Bold.otf", int(42 * s)), fill=WHITE, anchor="mm")
    return im


LOGO = logo_img()


def draw_end(img, t_local):
    p = ease_out(t_local / 0.6)
    paste_alpha(img, LOGO, ((W - LOGO.width) / 2, 470 + (1 - p) * 60), p)
    p2 = ease_out((t_local - 0.25) / 0.5)
    url = text_img("onairireland.ie", F("InterDisplay-Black.otf", 104), WHITE)
    paste_alpha(img, url, ((W - url.width) / 2, 1060 + (1 - p2) * 40), p2)
    p3 = ease_out((t_local - 0.45) / 0.5)
    tag = text_img("Ireland's guide to legal streaming", F_SUB, GREEN)
    paste_alpha(img, tag, ((W - tag.width) / 2, 1200 + (1 - p3) * 30), p3)


def make_audio(spec):
    clips, scene_durs = [], []
    lines = [sc["vo"] for sc in spec["scenes"]] + [spec["end_vo"]]
    for i, ln in enumerate(lines):
        a = tts.synth(ln)
        lead = int(0.35 * SR)
        tail = int((1.6 if i == len(lines) - 1 else 0.3) * SR)
        seg = np.concatenate([np.zeros(lead, np.float32), a, np.zeros(tail, np.float32)])
        clips.append(seg)
        scene_durs.append((len(seg) / SR, len(a) / SR))
    vo = np.concatenate(clips)
    vo = vo / max(1e-6, np.abs(vo).max()) * 0.89
    n = len(vo)
    tt = np.arange(n) / SR
    # quiet ambient bed under the voice
    bed = (np.sin(2 * np.pi * 110 * tt) + 0.6 * np.sin(2 * np.pi * 164.8 * tt)
           + 0.4 * np.sin(2 * np.pi * 220.5 * tt))
    bed *= (0.55 + 0.45 * np.sin(2 * np.pi * tt / 8)) * 0.012
    fade = np.minimum(1, np.minimum(tt / 1.0, (tt[-1] - tt) / 1.5))
    return np.clip(vo + bed * fade, -1, 1), scene_durs, lines


def write_wav(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


def render(spec_path, out_dir):
    spec = short_spec.load(spec_path)
    problems = short_spec.problems(spec)
    if problems:
        raise SystemExit(f"{spec_path}: " + "; ".join(problems))
    slug = os.path.basename(spec_path).replace(".short.yml", "")
    os.makedirs(out_dir, exist_ok=True)
    audio, durs, lines = make_audio(spec)
    wav = os.path.join(out_dir, f"{slug}.wav")
    write_wav(wav, audio)
    total = len(audio) / SR
    starts = np.cumsum([0] + [d for d, _ in durs])
    layers = [scene_layers(sc) for sc in spec["scenes"]]
    wtimes = [word_times(ln, sd) for ln, (_, sd) in zip(lines, durs)]
    mp4 = os.path.join(out_dir, f"{slug}.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4],
                          stdin=subprocess.PIPE)
    for f in range(int(math.ceil(total * FPS))):
        t = f / FPS
        si = min(int(np.searchsorted(starts, t, side="right") - 1), len(durs) - 1)
        tl = t - starts[si]
        img = BG.copy()
        draw_rings(img, t)
        draw_topbar(img, t, t / total)
        if si < len(layers):
            draw_items(img, layers[si], tl, durs[si][0])
        else:
            draw_end(img, tl)
        if not (si == len(layers) and tl > 0.35 + durs[si][1] + 0.2):
            draw_caption(img, lines[si], wtimes[si], tl - 0.35)
        ff.stdin.write(img.convert("RGB").tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed")
    os.remove(wav)
    md = os.path.join(out_dir, f"{slug}.youtube.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(short_spec.youtube_text(spec, total, starts))
    print(f"{mp4} ({total:.1f}s)")
    print(md)
    if tts.unknown_words:
        print("Spelled out letter by letter (add to FIXED in scripts/video/tts.py): "
              + ", ".join(sorted(set(tts.unknown_words))))
    return mp4, md


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="+")
    ap.add_argument("--out", default="video-out")
    args = ap.parse_args()
    for path in args.spec:
        render(path, args.out)
