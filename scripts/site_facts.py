#!/usr/bin/env python3
"""
Checked facts and prices, as plain text for the draft writer and the fact check.

_data/site_facts.yml holds who shows each competition in Ireland and what the
NOW sport memberships include. _data/prices.yml holds the checked prices.
generate_post.py and fact_check.py both build their prompts from here, so the
writer and the checker always see exactly the same facts.

Not run on its own: scripts/check_site_facts.py validates the facts file.
"""
import datetime
import os

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS_PATH = os.path.join(REPO_ROOT, "_data", "site_facts.yml")
PRICES_PATH = os.path.join(REPO_ROOT, "_data", "prices.yml")


def as_date(value):
    """A checked: value as a date (YAML may already have parsed it)."""
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))


def entry_problems(entries) -> list:
    """Everything wrong with the facts file's entries, as readable lines."""
    if not isinstance(entries, list):
        return ["the file must be a list of entries"]
    problems = []
    for i, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            problems.append(f"entry {i}: not a topic entry")
            continue
        where = f"entry {i} ({e.get('topic') or 'no topic'})"
        if not str(e.get("topic") or "").strip():
            problems.append(f"{where}: missing topic")
        facts = e.get("facts")
        if not isinstance(facts, list) or not facts or not all(isinstance(f, str) and f.strip() for f in facts):
            problems.append(f"{where}: facts must be a list of sentences")
        sources = e.get("source")
        sources = [sources] if isinstance(sources, str) else sources
        if not isinstance(sources, list) or not sources or not all(str(s).startswith("https://") for s in sources):
            problems.append(f"{where}: source must be one or more https:// links")
        try:
            as_date(e.get("checked"))
        except (TypeError, ValueError):
            problems.append(f"{where}: checked must be a date (YYYY-MM-DD)")
        guide = e.get("guide")
        if guide is not None and not str(guide).startswith("/"):
            problems.append(f"{where}: guide must be a site path starting with /")
    return problems


def load_facts(path=FACTS_PATH) -> list:
    """Load _data/site_facts.yml. Raises ValueError if any entry is malformed,
    so a broken facts file stops the draft instead of letting the writer fall
    back on memory."""
    with open(path, encoding="utf-8") as f:
        entries = yaml.safe_load(f) or []
    problems = entry_problems(entries)
    if problems:
        raise ValueError("_data/site_facts.yml: " + "; ".join(problems))
    return entries


def facts_for_prompt(entries=None) -> str:
    """The checked facts as plain text, one topic per block."""
    entries = load_facts() if entries is None else entries
    blocks = []
    for e in entries:
        lines = [f"{e['topic']} (checked {as_date(e['checked']).isoformat()}):"]
        lines += [f"- {fact.strip()}" for fact in e["facts"]]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _euro(amount) -> str:
    amount = float(amount)
    return f"€{amount:.0f}" if amount.is_integer() else f"€{amount:.2f}"


def prices_for_prompt(plans=None) -> str:
    """The price tracker's plans as plain text, with the date each was checked."""
    if plans is None:
        with open(PRICES_PATH, encoding="utf-8") as f:
            plans = yaml.safe_load(f) or []
    lines = []
    for p in plans:
        plan = p.get("plan")
        name = p["service"] if plan in (None, "", "Free", p["service"]) else f"{p['service']} ({plan})"
        monthly, yearly = p.get("monthly"), p.get("yearly")
        if monthly is not None and float(monthly) == 0 and not yearly:
            cost = "free"
        else:
            parts = []
            if monthly is not None:
                parts.append(f"{_euro(monthly)} a month")
            if yearly is not None:
                parts.append(f"{_euro(yearly)} a year")
            cost = " or ".join(parts) or "price not listed"
        note = f". {p['note'].strip().rstrip('.')}" if p.get("note") else ""
        checked = f" (checked {as_date(p['checked']).isoformat()})" if p.get("checked") else ""
        lines.append(f"- {name}: {cost}{note}{checked}")
    return "\n".join(lines)
