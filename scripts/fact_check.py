#!/usr/bin/env python3
"""
Claims list for a draft post: every service, channel, price, date and rights
claim in the article, its FAQ and its social drafts, each with a source or a flag.

Runs inside scripts/generate_post.py. The Mon/Wed/Fri draft run checks the draft,
sends any flagged claims back to the writer and checks again, until a check
flags nothing (or the topic is parked). A draft PR only opens with a clean list,
which the PR shows at the top. This script never edits the draft itself.

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
import yaml

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

# A claim stays ✅ only when its source is our facts file, our price tracker, or
# one of these primary sources: the service, broadcaster, league, governing body,
# app store or regulator itself (a subdomain counts too). Anything else, such as a
# news report, comparison site, forum or "watch abroad" page, can't confirm a
# claim: it becomes ⚠️ with a note naming the site. In #122 two BBC iPlayer claims
# were "confirmed" from a watch-abroad page and a 2015 article about VPNs.
# Add a host only with evidence that it is the organisation's own site.
PRIMARY_HOSTS = {
    # Streaming services and pay-TV providers
    "netflix.com", "disneyplus.com", "primevideo.com", "amazon.ie", "aboutamazon.eu",
    "apple.com", "hbomax.com", "paramountplus.com", "hayu.com", "nowtv.com", "sky.com",
    "virginmedia.ie", "eir.ie", "vodafone.ie", "three.ie", "premiersports.com",
    "premiersports.ie", "dazn.com", "britbox.com", "youtube.com",
    # Irish and UK broadcasters
    "rte.ie", "virginmediatelevision.ie", "tg4.ie", "bbc.co.uk", "bbc.com",
    "channel4.com", "itv.com", "itvx.com", "saorview.ie",
    # Leagues, governing bodies and competitions
    "gaa.ie", "irishrugby.ie", "fai.ie", "uefa.com", "premierleague.com",
    "sixnationsrugby.com", "epcrugby.com", "unitedrugby.com", "formula1.com",
    "rydercup.com", "pdc.tv", "motogp.com", "laliga.com", "spfl.co.uk",
    # Devices, app stores and platform help pages
    "google.com", "roku.com", "samsung.com", "lg.com", "amazon.co.uk",
    # Irish public bodies
    "citizensinformation.ie", "tvlicence.ie", "anpost.com", "anpost.ie",
    "comreg.ie", "cnam.ie", "gov.ie",
}
OUR_SOURCE_WORDS = ("our checked facts", "our facts", "our price", "our tracker", "checked prices")

PROMPT = """You are fact-checking a draft for On Air Ireland (onairireland.ie), an
independent site about LEGAL streaming in Ireland. Readers are in the Republic of
Ireland, so every rights holder, channel and price must be the Irish one, which
often differs from the UK.

1. List the factual claims a reader could act on: which service, channel, app or
   broadcaster shows something; what a membership, package or app includes;
   prices; dates and deadlines; which devices and features are available in
   Ireland. Skip general advice, opinions and how-to steps, and skip lines that
   only tell readers to check with a provider or say that something varies, may
   change or depends on the device. Merge near-duplicates and list at most
   <<MAX>>, most important first.

2. Check each claim:
   - First against OUR CHECKED FACTS and OUR CHECKED PRICES below. They were
     checked on the providers' own pages, and they win over anything else.
   - Otherwise, on the provider's or rights holder's own page for Ireland, using
     web search and web fetch. Use primary sources only: the broadcaster, the
     service, the league or governing body, the app store listing, An Post,
     Citizens Information or another Irish public body.
   - News reports, comparison sites, forums, blogs and pages about watching
     from abroad, VPNs or IPTV can never confirm a claim. If one of those is the
     only place you find it, mark the claim "unconfirmed" and name that site in
     the note.

3. Give each claim one status:
   - "ok": it matches our checked facts or prices, or you confirmed it on a
     primary source.
   - "wrong": it contradicts our checked facts, our checked prices, or every
     primary source you found.
   - "unconfirmed": you couldn't confirm it on a primary source.
   If primary sources disagree with each other (for example a provider's FAQ
   and its app store listing), the claim is "unconfirmed", never "wrong", and
   the note says "Official sources disagree:" and what each one says.
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


def _without_flags(post_text: str) -> str:
    """The post without its fact_check_wrong list, so a recheck doesn't check
    the list of wrong claims as if it were the article."""
    m = re.match(r"---\n(.*?)\n---\n", post_text, re.S)
    if not m:
        return post_text
    fm = yaml.safe_load(m.group(1)) or {}
    if not isinstance(fm, dict) or "fact_check_wrong" not in fm:
        return post_text
    fm.pop("fact_check_wrong")
    return ("---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000)
            + "---\n" + post_text[m.end():])


