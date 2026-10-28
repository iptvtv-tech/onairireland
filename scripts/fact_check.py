#!/usr/bin/env python3
"""
Claims list for a draft post: every service, channel, price, date and rights
claim in the article, its FAQ and its social drafts, each with a source or a flag.

Runs at the end of scripts/generate_post.py, and the Mon/Wed/Fri draft PR shows
the result at the top. It points the review at the right lines: it never edits
the draft and never blocks a merge.

It uses the model with web search and web fetch (as generate_sport_week.py
does), plus the checked facts in _data/site_facts.yml and the prices in
_data/prices.yml, so the writer and the checker work from the same facts.

Also runs on its own, on any post (needs ANTHROPIC_API_KEY):

    python scripts/fact_check.py _posts/2026-10-28-sky-sports-vs-premier-sports-which-do-you-need.md
"""
import json
import os
import re
import sys
from urllib.parse import urlparse

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_facts  # noqa: E402
from generate_social import write_multiline_output  # noqa: E402

MODEL = "claude-sonnet-5"
MAX_CLAIMS = 30
ICONS = {"wrong": "❌", "unconfirmed": "⚠️", "ok": "✅"}
STATUS_WORDS = {
    "ok": "ok", "confirmed": "ok", "correct": "ok", "true": "ok",
    "wrong": "wrong", "incorrect": "wrong", "false": "wrong", "contradicted": "wrong",
    "unconfirmed": "unconfirmed", "unverified": "unconfirmed", "unknown": "unconfirmed",
}
WHERE_LABELS = {"article": "Article", "faq": "FAQ", "x": "X post",
                "whatsapp": "WhatsApp", "video": "Video script"}

PROMPT = """You are fact-checking a draft for On Air Ireland (onairireland.ie), an
independent site about LEGAL streaming in Ireland. Readers are in the Republic of
Ireland, so every rights holder, channel and price must be the Irish one, which
often differs from the UK.

1. List the factual claims a reader could act on: which service, channel, app or
   broadcaster shows something; what a membership, package or app includes;
   prices; dates and deadlines; which devices and features are available in
   Ireland. Skip general advice, opinions and how-to steps. Merge near-duplicates
   and list at most <<MAX>>, most important first.

2. Check each claim:
   - First against OUR CHECKED FACTS and OUR CHECKED PRICES below. They were
     checked on the providers' own pages, and they win over anything else.
   - Otherwise, on the provider's or rights holder's own page for Ireland, using
     web search and web fetch. Use primary sources only: the broadcaster, the
     service, the league or governing body, An Post or Citizens Information.
     Never use comparison sites, forums, or sites about VPNs or IPTV.

3. Give each claim one status:
   - "ok": it matches our checked facts or prices, or you confirmed it on a
     primary source.
   - "wrong": it contradicts our checked facts, our checked prices or a primary
     source.
   - "unconfirmed": you couldn't confirm it on a primary source.
   A claim that a service does NOT show or include something is "unconfirmed"
   unless our checked facts or a primary source say so.

Return ONLY a JSON object between <json> and </json> tags, no commentary:
<json>
{"claims": [
  {"claim": "the claim, quoted or closely paraphrased, at most 25 words",
   "where": "faq",
   "status": "wrong",
   "note": "one short sentence: what is right, or what couldn't be confirmed",
   "source": "https://... the page you used, or: our checked facts"}
]}
</json>
"where" is one of: article, faq, x, whatsapp, video.

OUR CHECKED FACTS:

<<FACTS>>

OUR CHECKED PRICES (euro):
<<PRICES>>

=== DRAFT ARTICLE (front matter with the FAQ, then the body) ===
<<POST>>

=== X POST ===
<<X>>

=== WHATSAPP POST ===
<<WHATSAPP>>

=== VIDEO SCRIPT ===
<<VIDEO>>
"""


def build_prompt(post_text: str, social: dict = None) -> str:
    social = social or {}
    parts = {
        "<<MAX>>": str(MAX_CLAIMS),
        "<<FACTS>>": site_facts.facts_for_prompt(),
        "<<PRICES>>": site_facts.prices_for_prompt(),
        "<<POST>>": post_text.strip(),
        "<<X>>": (social.get("x_post") or "(none)").strip(),
        "<<WHATSAPP>>": (social.get("whatsapp_msg") or "(none)").strip(),
        "<<VIDEO>>": (social.get("youtube_script") or "(none)").strip(),
    }
    prompt = PROMPT
    for key, value in parts.items():
        prompt = prompt.replace(key, value)
    return prompt


