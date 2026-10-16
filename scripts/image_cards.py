#!/usr/bin/env python3
"""On Air Ireland brand-card generator.

Builds an original, unique header image for a post from the site's own product
icons (assets/images/products/*.svg, pre-rendered to scripts/card_kit/icons/).
No stock photos, logos, watermarks or third-party artwork are involved.

For each post it writes three files into assets/images/posts/:
    <slug>-hero.jpg    1600x800   page hero (header.overlay_image)
    <slug>-teaser.jpg  600x400    archive / related-post cards (header.teaser)
    <slug>-og.jpg      1200x630   social share card (header.og_image)

Cards are deterministic for a given slug, and each one has a "fingerprint"
(layout + mirrored? + palette + icon set). make_card() refuses to reuse a
fingerprint already in the ledger, so two posts never get the same card.

Needs only Pillow. Re-render the icon PNGs with scripts/card_kit/render_icons.js.
"""
import hashlib
import os
import random
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "scripts", "card_kit")
ICON_DIR = os.path.join(KIT, "icons")
FONT_PATH = os.path.join(KIT, "fonts", "Inter-Bold.otf")
LOGO_PATH = os.path.join(ROOT, "assets", "images", "logo.png")
POSTS_IMG_DIR = os.path.join(ROOT, "assets", "images", "posts")

SIZES = {"hero": (1600, 800), "teaser": (600, 400), "og": (1200, 630)}

# Brand-navy family, nudged per category so a category page reads as a set
# without every card looking identical.
PALETTES = {
    "Streaming-Services": {"bg": ("#0f2036", "#0e4a6e"), "accent": "#38bdf8", "label": "Streaming Services"},
    "Devices":            {"bg": ("#10243a", "#0f5560"), "accent": "#2dd4bf", "label": "Devices"},
    "Installation-Guides": {"bg": ("#131f3a", "#26407a"), "accent": "#818cf8", "label": "Installation Guides"},
    "News":               {"bg": ("#1a2230", "#334155"), "accent": "#fbbf24", "label": "News"},
    "Reviews":            {"bg": ("#1e1b3a", "#4c2f7a"), "accent": "#c084fc", "label": "Reviews"},
    "Sports-Streaming":   {"bg": ("#0f2a22", "#0f5a3d"), "accent": "#4ade80", "label": "Sports Streaming"},
    "Troubleshooting":    {"bg": ("#2a1822", "#7a2e3a"), "accent": "#fb923c", "label": "Troubleshooting"},
    "Watch-Guides":       {"bg": ("#2a1631", "#6a2457"), "accent": "#f472b6", "label": "Watch Guides"},
}

# Which icons suit which words in a post title. Order matters little; score =
# number of keyword hits.
ICON_KEYWORDS = {
    "streaming-stick": ["fire tv", "firestick", "fire stick", "stick", "amazon", "alexa"],
    "streaming-stick-lite": ["lite", "stick", "budget", "cheap"],
    "streaming-stick-alt": ["roku", "stick"],
    "streaming-box": ["roku", "box", "ultra", "apple tv", "cube"],
    "streaming-pebble": ["google tv", "chromecast", "streamer", "android tv"],
    "smart-tv": ["tv", "smart tv", "samsung", "lg", "app", "apps", "player", "netflix", "disney", "prime", "apple tv"],
    "smart-tv-2": ["tv", "smart tv", "samsung", "lg", "screen", "app", "youtube"],
    "soundbar": ["sound", "audio", "soundbar", "speaker", "volume", "sync"],
    "soundbar-sub": ["sound", "audio", "soundbar", "bass"],
    "speaker": ["speaker", "audio", "music", "sound"],
    "smart-speaker": ["alexa", "echo", "voice", "smart speaker"],
    "set-top-box": ["saorview", "freeview", "set-top", "set top", "box", "vodafone", "eir", "sky stream", "virgin"],
    "satellite-receiver": ["satellite", "sky", "receiver", "dish"],
    "indoor-aerial": ["aerial", "antenna", "saorview", "freeview", "signal"],
    "outdoor-aerial": ["aerial", "antenna", "saorview", "roof", "signal"],
    "mesh-wifi": ["wifi", "wi-fi", "buffering", "broadband", "mesh", "router", "slow internet", "slow broadband", "lag", "dropping"],
    "mesh-wifi-3": ["wifi", "wi-fi", "mesh", "coverage", "broadband"],
    "wifi-extender": ["wifi", "wi-fi", "extender", "signal", "dropout", "drops", "buffering"],
    "powerline": ["powerline", "wifi", "ethernet", "broadband"],
    "travel-router": ["router", "travel", "portable", "hotel"],
    "ethernet-cable": ["ethernet", "cable", "wired", "router", "broadband", "buffering"],
    "ethernet-adapter": ["ethernet", "adapter", "wired"],
    "hdmi-cable": ["hdmi", "cable", "cables", "4k", "connect", "no signal"],
    "hdmi-adapter": ["hdmi", "adapter", "extender"],
    "hdmi-switch": ["hdmi", "switch", "ports", "inputs"],
    "universal-remote": ["remote", "pairing", "control", "not working", "unresponsive"],
    "remote-cover": ["remote", "cover"],
    "batteries": ["remote", "batteries", "battery"],
    "projector": ["projector", "cinema", "movie", "film", "big screen"],
    "headphones": ["headphones", "audio", "listen", "quiet", "night"],
    "guidebook": ["guide", "setup", "set up", "how to", "manual"],
    "wall-mount": ["wall", "mount", "bracket", "install", "mounting"],
    "cable-clips": ["cable", "tidy", "clips", "wiring"],
    "extension-lead": ["power", "lead", "surge", "extension"],
    "screen-cleaning": ["screen", "clean", "picture"],
}