def build_prompt(post_text: str, social: dict = None) -> str:
    social = social or {}
    post_text = _without_flags(post_text)
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


def _is_ours(source: str) -> bool:
    return any(word in source.lower() for word in OUR_SOURCE_WORDS)


def _is_primary(source: str) -> bool:
    host = (urlparse(source).hostname or "").lower() if source.startswith(("http://", "https://")) else ""
    return bool(host) and any(host == h or host.endswith("." + h) for h in PRIMARY_HOSTS)


def enforce_sources(claims: list) -> list:
    """Turn a ✅ whose source isn't ours or a primary page into ⚠️, naming the site."""
    for c in claims:
        if c["status"] != "ok" or _is_ours(c["source"]) or _is_primary(c["source"]):
            continue
        host = urlparse(c["source"]).hostname if c["source"].startswith(("http://", "https://")) else ""
        where = host[4:] if host and host.startswith("www.") else host
        c["status"] = "unconfirmed"
        c["note"] = (f"Only confirmed on {where}, which isn't the provider's own page."
                     if where else "No primary source given.")
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


def count_claims(claims: list) -> dict:
    return {s: sum(1 for c in claims if c["status"] == s) for s in ICONS}


def format_markdown(claims: list, pr_note: str = None) -> str:
    """The claims list as the PR body section: problems first, the rest folded away.
    pr_note is None for a check run by hand; in the draft run it's a sentence
    about the send-back pass ("" if there was none)."""
    counts = count_claims(claims)
    flagged = [c for c in claims if c["status"] != "ok"]
    flagged.sort(key=lambda c: 0 if c["status"] == "wrong" else 1)
    confirmed = [c for c in claims if c["status"] == "ok"]

    lines = ["### 🔎 Fact check", ""]
    basis = "Checked against our facts file, our price tracker and the providers' own pages."
    note = f" {pr_note}" if pr_note else ""
    if not claims:
        lines.append("> ⚠️ **No checkable claims came back.** Check every service, price, date and "
                     "channel by hand.")
        return "\n".join(lines)
    if flagged:
        if pr_note is None:
            todo = "Fix or confirm every ❌ and ⚠️ line."
        elif counts["wrong"]:
            todo = ("**Each ❌ line fails the PR check until it's fixed:** correct it, then delete "
                    "`fact_check_wrong` from the post's front matter. Fix or confirm every ⚠️ line "
                    "before merging.")
        else:
            todo = "Fix or confirm every ⚠️ line before merging."
        lines.append(f"**{counts['wrong']} wrong · {counts['unconfirmed']} unconfirmed · "
                     f"{counts['ok']} confirmed.** {basis}{note} {todo}")
        lines += ["", "| | Claim | Where | Note | Source |", "|---|---|---|---|---|"]
        for c in flagged:
            lines.append(f"| {ICONS[c['status']]} | {_cell(c['claim'], 180)} | {WHERE_LABELS[c['where']]} "
                         f"| {_cell(c['note'], 220)} | {_source(c['source'])} |")
    elif pr_note is None:
        lines.append(f"**No problems found in {_claims(counts['ok'])}.** {basis} Anything it "
                     "missed still needs your check.")
    else:
        n = counts["ok"]
        lines.append(f"**{'All ' + str(n) + ' claims were' if n > 1 else 'The one claim was'} confirmed.** {basis}{note}")
    if confirmed:
        lines += ["", "<details>", f"<summary>{len(confirmed)} confirmed {_claims(len(confirmed)).split(' ', 1)[1]}</summary>", "",
                  "| | Claim | Where | Source |", "|---|---|---|---|"]
        for c in confirmed:
            lines.append(f"| ✅ | {_cell(c['claim'], 180)} | {WHERE_LABELS[c['where']]} | {_source(c['source'])} |")
        lines += ["", "</details>"]
    return "\n".join(lines)


def wrong_lines(claims: list) -> list:
    """The ❌ claims as one line each, for the post's fact_check_wrong list."""
    return [f"{WHERE_LABELS[c['where']]}: {c['claim']}" + (f" ({c['note']})" if c["note"] else "")
            for c in claims if c["status"] == "wrong"]


def check_post(post_text: str, social: dict = None, pr_note: str = None) -> dict:
    """Check one post and its social drafts. Returns the claims, their counts, the
    PR body section (markdown), a one-line summary and the number of flagged claims."""
    claims = enforce_sources(parse_claims(call_claude(build_prompt(post_text, social))))
    counts = count_claims(claims)
    return {
        "claims": claims,
        "counts": counts,
        "markdown": format_markdown(claims, pr_note),
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
