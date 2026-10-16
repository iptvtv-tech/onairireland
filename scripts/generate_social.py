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
            "model": "claude-sonnet-5",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    if not resp.ok:
        print(f"Anthropic API error (social) {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp.json()["content"][0]["text"]


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

def generate_sport_social(week_label: str, events: list) -> dict:
    """
    Generate X post and WhatsApp message for the weekly sport guide.

    Returns dict with keys: x_post, whatsapp_msg.
    """
    # Build a short listing for the prompt (top 10 events)
    top = events[:10]
    lines = "\n".join(
        f"- {e['event']} ({e['competition']}) — {e['watch']} — {e['date']} {e['time']}"
        for e in top
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
   <whatsapp>...</whatsapp>"""

    raw = _call_claude(prompt, 600)

    result = {
        "x_post": _parse_block(raw, "<xpost>", "</xpost>"),
        "whatsapp_msg": _parse_block(raw, "<whatsapp>", "</whatsapp>"),
    }

    for key, val in result.items():
        if not val:
            print(f"WARNING: sport social generation returned empty {key}. Raw:\n{raw[:400]}")

    return result
