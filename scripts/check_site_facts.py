#!/usr/bin/env python3
"""
Validate _data/site_facts.yml. Run by check-pr.yml.

The draft writer may only say who shows a competition, or what a membership
includes, from this file, so a broken entry has to be caught before it reaches
a draft. Fails (exit 1) on errors: a missing topic, no facts, a source that
isn't a link, or a bad checked date. Warns when an entry hasn't been confirmed
for STALE_DAYS, so an overdue quarterly check shows up on every PR.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402

import site_facts  # noqa: E402

STALE_DAYS = 100  # a quarter plus a little slack, as in check_prices_data.py


def main() -> int:
    with open(site_facts.FACTS_PATH, encoding="utf-8") as f:
        entries = yaml.safe_load(f) or []

    errors = site_facts.entry_problems(entries)
    warnings = []
    if not errors:
        today = datetime.date.today()
        for e in entries:
            age = (today - site_facts.as_date(e["checked"])).days
            if age > STALE_DAYS:
                warnings.append(f"{e['topic']}: last checked {age} days ago")
            if age < 0:
                errors.append(f"{e['topic']}: checked date is in the future")

    for line in errors:
        print(f"ERROR: {line}")
    for line in warnings:
        print(f"WARNING: {line}")
    print(f"Checked site facts: {len(entries) if isinstance(entries, list) else 0} topics, "
          f"{len(errors)} error(s), {len(warnings)} stale warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
