#!/usr/bin/env python3
"""
Writes the YouTube Short spec (_video_scripts/<date>-<slug>.short.yml) for a draft
post: the scenes and voiceover for a ~45-second vertical Short, plus the YouTube
title, description and tags.

Called by generate_post.py when the topic has a video. The spec is reviewed in
the draft PR with the article. Once it's merged, the YouTube Short workflow
renders the MP4 from it (scripts/video/render_short.py) and comments on the PR
with the download link.

Run by hand to (re)write a spec for an existing post:
    python scripts/generate_short.py _posts/<date>-<slug>.md
"""
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "video"))
import short_spec  # noqa: E402
from generate_social import _call_claude, _parse_block  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHATSAPP_URL = "https://whatsapp.com/channel/0029VbDvKAaEawdv3YeHxu2E"

EXAMPLE = """scenes:
  - kicker: HEAD TO HEAD
    head: Sky Sports or Premier Sports?
    vo: Sky Sports or Premier Sports? If you follow the Premier League in Ireland, you might need both.
  - kicker: SKY SPORTS
    head: Sky Sports
    pills: [Most Premier League games, Formula 1, Golf, PDC darts]
    vo: Sky Sports has most of the live Premier League, Formula 1 exclusively, most of the big golf, and PDC darts.
  - kicker: NO CONTRACT
    head: Both on NOW
    pills: [Sports · Sky Sports, Sports Extra · Premier Sports & TNT]
    vo: No contract? NOW's Sports membership has Sky Sports, and Sports Extra has Premier Sports and TNT Sports.
end_vo: Prices and the full guide are at onairireland.ie.
youtube:
  title: "Sky Sports vs Premier Sports in Ireland — Which Do You Need?"
  description: |
    Sky Sports or Premier Sports? Both show the Premier League in Ireland, but outside football they split neatly.

    📺 Sky Sports — most live Premier League games, every Formula 1 session exclusively until 2034 and PDC darts.

    💶 No contract, on NOW:
    • Sports (Sky Sports) — €38.99 a month
    • Sports Extra (Premier Sports and TNT Sports) — €33.99 a month

    NOW prices as shown on NOW's Irish site on 28 October 2026.
  tags: [sky sports vs premier sports, premier sports ireland, now sports ireland, on air ireland]"""

PROMPT = """You are turning an On Air Ireland article into a YouTube Short. On Air Ireland
(onairireland.ie) is an independent Irish guide to LEGAL streaming services, devices and TV.

Write the Short as YAML between <short> and </short>, in exactly the shape of this example
(which is from a different article):

<example>
{example}
</example>

Rules:
- Use ONLY facts stated in the article below. No service, channel, competition, price, date,
  number or claim that isn't in it. If the article gives a price, give the date it was checked,
  as the article states it. Never invent a date.
- 4 to 6 scenes, then end_vo. About 110 to 150 spoken words in all (40 to 55 seconds).
- kicker: 1 to 3 words in capitals. head: up to 30 characters. pills: up to 5 short labels,
  each under 32 characters. Use "sub" for one short line only when it adds something.
- vo: plain spoken Irish English, short sentences, no exclamation marks. The first scene's vo is
  the hook: the viewer's question in one or two sentences. Captions show the vo as written, so
  write names normally (RTÉ, TG4, NOW, 3pm).
- end_vo: one short sentence pointing to onairireland.ie.
- youtube.title: under 70 characters, says what the viewer learns, ends with "in Ireland" or
  names Ireland. No hashtags, no clickbait, no < or >.
- youtube.description: 3 to 6 short paragraphs or lists in the example's style (📺 💶 🆓 bullets
  are fine), from the article only. Do NOT add links, the WhatsApp channel or a sign-off: those
  are added automatically.
- youtube.tags: 8 to 12 lowercase search phrases, mostly ending in "ireland", plus "on air ireland".
- Practical and neutral, not salesy. No claims of testing or personal experience. Never mention
  VPNs, IPTV, or unofficial, pirated or illegal streaming in any way.

Article title: {title}
Article address: {post_url}

Article:
{body}

Longer video script written from the same article (for reference only):
{script}
"""


