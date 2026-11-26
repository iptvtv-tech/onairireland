#!/usr/bin/env python3
"""Validates _data/prices.yml. Run by check-pr.yml and the quarterly price check.

Fails (exit 1) on errors that would break /streaming-prices/ or the calculator.
Warns when a price hasn't been confirmed for STALE_DAYS, so an overdue
quarterly check shows up on every PR."""
import datetime
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import price_rules  # noqa: E402

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
_products_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_data", "products.yml")
with open(_products_path, encoding="utf-8") as _f:
    PRODUCT_IDS = {str(p.get("id")) for p in (yaml.safe_load(_f) or []) if isinstance(p, dict)}

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
    if r.get("evidence") not in (None, ""):
        # Optional here (the quarterly checker fills it in), but when it's there
        # it must be the provider's own words showing one of the row's prices.
        problem = price_rules.evidence_problem(r["evidence"], [r.get(k) for k in price_rules.PRICE_FIELDS])
        if problem:
            errors.append(f"{name}: {problem}")
    aff = r.get("affiliate")
    if aff is not None and str(aff) not in PRODUCT_IDS:
        errors.append(f"{name}: affiliate {aff!r} is not an id in _data/products.yml")
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

# Time-limited offers (_data/offers.yml): provider sources, a show_until date
# no more than three weeks after the check, and a real discount on a tracked plan.
try:
    offers = price_rules.load_offers()
except yaml.YAMLError as e:
    offers = []
    errors.append(f"_data/offers.yml is not valid YAML: {e}")
offer_errors, offer_warnings = price_rules.offer_problems(offers, rows, today, price_rules.is_approved)
errors += offer_errors
stale_count = len(warnings)
warnings += offer_warnings

for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)
print(f"Checked prices: {len(rows)} plans and {len(offers)} offer(s), {len(errors)} error(s), {len(warnings)} warning(s)")
if stale_count and os.environ.get("GITHUB_ACTIONS"):
    print(f"::warning title=Prices overdue::{stale_count} price(s) not confirmed in {STALE_DAYS} days. "
          "Run the Quarterly Price Check workflow.")
if offer_warnings and os.environ.get("GITHUB_ACTIONS"):
    print(f"::warning title=Offers ended::{len(offer_warnings)} offer(s) in _data/offers.yml have ended; remove or re-check them.")
sys.exit(1 if errors else 0)