# Sensible defaults when a title gives too few keyword hits.
CATEGORY_ICONS = {
    "Streaming-Services": ["smart-tv", "streaming-stick", "universal-remote", "streaming-box", "set-top-box", "smart-tv-2"],
    "Devices": ["streaming-stick", "streaming-box", "streaming-pebble", "smart-tv", "soundbar", "streaming-stick-alt"],
    "Installation-Guides": ["wall-mount", "hdmi-cable", "ethernet-cable", "mesh-wifi", "indoor-aerial", "set-top-box"],
    "News": ["smart-tv", "set-top-box", "universal-remote", "satellite-receiver", "streaming-stick", "smart-tv-2"],
    "Reviews": ["streaming-stick", "smart-tv", "soundbar", "headphones", "streaming-box", "streaming-pebble"],
    "Sports-Streaming": ["smart-tv", "soundbar", "outdoor-aerial", "satellite-receiver", "speaker", "projector"],
    "Troubleshooting": ["mesh-wifi", "ethernet-cable", "powerline", "wifi-extender", "hdmi-cable", "universal-remote"],
    "Watch-Guides": ["projector", "smart-tv", "headphones", "soundbar", "universal-remote", "speaker"],
}

# Tiles are 4:3. (cx, cy, w): centre as a fraction of the stage, width as a
# fraction of the stage width. A layout may be mirrored left-right.
LAYOUTS = {
    "trio":    [(0.17, 0.56, 0.30), (0.50, 0.44, 0.30), (0.83, 0.56, 0.30)],
    "duo":     [(0.28, 0.52, 0.44), (0.76, 0.44, 0.36)],
    "feature": [(0.29, 0.50, 0.52), (0.80, 0.27, 0.27), (0.80, 0.73, 0.27)],
    "stagger": [(0.16, 0.34, 0.27), (0.50, 0.60, 0.36), (0.84, 0.36, 0.27)],
    "wide":    [(0.50, 0.50, 0.50), (0.10, 0.66, 0.21), (0.90, 0.34, 0.21)],
}


def normalise_category(category: str) -> str:
    c = (category or "").strip().replace(" ", "-")
    return c if c in PALETTES else "Streaming-Services"


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _seed(*parts) -> int:
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:12], 16)


def available_icons():
    if not os.path.isdir(ICON_DIR):
        return []
    return sorted(f[:-4] for f in os.listdir(ICON_DIR) if f.endswith(".png"))


def _has_word(text: str, word: str) -> bool:
    """Whole-word (or whole-phrase) match, so 'slow' never matches 'Slow Horses'
    as a Wi-Fi hint and 'app' never matches 'Apple'."""
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None


