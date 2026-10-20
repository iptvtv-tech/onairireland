#!/usr/bin/env python3
"""Ensure price-change news posts lead readers to the canonical tracker."""
from pathlib import Path
import re
import sys
import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
PATTERN = re.compile(r"\b(?:price|prices|pricing)\b", re.I)
errors = []
checked = 0
for path in sorted(POSTS.glob("*.md")):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        continue
    try:
        front_matter = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        continue
    title = str(front_matter.get("title", ""))
    cats = front_matter.get("categories") or []
    if cats and cats[0] == "News" and PATTERN.search(title):
        checked += 1
        if "/streaming-prices/" not in text:
            errors.append(f"{path.name}: price-news post is missing a link to /streaming-prices/")
for error in errors:
    print(f"ERROR: {error}")
print(f"Checked price-news links: {checked} post(s), {len(errors)} error(s)")
sys.exit(1 if errors else 0)
