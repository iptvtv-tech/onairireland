#!/usr/bin/env python3
"""Validates _data/prices.yml. Run by check-pr.yml and the quarterly price check.

Fails (exit 1) on errors that would break /streaming-prices/ or the calculator.
Warns when a price hasn't been confirmed for STALE_DAYS, so an overdue
quarterly check shows up on every PR."""
import datetime
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES = os.path.join(ROOT, "_data", "prices.yml")
GROUPS = {"general", "film-tv", "sport", "free"}
STALE_DAYS = 100   # a quarter plus a week or so of slack
MAX_PRICE = 500    # anything higher is almost certainly a typo

errors, warnings = [], []
try:
    rows = yaml.safe_load(open(PRICES, encoding="utf-8")) or []
except yaml.YAMLError as e:
    print(f"ERROR: _data/prices.yml is not valid YAML: {e}")
    sys.exit(1)

today = datetime.date.today()
seen = set()
for i, r in enumerate(rows, 1):
    if not isinstance(r, dict):
        errors.append(f"entry {i}: not a mapping")
        continue
    name = f"{r.get('service', '?')} / {r.get('plan', '?')}"
    for key in ("service", "plan", "group", "checked"):
        if not r.get(key) and r.get(key) != 0:
            errors.append(f"{name}: missing {key}")
    if (r.get("service"), r.get("plan")) in seen:
        errors.append(f"{name}: listed twice")
    seen.add((r.get("service"), r.get("plan")))
    if r.get("group") and r["group"] not in GROUPS:
        errors.append(f"{name}: unknown group {r['group']!r}")
    if r.get("monthly") is None and r.get("yearly") is None:
        errors.append(f"{name}: needs monthly or yearly")
    for key in ("monthly", "yearly"):
        v = r.get(key)
        if v is not None and (not isinstance(v, (int, float)) or v < 0 or v > MAX_PRICE):
            errors.append(f"{name}: {key} {v!r} is not a sensible euro amount")
    url = r.get("url")
    if url and not str(url).startswith("https://"):
        errors.append(f"{name}: url should start with https://")
    for key in ("checked", "changed"):
        v = r.get(key)
        if v is None:
            continue
        if not isinstance(v, datetime.date):
            errors.append(f"{name}: {key} must be a YYYY-MM-DD date")
        elif v > today:
            errors.append(f"{name}: {key} {v} is in the future")
    checked = r.get("checked")
    if isinstance(checked, datetime.date) and (today - checked).days > STALE_DAYS:
        warnings.append(f"{name}: last checked {checked} ({(today - checked).days} days ago)")

for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)
print(f"Checked prices: {len(rows)} plans, {len(errors)} error(s), {len(warnings)} stale warning(s)")
if warnings and os.environ.get("GITHUB_ACTIONS"):
    print(f"::warning title=Prices overdue::{len(warnings)} price(s) not confirmed in {STALE_DAYS} days. "
          "Run the Quarterly Price Check workflow.")
sys.exit(1 if errors else 0)