def call_claude(prompt: str) -> str:
    """Run the checking conversation (following pause_turn) and return its text."""
    tools = [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 8},
        {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 8,
         "max_content_tokens": 20000},
    ]
    messages = [{"role": "user", "content": prompt}]
    text = []
    for _ in range(5):
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": MODEL, "max_tokens": 12000, "tools": tools, "messages": messages},
            timeout=600,
        )
        if not resp.ok:
            print(f"Anthropic API error (fact check) {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        text += [b.get("text", "") for b in content if b.get("type") == "text"]
        for b in content:
            if b.get("type") == "web_fetch_tool_result":
                print(f"Fact check fetched: {((b.get('content') or {}).get('url')) or '?'}")
        stop_reason = data.get("stop_reason")
        if stop_reason == "max_tokens":
            print("WARNING: the fact check hit max_tokens; its claims list may be cut short.")
        if stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": content})
    return "".join(text)


def parse_claims(raw: str) -> list:
    """The claims list from the model's reply. Raises ValueError if there isn't one."""
    m = re.search(r"<json>\s*(\{.*\})\s*</json>", raw, re.S) or re.search(r"(\{\s*\"claims\".*\})", raw, re.S)
    if not m:
        raise ValueError("no claims list in the reply")
    items = json.loads(m.group(1)).get("claims")
    if not isinstance(items, list):
        raise ValueError("the reply's claims list isn't a list")
    claims = []
    for item in items[:MAX_CLAIMS]:
        if not isinstance(item, dict) or not str(item.get("claim") or "").strip():
            continue
        status = STATUS_WORDS.get(str(item.get("status", "")).strip().lower(), "unconfirmed")
        where = str(item.get("where", "article")).strip().lower()
        claims.append({
            "claim": str(item["claim"]).strip(),
            "where": where if where in WHERE_LABELS else "article",
            "status": status,
            "note": str(item.get("note") or "").strip(),
            "source": str(item.get("source") or "").strip(),
        })
    return claims


def _cell(text: str, limit: int) -> str:
    """Make text safe for one Markdown table cell."""
    text = " ".join(str(text).split()).replace("|", "/")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _source(source: str) -> str:
    if source.startswith(("http://", "https://")):
        host = urlparse(source).netloc.lower()
        host = host[4:] if host.startswith("www.") else host
        return f"[{host}]({source.replace(' ', '%20').replace(')', '%29')})"
    if not source:
        return "—"
    if "checked facts" in source.lower() or source.lower().startswith("our"):
        return "our facts"
    return _cell(source, 60)


def _claims(n: int) -> str:
    return f"{n} claim" if n == 1 else f"{n} claims"


def format_markdown(claims: list) -> str:
    """The claims list as the PR body section: problems first, the rest folded away."""
    counts = {s: sum(1 for c in claims if c["status"] == s) for s in ICONS}
    flagged = [c for c in claims if c["status"] != "ok"]
    flagged.sort(key=lambda c: 0 if c["status"] == "wrong" else 1)
    confirmed = [c for c in claims if c["status"] == "ok"]

    lines = ["### 🔎 Fact check", ""]
    basis = ("Checked against our facts file, our price tracker and the providers' own pages. "
             "It doesn't block the merge")
    if not claims:
        lines.append("> ⚠️ **No checkable claims came back.** Check every service, price, date and "
                     "channel by hand.")
        return "\n".join(lines)
    if flagged:
        lines.append(f"**{counts['wrong']} wrong · {counts['unconfirmed']} unconfirmed · "
                     f"{counts['ok']} confirmed.** {basis}, so fix or confirm every ❌ and ⚠️ line first.")
        lines += ["", "| | Claim | Where | Note | Source |", "|---|---|---|---|---|"]
        for c in flagged:
            lines.append(f"| {ICONS[c['status']]} | {_cell(c['claim'], 180)} | {WHERE_LABELS[c['where']]} "
                         f"| {_cell(c['note'], 220)} | {_source(c['source'])} |")
    else:
        lines.append(f"**No problems found in {_claims(counts['ok'])}.** {basis}, and anything it "
                     "missed still needs your check.")
    if confirmed:
        lines += ["", "<details>", f"<summary>{len(confirmed)} confirmed {_claims(len(confirmed)).split(' ', 1)[1]}</summary>", "",
                  "| | Claim | Where | Source |", "|---|---|---|---|"]
        for c in confirmed:
            lines.append(f"| ✅ | {_cell(c['claim'], 180)} | {WHERE_LABELS[c['where']]} | {_source(c['source'])} |")
        lines += ["", "</details>"]
    return "\n".join(lines)


def check_post(post_text: str, social: dict = None) -> dict:
    """Check one post and its social drafts. Returns the claims, the PR body
    section (markdown), a one-line summary and the number of flagged claims."""
    claims = parse_claims(call_claude(build_prompt(post_text, social)))
    counts = {s: sum(1 for c in claims if c["status"] == s) for s in ICONS}
    return {
        "claims": claims,
        "markdown": format_markdown(claims),
        "summary": (f"Fact check: {counts['wrong']} wrong, {counts['unconfirmed']} unconfirmed, "
                    f"{counts['ok']} confirmed."),
        "flagged": counts["wrong"] + counts["unconfirmed"],
    }


def write_fact_check_output(gh_out: str, result: dict) -> None:
    """Hand the PR body section to the workflow (GITHUB_OUTPUT), or print it."""
    if gh_out:
        write_multiline_output(gh_out, "fact_check", result["markdown"])
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"fact_flags={result['flagged']}\n")
    else:
        print(result["markdown"])


def main(argv) -> int:
    if len(argv) != 2 or not os.path.isfile(argv[1]):
        print("Usage: python scripts/fact_check.py _posts/<post>.md")
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        result = check_post(fh.read())
    print(result["markdown"])
    print()
    print(result["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
