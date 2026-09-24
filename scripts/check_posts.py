#!/usr/bin/env python3
"""Validates every post's front matter. Run by .github/workflows/check-pr.yml.
Fails (exit 1) on errors; prints warnings for things worth fixing."""
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "_posts")
VALID_CATEGORIES = {
    "Streaming-Services", "Devices", "Installation-Guides", "News",
    "Reviews", "Sports-Streaming", "Troubleshooting", "Watch-Guides",
}

errors, warnings = [], []
for name in sorted(os.listdir(POSTS)):
    if not name.endswith(".md"):
        continue
    path = os.path.join(POSTS, name)
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        errors.append(f"{name}: missing front matter block")
        continue
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        errors.append(f"{name}: invalid YAML front matter: {e}")
        continue
    body = m.group(2)

    title = str(fm.get("title", "")).strip()
    if not title:
        errors.append(f"{name}: no title")
    elif title.lower().startswith("title:"):
        errors.append(f"{name}: title starts with 'title:' ({title!r})")
    cats = fm.get("categories") or []
    if not cats:
        errors.append(f"{name}: no category")
    elif cats[0] not in VALID_CATEGORIES:
        errors.append(f"{name}: unknown category {cats[0]!r}")
    desc = str(fm.get("description", "") or "")
    if not desc:
        warnings.append(f"{name}: no description")
    elif len(desc) > 160:
        warnings.append(f"{name}: description is {len(desc)} chars (aim for <= 155)")
    if "AFFILIATE_LINK_" in body or "TODO" in body:
        errors.append(f"{name}: contains a placeholder (AFFILIATE_LINK_ or TODO)")
    for url in re.findall(r"(?:overlay_image|teaser):\s*(\S+)", m.group(1)):
        if url.startswith("/") and not os.path.exists(os.path.join(ROOT, url.lstrip("/"))):
            errors.append(f"{name}: image not found: {url}")
        if url.endswith(")"):
            errors.append(f"{name}: image URL ends with ')': {url}")

for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)
print(f"Checked posts: {len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(1 if errors else 0)
