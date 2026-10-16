#!/usr/bin/env python3
"""
Quarterly price check for _data/prices.yml.

For each paid service listed in _data/price_sources.yml, Claude reads the
provider's OWN website (web search and fetch are limited to the domains in that
file) and reports the current Irish euro price for each plan, with a word-for-
word quote and the page it came from.

Safeguards -- nothing here publishes anything:
  * A price is only used if its quote, including the euro amount, appears in
    the text of a page Claude actually fetched in this run. This script checks
    that itself; Claude's word alone is never enough.
  * Changes larger than MAX_CHANGE (35%) are NOT applied; they are listed for
    a manual check.
  * Anything not confirmed is left exactly as it is and listed in the report.
  * The workflow opens a PR. Prices only change on the site when you merge it.
  * If nothing at all could be confirmed, or most services failed, the script
    exits with an error so the workflow fails and GitHub emails you.

Writes the report to $PRICE_REPORT_PATH (used as the PR body).
"""
import datetime
import json
import os
import re
import sys

import requests
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_PATH = os.path.join(ROOT, "_data", "prices.yml")
SOURCES_PATH = os.path.join(ROOT, "_data", "price_sources.yml")
REPORT_PATH = os.environ.get("PRICE_REPORT_PATH", "/tmp/price_check_report.md")

MAX_CHANGE = 0.35          # fractional change above which nothing is applied
MAX_QUOTE_CHARS = 300

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_social import MODEL  # noqa: E402  one place to change the model

# Field order used when a field has to be added to a plan in prices.yml.
FIELD_ORDER = ["service", "plan", "monthly", "yearly", "note", "changed",
               "checked", "source", "url", "group", "combinable"]


# ---------------------------------------------------------------------------
# Claude call
# ---------------------------------------------------------------------------

def build_prompt(service, plans, cfg):
    lines = []
    for p in plans:
        parts = []
        if p.get("monthly") is not None:
            parts.append(f"monthly €{p['monthly']:.2f}")
        if p.get("yearly") is not None:
            parts.append(f"yearly €{p['yearly']:.2f}")
        lines.append(f"- {p['plan']}: {', '.join(parts) or 'no price listed'}")
    urls = "\n".join(f"- {u}" for u in cfg.get("start_urls", []))
    return f"""You are checking Irish streaming prices for On Air Ireland, an independent
site about legal streaming in Ireland.

Service: {service}
Find the CURRENT standard price in euro for customers in Ireland for each plan
below, using only the provider's own website. Fetch these pages first:
{urls}
If they don't show Irish euro prices, search the provider's site.

Plans we list now (our current figures, which may be out of date):
{chr(10).join(lines)}

Rules:
- Only report a price you read on a page you fetched with web_fetch in this conversation.
- For each price, copy `quote` WORD FOR WORD from that fetched page: a short passage
  (under {MAX_QUOTE_CHARS} characters) that contains the € amount exactly as the page shows it.
- Standard prices only. Not introductory offers, trials, discounts or bundles. If only an
  offer price is shown, report null and say so in notes.
- Euro prices for Ireland only. Never convert from another currency. If a page shows another
  country's prices, report null.
- monthly = price per month. yearly = price per year (annual plan or season pass).
- If you can't find a plan or price, report null for it.

Return ONLY this JSON between <result> and </result>:
<result>
{{"plans": [{{"plan": "<plan name exactly as in our list>",
             "monthly": {{"price": 0.00, "source_url": "<fetched page>", "quote": "<verbatim>"}} or null,
             "yearly":  {{"price": 0.00, "source_url": "<fetched page>", "quote": "<verbatim>"}} or null}}],
 "new_plans": [{{"plan": "<name>", "monthly": 0.00 or null, "yearly": 0.00 or null, "source_url": "<page>"}}],
 "notes": "<one or two sentences>"}}
</result>"""


