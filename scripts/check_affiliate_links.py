#!/usr/bin/env python3
"""Check affiliate links in posts and pages.

Posts must link to Amazon only through the product-link include, which reads
the address from _data/products.yml and always adds rel="nofollow sponsored
noopener":

    {% include product-link.html id="fire-tv-stick-4k" text="Fire TV Stick 4K" %}

This script fails when:
  - a post contains a raw Amazon link (Markdown or HTML) instead of the include
  - an include uses an id that is not in _data/products.yml
  - a page has a raw Amazon link without rel="sponsored"
  - a post with affiliate links is missing the affiliate disclosure include
"""
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
PAGES = ROOT / "_pages"
PRODUCTS = ROOT / "_data" / "products.yml"

MARKDOWN_LINK = re.compile(
    r"\[[^\]\n]+\]\((https?://(?:amzn\.to|link\.amazon|(?:www\.)?amazon\.[a-z.]+)[^\s)]*)\)(\s*\{:[^}]*\})?",
    re.I,
)
HTML_ANCHOR = re.compile(
    r"<a\b[^>]*href=[\"'](https?://(?:amzn\.to|link\.amazon|(?:www\.)?amazon\.[a-z.]+)[^\"']*)[\"'][^>]*>",
    re.I | re.S,
)
PRODUCT_LINK = re.compile(r"\{%-?\s*include\s+product-link\.html\s+([^%]*?)-?%\}")
ID_PARAM = re.compile(r'\bid\s*=\s*"([^"]+)"')
SPONSORED_REL = re.compile(r"\brel\s*=\s*([\"'])([^\"']*)\1", re.I)
DISCLOSURE = "{% include affiliate-disclosure.html %}"

products = yaml.safe_load(PRODUCTS.read_text(encoding="utf-8")) or []
product_ids = {str(p.get("id")) for p in products if isinstance(p, dict)}

errors = []
include_links = raw_links = files_with_links = 0


def has_sponsored(attributes: str) -> bool:
    return any("sponsored" in m.group(2).lower().split() for m in SPONSORED_REL.finditer(attributes))


for directory in (POSTS, PAGES):
    if not directory.is_dir():
        continue
    for path in sorted(directory.rglob("*")):
        if path.suffix.lower() not in {".md", ".markdown", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        is_post = directory == POSTS
        found = False

        for match in PRODUCT_LINK.finditer(text):
            found = True
            include_links += 1
            id_match = ID_PARAM.search(match.group(1))
            if not id_match:
                errors.append(f"{relative}: product-link include without id=\"...\"")
            elif id_match.group(1) not in product_ids:
                errors.append(f"{relative}: product-link id {id_match.group(1)!r} is not in _data/products.yml")

        raw = [(m.group(1), m.group(2) or "") for m in MARKDOWN_LINK.finditer(text)]
        raw += [(m.group(1), m.group(0)) for m in HTML_ANCHOR.finditer(text)]
        for url, attributes in raw:
            found = True
            raw_links += 1
            if is_post:
                errors.append(
                    f"{relative}: raw Amazon link {url}; add the product to _data/products.yml "
                    f"and use {{% include product-link.html id=\"...\" text=\"...\" %}}"
                )
            elif not has_sponsored(attributes):
                errors.append(f"{relative}: Amazon link missing rel=\"sponsored\": {url}")

        if found:
            files_with_links += 1
            if is_post and DISCLOSURE not in text:
                errors.append(f"{relative}: affiliate links found but {DISCLOSURE} is missing")

for error in errors:
    print(f"ERROR: {error}")
print(
    f"Checked affiliate links: {include_links} product-link include(s) and {raw_links} raw link(s) "
    f"across {files_with_links} file(s), {len(errors)} error(s)"
)
sys.exit(1 if errors else 0)