def pick_icons(title: str, category: str, salt: int = 0, n: int = 3):
    """Choose n icons that fit the title, varied by salt. Relevant icons
    (keyword hits) come first; category defaults fill the rest."""
    have = set(available_icons())
    t = " " + re.sub(r"[^a-z0-9+ ]+", " ", (title or "").lower()) + " "
    scored = []
    for icon, words in ICON_KEYWORDS.items():
        if icon not in have:
            continue
        score = sum(1 for w in words if _has_word(t, w))
        if score:
            scored.append((score, icon))
    scored.sort(key=lambda x: (-x[0], x[1]))
    relevant = [i for _, i in scored][:6]
    defaults = [i for i in CATEGORY_ICONS[normalise_category(category)] if i in have]
    pool = relevant + [i for i in defaults if i not in relevant]
    rng = random.Random(_seed("icons", title, salt))
    # Keep the best-matching icon in play, shuffle the rest of the pool.
    chosen = []
    if relevant:
        chosen.append(relevant[0] if salt == 0 else rng.choice(relevant[:3]))
    rest = [i for i in pool if i not in chosen]
    rng.shuffle(rest)
    chosen += rest[: max(0, n - len(chosen))]
    return chosen[:n]


def fingerprint(layout: str, flip: bool, palette: str, icons) -> str:
    return "|".join([layout, "m" if flip else "s", palette, ",".join(sorted(icons))])


def _aa_mask(size, radius, scale=4):
    w, h = size
    m = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * scale - 1, h * scale - 1), radius=radius * scale, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def _gradient(size, c0, c1, angle="v"):
    w, h = size
    a, b = Image.new("RGB", (1, 1), c0), Image.new("RGB", (1, 1), c1)
    if angle == "v":
        g = Image.linear_gradient("L").resize((w, h))
    else:  # diagonal
        g = Image.linear_gradient("L").resize((max(w, h) * 2, max(w, h) * 2)).rotate(35, resample=Image.BICUBIC)
        left, top = (g.width - w) // 2, (g.height - h) // 2
        g = g.crop((left, top, left + w, top + h))
    return Image.composite(b.resize((w, h)), a.resize((w, h)), g)


def _background(size, palette, variant):
    w, h = size
    pal = PALETTES[palette]
    rng = random.Random(variant)
    img = _gradient(size, _hex(pal["bg"][0]), _hex(pal["bg"][1]), "v" if variant % 2 else "d")
    img = img.convert("RGBA")
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    acc = _hex(pal["accent"])
    for _ in range(3):
        r = int(rng.uniform(0.25, 0.55) * max(w, h))
        cx = int(rng.uniform(-0.05, 1.05) * w)
        cy = int(rng.uniform(-0.1, 1.1) * h)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=acc + (int(rng.uniform(14, 30)),))
    return Image.alpha_composite(img, layer)