def call_claude(prompt, domains):
    """Run one conversation (following pause_turn) and return all content blocks."""
    tools = [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 3,
         "allowed_domains": domains,
         "user_location": {"type": "approximate", "country": "IE", "timezone": "Europe/Dublin"}},
        {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 6,
         "allowed_domains": domains, "max_content_tokens": 40000},
    ]
    messages = [{"role": "user", "content": prompt}]
    blocks = []
    for _ in range(4):
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": MODEL, "max_tokens": 3000, "messages": messages, "tools": tools},
            timeout=300,
        )
        if not resp.ok:
            raise RuntimeError(f"API error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        blocks.extend(data.get("content", []))
        if data.get("stop_reason") != "pause_turn":
            return blocks
        messages.append({"role": "assistant", "content": data["content"]})
    return blocks


# ---------------------------------------------------------------------------
# Evidence checks
# ---------------------------------------------------------------------------

def norm_text(s: str) -> str:
    s = s.replace(" ", " ").replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def norm_url(u: str) -> str:
    u = (u or "").strip().lower().split("#")[0]
    u = re.sub(r"^https?://(www\.)?", "", u)
    return u.rstrip("/")


def fetched_pages(blocks) -> dict:
    """url -> normalised page text, for every successful web_fetch."""
    pages = {}
    for b in blocks:
        if b.get("type") != "web_fetch_tool_result":
            continue
        c = b.get("content") or {}
        if c.get("type") != "web_fetch_result":
            continue
        src = (c.get("content") or {}).get("source") or {}
        if src.get("type") == "text" and src.get("data"):
            pages[norm_url(c.get("url", ""))] = norm_text(src["data"])
    return pages


def final_text(blocks) -> str:
    return "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def parse_result(text: str):
    m = re.search(r"<result>\s*(.*?)\s*</result>", text, re.S)
    if not m:
        return None
    raw = m.group(1).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def amount_in(quote: str, price: float) -> bool:
    """True if the quote shows this euro amount (€11.99, € 11,99, 11.99 €, 11.99 EUR, €95)."""
    variants = {f"{price:.2f}", f"{price:.2f}".replace(".", ",")}
    if abs(price - round(price)) < 0.005:
        variants.add(str(int(round(price))))
    q = norm_text(quote)
    for v in variants:
        v = re.escape(v)
        if re.search(rf"€\s?{v}(?![\d.,]*\d)|(?<![\d.,]){v}\s?(€|eur\b)", q):
            return True
    return False


def verify(evidence, pages):
    """Return (ok, reason) for one reported price."""
    if not isinstance(evidence, dict) or evidence.get("price") is None:
        return False, "not found on the provider's site"
    try:
        price = float(evidence["price"])
    except (TypeError, ValueError):
        return False, "price was not a number"
    quote = str(evidence.get("quote") or "")
    if not quote or len(quote) > MAX_QUOTE_CHARS:
        return False, "no usable quote"
    if not amount_in(quote, price):
        return False, f"quote doesn't show €{price:.2f}"
    page = pages.get(norm_url(evidence.get("source_url", "")))
    if page is None:
        return False, "source page wasn't fetched in this run"
    if norm_text(quote) not in page:
        return False, "quote not found word for word on the fetched page"
    return True, ""


# ---------------------------------------------------------------------------
# Editing prices.yml as text (keeps comments and layout)
# ---------------------------------------------------------------------------

def scalar(line: str):
    try:
        return yaml.safe_load(line.split(":", 1)[1])
    except Exception:
        return None


def find_block(lines, service, plan):
    for i, line in enumerate(lines[:-1]):
        if line.startswith("- service:") and scalar(line) == service \
                and lines[i + 1].strip().startswith("plan:") and scalar(lines[i + 1]) == plan:
            j = i + 1
            while j < len(lines) and lines[j].startswith("  ") and lines[j].strip():
                j += 1
            return i, j
    return None


def fmt(key, value):
    if isinstance(value, float):
        return f"  {key}: {value:.2f}\n"
    if isinstance(value, datetime.date):
        return f"  {key}: {value.isoformat()}\n"
    dumped = yaml.safe_dump({key: value}, allow_unicode=True, width=1000, sort_keys=False)
    return "  " + dumped.split("\n...")[0].rstrip("\n") + "\n"


def set_field(lines, service, plan, key, value):
    start, end = find_block(lines, service, plan)
    keys = {}
    for k in range(start, end):
        m = re.match(r"^(?:- |  )(\w+):", lines[k])
        if m:
            keys[m.group(1)] = k
    new_line = fmt(key, value)
    if start == keys.get(key):  # never rewrite the "- service:" line itself
        return
    if key in keys:
        lines[keys[key]] = new_line
        return
    pos = start + 1
    for earlier in FIELD_ORDER[:FIELD_ORDER.index(key)]:
        if earlier in keys:
            pos = max(pos, keys[earlier] + 1)
    lines.insert(pos, new_line)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def money(v):
    return "–" if v is None else f"€{v:.2f}"


def link(url):
    return f"[source]({url})" if url else ""


def check_service(service, plans, cfg, today):
    """Return a list of per-plan outcomes and a list of possible new plans."""
    blocks = call_claude(build_prompt(service, plans, cfg), cfg["domains"])
    pages = fetched_pages(blocks)
    result = parse_result(final_text(blocks))
    if result is None:
        raise RuntimeError("no parsable <result> JSON in the reply")

    found = {str(p.get("plan", "")).strip().lower(): p for p in result.get("plans", [])}
    outcomes = []
    for row in plans:
        rep = found.get(row["plan"].strip().lower(), {})
        out = {"service": service, "plan": row["plan"], "row": row, "fields": {},
               "problems": [], "notes": result.get("notes", "")}
        for field in ("monthly", "yearly"):
            ev = rep.get(field)
            current = row.get(field)
            if ev is None and current is None:
                continue
            ok, reason = verify(ev, pages)
            if not ok:
                if current is not None:
                    out["problems"].append(f"{field}: {reason}")
                continue
            new = round(float(ev["price"]), 2)
            out["fields"][field] = {"old": current, "new": new,
                                    "url": ev.get("source_url"), "quote": ev.get("quote")}
        outcomes.append(out)
    return outcomes, result.get("new_plans", []) or []


def classify(out):
    """confirmed | changed | large | unverified"""
    if out["problems"] or not out["fields"]:
        return "unverified"
    changed = False
    for f in out["fields"].values():
        old, new = f["old"], f["new"]
        if old is None:
            changed = True
            continue
        if abs(old - new) >= 0.005:
            changed = True
            if old == 0 or abs(new - old) / old > MAX_CHANGE:
                return "large"
    return "changed" if changed else "confirmed"


def main():
    today = datetime.date.today()
    with open(PRICES_PATH, encoding="utf-8") as f:
        text = f.read()
    rows = yaml.safe_load(text) or []
    with open(SOURCES_PATH, encoding="utf-8") as f:
        sources = yaml.safe_load(f) or {}

    by_service = {}
    for r in rows:
        by_service.setdefault(r["service"], []).append(r)

    outcomes, new_plans, not_checked, errors = [], [], [], []
    to_check = []
    for service, plans in by_service.items():
        cfg = sources.get(service)
        if all(p.get("group") == "free" and not p.get("yearly") for p in plans):
            not_checked.append((service, "free service"))
        elif not cfg or cfg.get("skip"):
            not_checked.append((service, "no entry in _data/price_sources.yml" if not cfg else "skip: true"))
        else:
            to_check.append((service, plans, cfg))

    for service, plans, cfg in to_check:
        print(f"Checking {service}...")
        try:
            outs, extra = check_service(service, plans, cfg, today)
            outcomes.extend(outs)
            new_plans.extend((service, p) for p in extra)
        except Exception as exc:  # one failure never stops the others
            print(f"  failed: {exc}")
            errors.append((service, str(exc)))
            for p in plans:
                outcomes.append({"service": service, "plan": p["plan"], "row": p, "fields": {},
                                 "problems": [f"check failed: {exc}"[:200]], "notes": ""})

    # Apply only confirmed and changed plans.
    lines = text.splitlines(keepends=True)
    groups = {"confirmed": [], "changed": [], "large": [], "unverified": []}
    for out in outcomes:
        kind = classify(out)
        groups[kind].append(out)
        if kind not in ("confirmed", "changed"):
            continue
        src_cfg = sources.get(out["service"], {})
        url = next((f["url"] for f in out["fields"].values() if f.get("url")), None)
        for field, f in out["fields"].items():
            set_field(lines, out["service"], out["plan"], field, float(f["new"]))
        if kind == "changed":
            set_field(lines, out["service"], out["plan"], "changed", today)
        set_field(lines, out["service"], out["plan"], "checked", today)
        set_field(lines, out["service"], out["plan"], "source",
                  src_cfg.get("source_name", out["service"]))
        if url:
            set_field(lines, out["service"], out["plan"], "url", url)

    new_text = "".join(lines)
    yaml.safe_load(new_text)  # never write a file that doesn't parse
    if new_text != text:
        with open(PRICES_PATH, "w", encoding="utf-8") as f:
            f.write(new_text)

    write_report(today, groups, new_plans, not_checked, errors)

    verified = len(groups["confirmed"]) + len(groups["changed"])
    print(f"Confirmed {len(groups['confirmed'])}, changed {len(groups['changed'])}, "
          f"large {len(groups['large'])}, unverified {len(groups['unverified'])}, "
          f"service errors {len(errors)}")
    if verified == 0:
        print("ERROR: no price could be confirmed. Check the API key, model and price_sources.yml.")
        sys.exit(1)
    if to_check and len(errors) * 2 >= len(to_check):
        print("ERROR: half or more of the services failed. See the log above.")
        sys.exit(1)


def write_report(today, groups, new_plans, not_checked, errors):
    q = (today.month - 1) // 3 + 1
    out = [f"Automated quarterly price check for Q{q} {today.year}, run {today.isoformat()}. "
           "Prices were read from each provider's own website. A price was only used when "
           "its quote, including the € amount, was found word for word on a page fetched in this run.",
           "",
           "**Merging this PR updates /streaming-prices/ and the cost calculator live.**",
           "",
           "Before merging:",
           "- [ ] Open each link under *Price changes* and confirm the plan, the price and that it's the Irish price",
           "- [ ] Work through *Check by hand* and edit `_data/prices.yml` in this PR where needed",
           "- [ ] Update any hub page or post that quotes a changed price",
           "- [ ] The quarterly review post (if drafted) matches these figures",
           ""]

    out.append(f"## Price changes ({len(groups['changed'])})")
    if groups["changed"]:
        out += ["", "| Service | Plan | Was | Now | Evidence |", "| --- | --- | --- | --- | --- |"]
        for o in groups["changed"]:
            for field, f in o["fields"].items():
                if f["old"] is None or abs(f["old"] - f["new"]) >= 0.005:
                    quote = str(f["quote"]).replace("|", "/")[:160]
                    out.append(f"| {o['service']} | {o['plan']} ({field}) | {money(f['old'])} | "
                               f"{money(f['new'])} | \"{quote}\" {link(f['url'])} |")
    else:
        out.append("\nNone.")
    out.append("")

    hand = groups["large"] + groups["unverified"]
    out.append(f"## Check by hand — not changed ({len(hand)})")
    if hand:
        out += ["", "| Service | Plan | Our figure | Why | What the checker saw |",
                "| --- | --- | --- | --- | --- |"]
        for o in groups["large"]:
            for field, f in o["fields"].items():
                if f["old"] is not None and abs(f["old"] - f["new"]) >= 0.005:
                    out.append(f"| {o['service']} | {o['plan']} ({field}) | {money(f['old'])} | "
                               f"Change over {int(MAX_CHANGE * 100)}% | {money(f['new'])} {link(f['url'])} |")
        for o in groups["unverified"]:
            row = o["row"]
            parts = []
            if row.get("monthly") is not None:
                parts.append(f"{money(row['monthly'])}/mo")
            if row.get("yearly") is not None:
                parts.append(f"{money(row['yearly'])}/yr")
            ours = ", ".join(parts)
            why = "; ".join(o["problems"]) or "not found"
            out.append(f"| {o['service']} | {o['plan']} | {ours or '–'} | {why} | {link(row.get('url'))} |")
    else:
        out.append("\nNone.")
    out.append("")

    out.append(f"## Confirmed unchanged ({len(groups['confirmed'])})")
    if groups["confirmed"]:
        out.append("")
        out.append("`checked` set to today and the source moved to the provider's own page.")
        out.append("")
        for o in groups["confirmed"]:
            url = next((f["url"] for f in o["fields"].values() if f.get("url")), "")
            prices = ", ".join(f"{money(f['new'])} {k}" for k, f in o["fields"].items())
            out.append(f"- {o['service']} {o['plan']}: {prices} {link(url)}")
    else:
        out.append("\nNone.")
    out.append("")

    if new_plans:
        out.append("## Plans on the provider's site we don't list (not added)")
        out.append("")
        for service, p in new_plans:
            prices = ", ".join(f"{money(p.get(k))} {k}" for k in ("monthly", "yearly") if p.get(k) is not None)
            out.append(f"- {service} {p.get('plan', '?')}: {prices or 'no price'} {link(p.get('source_url'))}")
        out.append("")

    if not_checked:
        out.append("## Not checked automatically")
        out.append("")
        for service, why in not_checked:
            out.append(f"- {service} ({why})")
        out.append("")

    if errors:
        out.append("## Errors")
        out.append("")
        for service, err in errors:
            out.append(f"- {service}: {err[:200]}")
        out.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
