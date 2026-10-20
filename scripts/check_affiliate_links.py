#!/usr/bin/env python3
"""Check that affiliate links are disclosed and marked rel=sponsored."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIRS = (ROOT / "_posts", ROOT / "_pages")
AFFILIATE_URL = re.compile(r"https?://(?:amzn\.to|link\.amazon)(?:/[^\s)\]\"'<>]*)?", re.I)
MARKDOWN_LINK = re.compile(
    r"\[[^\]\n]+\]\((https?://(?:amzn\.to|link\.amazon)[^\s)]+)\)(\s*\{:[^}]*\})?",
    re.I,
)
HTML_ANCHOR = re.compile(r"<a\b[^>]*href=[\"'](https?://(?:amzn\.to|link\.amazon)[^\"']*)[\"'][^>]*>", re.I | re.S)
SPONSORED_REL = re.compile(r"\brel\s*=\s*([\"'])([^\"']*)\1", re.I)
errors = []
checked_links = 0
checked_posts = 0


def has_sponsored_attribute(attributes: str) -> bool:
    for match in SPONSORED_REL.finditer(attributes):
        rel_values = set(match.group(2).lower().split())
        if "sponsored" in rel_values:
            return True
    return False


for directory in CONTENT_DIRS:
    if not directory.is_dir():
        continue
    for path in sorted(directory.rglob("*")):
        if path.suffix.lower() not in {".md", ".markdown", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        found_links = []

        for match in MARKDOWN_LINK.finditer(text):
            found_links.append((match.group(1), match.group(2) or "", match.start()))
        for match in HTML_ANCHOR.finditer(text):
            found_links.append((match.group(1), match.group(0), match.start()))

        # Count each source occurrence once; HTML and Markdown patterns do not overlap in valid source.
        found_links.sort(key=lambda item: item[2])
        seen_positions = set()
        unique_links = []
        for link in found_links:
            if link[2] not in seen_positions:
                unique_links.append(link)
                seen_positions.add(link[2])

        if not unique_links:
            continue
        relative = path.relative_to(ROOT).as_posix()
        checked_posts += 1
        for url, attributes, _position in unique_links:
            checked_links += 1
            if not has_sponsored_attribute(attributes):
                errors.append(f"{relative}: affiliate link missing rel=\"sponsored\": {url}")

        if directory.name == "_posts" and "{% include affiliate-disclosure.html %}" not in text:
            errors.append(f"{relative}: affiliate link found but affiliate-disclosure include is missing")

for error in errors:
    print(f"ERROR: {error}")
print(f"Checked affiliate links: {checked_links} link(s) across {checked_posts} file(s), {len(errors)} error(s)")
sys.exit(1 if errors else 0)
