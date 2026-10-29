"""The _video_scripts/*.short.yml format: loading, checking and the YouTube upload text.

No heavy imports, so the PR check and the draft generator can use it too.

A spec looks like this:

    post: _posts/<date>-<slug>.md
    post_url: https://onairireland.ie/<category>/<slug>/
    scenes:                       # 3 to 7 scenes, about 5 to 12 seconds each
      - kicker: HEAD TO HEAD      # small green label
        head: Netflix or Disney+? # big white text, up to 40 characters
        sub: optional grey line
        pills: [optional, short, labels]
        badge: FREE               # optional
        vo: What the voice says in this scene (shown as captions too).
    end_vo: Full guide at onairireland.ie.
    youtube:
      title: Up to 100 characters
      description: |
        ...must contain post_url...
      tags: [up to 500 characters in all]
"""
import yaml

BANNED = ("vpn", "iptv", "unofficial", "pirat", "illegal", "dodgy", "grey area", "sideload", "kodi")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _all_text(spec):
    yt = spec.get("youtube") or {}
    parts = [spec.get("end_vo", ""), yt.get("title", ""), yt.get("description", ""),
             " ".join(map(str, yt.get("tags") or []))]
    for sc in spec.get("scenes") or []:
        parts += [str(sc.get(k, "")) for k in ("kicker", "head", "sub", "badge", "vo")]
        parts += [str(p) for p in sc.get("pills") or []]
    return " ".join(parts)


def problems(spec):
    """Everything wrong with a spec, as a list of sentences (empty if it's fine)."""
    out = []
    if not isinstance(spec, dict):
        return ["the file isn't a YAML mapping"]
    scenes = spec.get("scenes")
    if not isinstance(scenes, list) or not 3 <= len(scenes) <= 7:
        out.append("needs 3 to 7 scenes")
        scenes = scenes if isinstance(scenes, list) else []
    for i, sc in enumerate(scenes, 1):
        for key in ("kicker", "head", "vo"):
            if not str((sc or {}).get(key, "")).strip():
                out.append(f"scene {i} has no {key}")
        if len(str((sc or {}).get("head", ""))) > 40:
            out.append(f"scene {i}'s head is over 40 characters")
        if len(str((sc or {}).get("vo", "")).split()) > 40:
            out.append(f"scene {i}'s voiceover is over 40 words")
    if not str(spec.get("end_vo", "")).strip():
        out.append("missing end_vo")
    yt = spec.get("youtube")
    if not isinstance(yt, dict):
        out.append("missing the youtube section")
        yt = {}
    title = str(yt.get("title", ""))
    if not title or len(title) > 100:
        out.append("YouTube title is missing or over 100 characters")
    if "<" in title or ">" in title:
        out.append("YouTube title can't contain < or >")
    desc = str(yt.get("description", ""))
    if not desc or len(desc) > 5000:
        out.append("YouTube description is missing or over 5,000 characters")
    if spec.get("post_url") and spec["post_url"] not in desc:
        out.append("the YouTube description doesn't link the article (post_url)")
    if len(", ".join(map(str, yt.get("tags") or []))) > 500:
        out.append("tags are over YouTube's 500-character limit")
    words = sum(len(str(sc.get("vo", "")).split()) for sc in scenes if isinstance(sc, dict))
    if words > 170:
        out.append(f"voiceover is {words} words; keep it under 170 (about a minute)")
    low = _all_text(spec).lower()
    for b in BANNED:
        if b in low:
            out.append(f"contains a word the site never uses: {b}")
    return out


def youtube_text(spec, total=None, starts=None):
    """Ready-to-paste upload text. total/starts (seconds) come from the render."""
    yt = spec["youtube"]
    lines = [f"# YouTube upload: {yt['title']}", "",
             "## Title", "", yt["title"], "",
             "## Description", "", str(yt["description"]).rstrip(), "",
             "## Tags", "", ", ".join(map(str, yt.get("tags") or [])), "",
             "## Settings", "",
             "- Upload the MP4 as it is: it's vertical and under 3 minutes, so YouTube makes it a Short.",
             "- Audience: No, it's not made for kids.",
             "- Altered or synthetic content: answer as for the channel's other Shorts "
             "(the voice is computer-generated).",
             "- Category: People & Blogs, as the other Shorts.",
             "- Chapters: none. YouTube doesn't show chapters on Shorts."]
    if total:
        lines.append(f"- Length: {total:.0f} seconds.")
    if starts is not None:
        lines += ["", "## Scene times", ""]
        heads = [sc["head"] for sc in spec["scenes"]] + ["End card"]
        for head, st in zip(heads, starts):
            lines.append(f"- {int(st // 60)}:{int(st % 60):02d} {head}")
    return "\n".join(lines) + "\n"
