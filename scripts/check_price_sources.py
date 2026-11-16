#!/usr/bin/env python3
"""Guard price data against unapproved, non-primary source domains.
The allowlist lives in price_rules.py, shared with the offers check."""
from pathlib import Path
from urllib.parse import urlparse
import sys
import yaml

from price_rules import is_approved

ROOT = Path(__file__).resolve().parent.parent
PRICES = ROOT / "_data" / "prices.yml"

try:
    rows = yaml.safe_load(PRICES.read_text(encoding="utf-8")) or []
except yaml.YAMLError as exc:
    print(f"ERROR: invalid _data/prices.yml: {exc}")
    sys.exit(1)
errors = []
for row in rows:
    name = f"{row.get('service', '?')} / {row.get('plan', '?')}"
    url = str(row.get("url", ""))
    host = urlparse(url).hostname or ""
    if not url.startswith("https://") or not host:
        errors.append(f"{name}: missing a valid HTTPS source URL")
    elif not is_approved(host):
        errors.append(f"{name}: source host {host!r} is not on the primary-source allowlist; verify the provider source or update the allowlist with evidence")
for error in errors:
    print(f"ERROR: {error}")
print(f"Checked price sources: {len(rows)} plan(s), {len(errors)} issue(s)")
sys.exit(1 if errors else 0)
