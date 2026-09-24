#!/usr/bin/env python3
"""Builds _data/sport_week.yml: the big live sport on Irish TV and streaming
services for the next seven days (Friday to Thursday).

Run by .github/workflows/weekly-sport-guide.yml every Thursday. It opens a pull
request, so nothing goes live until you've checked it and merged.

Uses Claude with web search so every listing comes from a current source
(broadcaster schedules, GAA/IRFU/FAI fixture lists, RTÉ/Virgin Media/Sky/TNT
listings). Needs the ANTHROPIC_API_KEY repo secret (already used by the daily
post workflow).

Usage:
    python scripts/generate_sport_week.py              # week starting next Friday
    python scripts/generate_sport_week.py 2026-10-02   # week starting on that date
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml

OUT = Path("_data/sport_week.yml")
TZ_NOTE = "Irish time (Europe/Dublin)"

SPORTS = ["GAA", "Rugby", "Football", "Golf", "Racing", "Boxing", "Cricket",
          "Tennis", "Motorsport", "Athletics", "Cycling", "Other"]

HEADER = """# "Sport on TV this week" data, shown on /sport-on-tv/.
# Written every Thursday by scripts/generate_sport_week.py (GitHub Action
# "Weekly Sport Guide"), which opens a pull request for you to check.
# Leave events empty to show the "coming soon" message.
"""


def week_range(argv):
    if len(argv) > 1:
        start = dt.date.fromisoformat(argv[1])
    else:
        today = dt.date.today()
        days_to_friday = (4 - today.weekday()) % 7 or 7
        start = today + dt.timedelta(days=days_to_friday)
    return start, start + dt.timedelta(days=6)


def build_prompt(start, end):
    return f"""You are compiling a weekly "Sport on TV" listing for an Irish website
about LEGAL streaming. Research, with web search, the notable live sport that
viewers in the Republic of Ireland can watch between {start:%A %d %B %Y} and
{end:%A %d %B %Y} inclusive, and where to watch each one legally.

Cover, where there is anything on: GAA (football, hurling, camogie, ladies
football, club championships), Ireland rugby internationals, URC games with
Leinster/Munster/Ulster/Connacht, Champions Cup, Ireland football
internationals, League of Ireland, Premier League, Champions League, Europa
League, major golf with Irish players, major horse racing meetings, big boxing
nights with Irish fighters, and any other major event Irish viewers care about.
Aim for 10-25 of the most important events, not every match.

Rules:
- Only list an event if you found a current source for its date AND for the
  broadcaster/streaming service showing it in Ireland. Irish rights often differ
  from the UK: check Irish sources (RTÉ, Virgin Media Television, TG4, Premier
  Sports, Sky Sports, TNT Sports, GAA+, LOITV, NOW, Prime Video, DAZN).
- If you can confirm the event and date but not the Irish broadcaster, leave it out.
- Times are {TZ_NOTE}, 24-hour HH:MM. Use "TBC" if the time isn't confirmed.
- "free" is true only when the event is on a free-to-air channel or free app
  (RTÉ, Virgin Media One/Two, TG4, RTÉ Player, Virgin Media Play, TG4 Player).
- Never mention VPNs, unofficial streams or anything unlicensed.
- "sport" must be one of: {", ".join(SPORTS)}.

Return ONLY a JSON object between <json> and </json> tags, no commentary:
<json>
{{"events": [
  {{"date": "YYYY-MM-DD", "time": "HH:MM", "sport": "GAA",
    "event": "Kilkenny v Galway", "competition": "Leinster Senior Hurling Championship",
    "watch": "RTÉ 2 and RTÉ Player", "free": true,
    "source": "https://... the page confirming the broadcaster"}}
]}}
</json>"""


def call_claude(prompt):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-5",
            "max_tokens": 8000,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 20}],
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=600,
    )
    if not resp.ok:
        print(f"Anthropic API error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def parse_events(raw, start, end):
    m = re.search(r"<json>\s*(\{.*\})\s*</json>", raw, re.S) or re.search(r"(\{\s*\"events\".*\})", raw, re.S)
    if not m:
        sys.exit("No JSON found in the response:\n" + raw[:2000])
    events = json.loads(m.group(1)).get("events", [])

    clean, dropped = [], []
    for e in events:
        try:
            d = dt.date.fromisoformat(str(e["date"]))
        except (KeyError, ValueError):
            dropped.append((e, "bad date"))
            continue
        if not start <= d <= end:
            dropped.append((e, "outside the week"))
            continue
        missing = [k for k in ("event", "competition", "watch", "source") if not str(e.get(k, "")).strip()]
        if missing:
            dropped.append((e, "missing " + ", ".join(missing)))
            continue
        if not str(e["source"]).startswith("http"):
            dropped.append((e, "source is not a link"))
            continue
        text = " ".join(str(v) for v in e.values()).lower()
        if "vpn" in text or "iptv" in text:
            dropped.append((e, "mentions VPN/IPTV"))
            continue
        time = str(e.get("time", "TBC")).strip()
        if not re.fullmatch(r"\d{2}:\d{2}", time):
            time = "TBC"
        sport = e.get("sport") if e.get("sport") in SPORTS else "Other"
        clean.append({
            "date": d,
            "time": time,
            "sport": sport,
            "event": str(e["event"]).strip(),
            "competition": str(e["competition"]).strip(),
            "watch": str(e["watch"]).strip(),
            "free": bool(e.get("free")),
            "source": str(e["source"]).strip(),
        })

    clean.sort(key=lambda x: (x["date"], x["time"] if x["time"] != "TBC" else "99:99"))
    for e, why in dropped:
        print(f"Dropped ({why}): {e}")
    return clean


def main():
    start, end = week_range(sys.argv)
    print(f"Building sport listings for {start} to {end}")
    raw = call_claude(build_prompt(start, end))
    events = parse_events(raw, start, end)
    if len(events) < 3:
        sys.exit(f"Only {len(events)} usable events found; not overwriting {OUT}. Response was:\n{raw[:3000]}")

    data = {
        "week_start": start,
        "week_end": end,
        "generated": dt.date.today(),
        "events": events,
    }
    OUT.write_text(HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    print(f"Wrote {len(events)} events to {OUT}")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"week_label={start:%-d %b} to {end:%-d %b %Y}\n")
            fh.write(f"event_count={len(events)}\n")


if __name__ == "__main__":
    main()