def _tile(icon_name, width):
    """A white-to-pale-blue rounded tile (4:3) with the icon and a soft shadow."""
    height = int(width * 0.75)
    pad = int(width * 0.10)
    shadow_pad = int(width * 0.12)
    canvas = Image.new("RGBA", (width + shadow_pad * 2, height + shadow_pad * 2), (0, 0, 0, 0))
    radius = int(width * 0.075)
    mask = _aa_mask((width, height), radius)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.paste((2, 8, 23, 110), (shadow_pad, shadow_pad + int(width * 0.04)), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(width * 0.045))
    canvas = Image.alpha_composite(canvas, shadow)
    body = _gradient((width, height), _hex("#f8fafc"), _hex("#dff1fe"), "v").convert("RGBA")
    icon = Image.open(os.path.join(ICON_DIR, icon_name + ".png")).convert("RGBA")
    iw = width - pad
    icon = icon.resize((iw, int(iw * icon.height / icon.width)), Image.LANCZOS)
    body.alpha_composite(icon, ((width - icon.width) // 2, (height - icon.height) // 2))
    canvas.paste(body, (shadow_pad, shadow_pad), mask)
    return canvas, shadow_pad


def _tile_rects(stage, layout, flip):
    """Tile rectangles (cx, cy, w, h) for a layout, shrunk by a single factor
    until every tile sits inside the stage and none overlap."""
    sx, sy, sw, sh = stage
    spec = [((1 - cx) if flip else cx, cy, wf) for cx, cy, wf in LAYOUTS[layout]]
    gap = 0.025 * sw
    k = 1.0
    while k > 0.3:
        rects = []
        for cx, cy, wf in spec:
            w = wf * sw * k
            rects.append((sx + cx * sw, sy + cy * sh, w, w * 0.75))
        inside = all(
            cx - w / 2 >= sx - 1 and cx + w / 2 <= sx + sw + 1 and cy - h / 2 >= sy - 1 and cy + h / 2 <= sy + sh + 1
            for cx, cy, w, h in rects
        )
        apart = all(
            abs(a[0] - b[0]) * 2 >= (a[2] + b[2]) + gap * 2 or abs(a[1] - b[1]) * 2 >= (a[3] + b[3]) + gap * 2
            for i, a in enumerate(rects) for b in rects[i + 1:]
        )
        if inside and apart:
            return rects
        k -= 0.02
    return rects


def _place_tiles(img, stage, layout, flip, icons):
    for i, (cx, cy, w, h) in enumerate(_tile_rects(stage, layout, flip)):
        tile, pad = _tile(icons[i % len(icons)], int(w))
        img.alpha_composite(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))


def _font(px):
    return ImageFont.truetype(FONT_PATH, px)


def _wrap(draw, text, font, max_w, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip(" ,;:-") + "…"
    return lines


def compose(kind, layout, flip, palette, variant, icons, title, category):
    size = SIZES[kind]
    w, h = size
    img = _background(size, palette, variant)
    if kind == "hero":
        # The page title is overlaid near the top of a post hero, so keep the
        # bright tiles in the lower part of the image.
        stage = (w * 0.04, h * 0.33, w * 0.92, h * 0.63)
    elif kind == "teaser":
        stage = (w * 0.05, h * 0.06, w * 0.90, h * 0.88)
    else:  # og: text left, tiles right
        stage = (w * 0.50, h * 0.08, w * 0.48, h * 0.84)
    _place_tiles(img, stage, layout, flip, icons)
    if kind == "og":
        d = ImageDraw.Draw(img)
        pal = PALETTES[palette]
        # Left-hand scrim so the title stays readable over the tiles' shadow.
        pill_font = _font(24)
        label = pal["label"].upper()
        pw = int(d.textlength(label, font=pill_font)) + 36
        d.rounded_rectangle((64, 70, 64 + pw, 70 + 44), radius=22, fill=_hex(pal["accent"]))
        d.text((64 + 18, 70 + 6), label, font=pill_font, fill=_hex("#0b1626"))
        title_font = _font(58)
        lines = _wrap(d, title, title_font, 560, 4)
        y = 148
        for line in lines:
            d.text((64, y), line, font=title_font, fill=(255, 255, 255))
            y += 72
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA").resize((44, 44), Image.LANCZOS)
            img.alpha_composite(logo, (64, h - 44 - 52))
        d.text((64 + 58, h - 44 - 52 + 6), "On Air Ireland", font=_font(28), fill=(226, 232, 240))
    return img.convert("RGB")


def make_card(slug, title, category, used_fingerprints, out_dir=POSTS_IMG_DIR, max_tries=200):
    """Create the three card images for a post and return a ledger-ready dict.
    Never reuses a fingerprint in used_fingerprints."""
    pal = normalise_category(category)
    used = set(used_fingerprints or [])
    layouts = sorted(LAYOUTS)
    for salt in range(max_tries):
        rng = random.Random(_seed("card", slug, salt))
        layout = rng.choice(layouts)
        flip = rng.random() < 0.5
        icons = pick_icons(title, category, salt=salt // 4)
        fp = fingerprint(layout, flip, pal, icons)
        if fp in used:
            continue
        variant = _seed("bg", slug, salt) % 100000
        os.makedirs(out_dir, exist_ok=True)
        files = {}
        for kind in ("hero", "teaser", "og"):
            img = compose(kind, layout, flip, pal, variant, icons, title, category)
            path = os.path.join(out_dir, f"{slug}-{kind}.jpg")
            img.save(path, "JPEG", quality=84, optimize=True, progressive=True)
            files[kind] = "/" + os.path.relpath(path, ROOT).replace(os.sep, "/")
        return {
            "kind": "card",
            "files": files,
            "fingerprint": fp,
            "layout": layout + ("-mirrored" if flip else ""),
            "palette": pal,
            "icons": icons,
        }
    raise RuntimeError("Could not find an unused card composition for " + slug)


if __name__ == "__main__":
    import sys
    s = sys.argv[1] if len(sys.argv) > 1 else "demo-card"
    t = sys.argv[2] if len(sys.argv) > 2 else "How to Set Up NOW on a Samsung or LG Smart TV"
    c = sys.argv[3] if len(sys.argv) > 3 else "Installation-Guides"
    out = sys.argv[4] if len(sys.argv) > 4 else "/tmp"
    print(make_card(s, t, c, [], out_dir=out))
