#!/usr/bin/env python3
"""
Generates social copy (X post, WhatsApp message, and optionally a YouTube
script) from a blog post or sport listings.

Called as a module by generate_post.py and generate_sport_week.py.
Not run standalone.
"""
import os
import re

import requests

# Model used for all social copy generation. Update here to change everywhere.
MODEL = "claude-sonnet-5"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, max_tokens: int = 600) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            # Room for any thinking the model does before it writes the copy.
            "max_tokens": max(max_tokens, 2000),
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    if not resp.ok:
        print(f"Anthropic API error (social) {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    data = resp.json()
    # The reply can hold several blocks (e.g. a thinking block before the
    # text), so join every text block instead of assuming the first one.
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    if not text:
        kinds = [b.get("type") for b in data.get("content", [])]
        raise RuntimeError(f"no text in reply (stop_reason={data.get('stop_reason')}, blocks={kinds})")
    return text


def _parse_block(text: str, open_tag: str, close_tag: str) -> str:
    """Extract content between open_tag and close_tag, strip whitespace."""
    m = re.search(
        rf"{re.escape(open_tag)}\s*(.*?)\s*{re.escape(close_tag)}", text, re.S
    )
    return m.group(1).strip() if m else ""


def write_multiline_output(gh_out_path: str, key: str, value: str) -> None:
    """Write a (possibly multiline) value to GITHUB_OUTPUT using heredoc syntax."""
    if not gh_out_path or not value:
        return
    delimiter = "OAIEOF"
    with open(gh_out_path, "a", encoding="utf-8") as fh:
        fh.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


# ---------------------------------------------------------------------------
# Blog-post social content
# ---------------------------------------------------------------------------

def generate_post_social(
    title: str,
    category: str,
    brief: str,
    post_body: str,
    pillar: str = "",
    video_angle: str = None,
    want_whatsapp: bool = True,
) -> dict:
    """
    Generate social copy for a blog post.

    Returns a dict with:
      x_post        — tweet, under 280 chars (always)
      whatsapp_msg  — WhatsApp channel message (only if want_whatsapp is True)
      youtube_script — full spoken script (only if video_angle is set)
    """
    pillar_line = f"Content pillar: {pillar}" if pillar else ""

    whatsapp_section = ""
    if want_whatsapp:
        whatsapp_section = """

2. WHATSAPP between <whatsapp> and </whatsapp>:
   3-5 lines for a WhatsApp channel post.
   Line 1: one emoji category label + one-line headline:
     📺 new service/app content
     🔔 price or availability change
     🏆 sport content
     💡 tips or how-to guides
     📱 device content
   Then 1-3 short factual lines.
   Final line: Full guide → onairireland.ie
   No extra emojis beyond the first line.
   <whatsapp>...</whatsapp>"""

    youtube_section = ""
    max_tokens = 600

    if video_angle:
        max_tokens = 4000
        youtube_section = """

3. YOUTUBE SCRIPT between <youtube> and </youtube>:
   Write a full spoken script based on the blog post content.
   Video angle: """ + video_angle + """

   Use this structure:
   [Hook]
   One sentence naming the viewer's problem or question.

   [Intro]
   Quick overview of what the video covers (15-30 sec of speech).

   [Main content — use plain subheadings like [Section: name] for each part]
   Walk through the blog post's key points in natural spoken language.
   Short sentences. Conversational — not written prose. No stage directions.

   [Verdict / recommendation]
   A plain, direct summary or next step.

   [Sign-off]
   "For more on legal streaming in Ireland, see onairireland.ie — link in the description."

   <youtube>
   ... script here ...
   </youtube>"""

    prompt = f"""You are writing social copy for On Air Ireland (onairireland.ie), an independent
Irish site about LEGAL streaming services and devices.

Tone: practical, factual, plain Irish English. Not salesy. No exclamation marks.
Never mention VPNs, unofficial IPTV or unlicensed streaming.
Links only to onairireland.ie pages — never to external sites.

Blog post details
Title: {title}
Category: {category}
{pillar_line}
Brief: {brief}

Blog post excerpt:
{post_body[:900]}

---

Write each section exactly as labelled:

1. X POST between <xpost> and </xpost>:
   One tweet, under 280 characters total. Factual, no fluff, no hashtags.
   Must end with: onairireland.ie
   <xpost>...</xpost>{whatsapp_section}{youtube_section}"""

    raw = _call_claude(prompt, max_tokens)

    result = {
        "x_post": _parse_block(raw, "<xpost>", "</xpost>"),
    }
    if want_whatsapp:
        result["whatsapp_msg"] = _parse_block(raw, "<whatsapp>", "</whatsapp>")
    if video_angle:
        result["youtube_script"] = _parse_block(raw, "<youtube>", "</youtube>")

    # Warn if anything came back empty
    for key, val in result.items():
        if not val:
            print(f"WARNING: social generation returned empty {key}. Raw response:\n{raw[:400]}")

    return result


# ---------------------------------------------------------------------------
# Sport-guide social content
# ---------------------------------------------------------------------------

FREE_TO_AIR = re.compile(r"\b(RT[ÉE]|TG4|Virgin Media)\b", re.I)


def _irish_time(hhmm: str) -> str:
    """'20:10' -> '8.10pm', '15:00' -> '3pm', 'TBC' -> 'time TBC'."""
    m = re.fullmatch(r"(\d{2}):(\d{2})", str(hhmm))
    if not m:
        return "time TBC"
    h, mins = int(m.group(1)), m.group(2)
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{suffix}" if mins == "00" else f"{h12}.{mins}{suffix}"


def _free_channels(watch: str) -> str:
    """The free-to-air part of a 'watch' line, e.g. 'TG4 and Premier Sports 1' -> 'TG4'."""
    parts = [p.strip() for p in re.split(r"\s*(?:/|,|\band\b|\bor\b)\s*", watch) if p.strip()]
    free = [p for p in parts if FREE_TO_AIR.search(p)]
    return " and ".join(free) if free else watch


def build_matchday_alert(event: dict) -> dict:
    """
    Build the match-day alert for one event straight from the checked listing,
    so the time and channel always match _data/sport_week.yml.

    Returns dict with keys: matchday_msg, matchday_day (e.g. 'Saturday 31 Oct').
    """
    d = event["date"]
    if isinstance(d, str):
        import datetime as _dt
        d = _dt.date.fromisoformat(d)
    if event.get("free"):
        access = f"✅ Free on {_free_channels(event['watch'])}"
    else:
        access = f"💶 Needs {event['watch']}"
    msg = (
        f"🔴 *TODAY: {event['event']}*\n"
        f"⏰ {_irish_time(event['time'])} | 📺 {event['watch']}\n"
        f"{access}\n\n"
        f"This week's full list → onairireland.ie/sport-on-tv/"
    )
    return {"matchday_msg": msg, "matchday_day": f"{d:%A} {d.day} {d:%b}"}


def generate_sport_social(week_label: str, events: list) -> dict:
    """
    Generate X post, WhatsApp message and a match-day alert for the weekly
    sport guide.

    Returns dict with keys: x_post, whatsapp_msg, matchday_msg, matchday_day.
    """
    # Number every event: the model sees the whole week (not just the first
    # few days) and picks the match-day game by number.
    lines = "\n".join(
        f"{i}. {e['event']} ({e['competition']}) — {e['watch']}"
        f"{' (free)' if e.get('free') else ''} — {e['date']} {e['time']}"
        for i, e in enumerate(events, 1)
    )

    prompt = f"""You are writing social copy for On Air Ireland (onairireland.ie), an independent
Irish site about LEGAL streaming.

Tone: practical, factual, plain Irish English. Not salesy. No exclamation marks.
Never mention VPNs or unlicensed streaming.

Sport on Irish TV — {week_label}:
{lines}

Write:

1. X POST between <xpost> and </xpost>:
   One tweet, under 280 characters. Highlight the 2-3 biggest events.
   End with: onairireland.ie/sport-on-tv/
   <xpost>...</xpost>

2. WHATSAPP between <whatsapp> and </whatsapp>:
   WhatsApp channel post.
   Line 1: 🏆 Sport on TV this week
   Then list the 5-7 biggest events, one per line:
     Event name — Channel — Date Time
   Final line: Full listings → onairireland.ie/sport-on-tv/
   <whatsapp>...</whatsapp>

3. MATCH-DAY PICK between <pick> and </pick>:
   The number of the single game Irish viewers care most about this week
   (an Ireland international first, then a big GAA, provincial rugby or
   Premier League game). Prefer a free-to-air game when two are close.
   Just the number.
   <pick>...</pick>"""

    raw = _call_claude(prompt, 600)

    result = {
        "x_post": _parse_block(raw, "<xpost>", "</xpost>"),
        "whatsapp_msg": _parse_block(raw, "<whatsapp>", "</whatsapp>"),
    }

    for key, val in result.items():
        if not val:
            print(f"WARNING: sport social generation returned empty {key}. Raw:\n{raw[:400]}")

    # Match-day alert: the model only chooses the game; the text is built from
    # the listing itself. Falls back to the first free game, then the first game.
    pick = _parse_block(raw, "<pick>", "</pick>")
    m = re.search(r"\d+", pick)
    idx = int(m.group()) - 1 if m else -1
    if not 0 <= idx < len(events):
        print(f"WARNING: no usable match-day pick ({pick!r}); using a fallback.")
        idx = next((i for i, e in enumerate(events) if e.get("free")), 0)
    if events:
        result.update(build_matchday_alert(events[idx]))

    return result