def _footer(post_url, has_prices):
    lines = [f"🔗 Full guide: {post_url}"]
    if has_prices:
        lines.append("💶 Every Irish streaming price: https://onairireland.ie/streaming-prices/")
    lines += ["", "📲 Get alerts when Irish streaming prices change — free WhatsApp channel:", WHATSAPP_URL,
              "", "📘 Free PDF guides: https://onairireland.ie/free-guides/",
              "Only legal services available in Ireland."]
    return "\n".join(lines)


def _strip_front_matter(text):
    m = re.match(r"---\n.*?\n---\n", text, re.S)
    return text[m.end():] if m else text


def generate_short_spec(title, body, script, post_url, post_rel):
    """Ask the model for the spec, check it, retry once with the problems. Returns the spec dict."""
    prompt = PROMPT.format(example=EXAMPLE, title=title, post_url=post_url,
                           body=_strip_front_matter(body)[:9000], script=(script or "(none)")[:5000])
    last = []
    for attempt in range(2):
        if last:
            prompt += ("\n\nYour last answer had these problems; fix them and send the whole YAML again:\n- "
                       + "\n- ".join(last))
        raw = _call_claude(prompt, 4000)
        block = _parse_block(raw, "<short>", "</short>") or raw
        block = re.sub(r"^```(?:yaml)?\s*|\s*```$", "", block.strip())
        try:
            spec = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            last = [f"the YAML didn't parse: {exc}"]
            continue
        if not isinstance(spec, dict) or not isinstance(spec.get("youtube"), dict):
            last = ["the answer must be one YAML mapping with scenes, end_vo and youtube"]
            continue
        desc = str(spec["youtube"].get("description", "")).rstrip()
        spec["youtube"]["description"] = desc + "\n\n" + _footer(post_url, "€" in desc) + "\n"
        spec = {"post": post_rel, "post_url": post_url, **spec}
        last = short_spec.problems(spec)
        if not last:
            return spec
        print(f"Short spec attempt {attempt + 1} problems: {'; '.join(last)}")
    raise RuntimeError("the Short spec still had problems: " + "; ".join(last))


class _Literal(str):
    pass


def _literal_repr(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_Literal, _literal_repr)


def write_spec(spec, path, today):
    spec = dict(spec)
    spec["youtube"] = dict(spec["youtube"])
    spec["youtube"]["description"] = _Literal(spec["youtube"]["description"])
    header = (f"# YouTube Short for {spec['post']}\n"
              f"# Generated {today}. Review it with the article: every fact must match the post.\n"
              "# After merging, the YouTube Short workflow renders the MP4 and comments on the PR.\n"
              "# Scenes: kicker (small green label), head (big text), optional sub, pills, badge;\n"
              "# vo is spoken and shown as captions. Format: scripts/video/short_spec.py\n\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.dump(spec, fh, allow_unicode=True, sort_keys=False, width=1000)


def short_text_for_fact_check(spec):
    """The spoken lines and YouTube text, for the claims list."""
    lines = [sc["vo"] for sc in spec["scenes"]] + [spec["end_vo"]]
    return ("YouTube Short voiceover:\n" + "\n".join(lines)
            + "\n\nYouTube title: " + spec["youtube"]["title"]
            + "\nYouTube description:\n" + spec["youtube"]["description"])


def main(argv):
    if len(argv) != 2 or not os.path.isfile(argv[1]):
        print("Usage: python scripts/generate_short.py _posts/<date>-<slug>.md")
        return 2
    post_path = argv[1]
    with open(post_path, encoding="utf-8") as fh:
        text = fh.read()
    fm = yaml.safe_load(re.match(r"---\n(.*?)\n---\n", text, re.S).group(1))
    name = os.path.basename(post_path)[:-3]
    slug = name[11:]
    category = (fm.get("categories") or ["posts"])[0]
    post_url = f"https://onairireland.ie/{str(category).lower()}/{slug}/"
    script_path = os.path.join(REPO_ROOT, "_video_scripts", f"{name}.md")
    script = open(script_path, encoding="utf-8").read() if os.path.isfile(script_path) else ""
    spec = generate_short_spec(fm.get("title", slug), text, script, post_url,
                               os.path.relpath(os.path.abspath(post_path), REPO_ROOT))
    out = os.path.join(REPO_ROOT, "_video_scripts", f"{name}.short.yml")
    write_spec(spec, out, name[:10])
    print(f"Wrote {os.path.relpath(out, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
