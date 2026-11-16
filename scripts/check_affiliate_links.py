#!/usr/bin/env python3
"""Check affiliate links in posts and pages.

Posts must link to Amazon and Awin partners (e.g. DAZN) only through the product-link include, which reads
the address from _data/products.yml and always adds rel="nofollow sponsored
noopener":

    {% include product-link.html id="fire-tv-stick-4k" text="Fire TV Stick 4K" %}

This script fails when:
  - a post contains a raw Amazon or Awin link (Markdown or HTML) instead of the include
  - a post or page links straight to an Awin partner's own site (e.g. dazn.com):
    the click carries no tracking, so it goes through the include with
    to="<that page>", which keeps our link and lands on the same page
  - an include's to="..." isn't an https page on that partner's site
  - an include uses an id that is not in _data/products.yml
  - a page has a raw Amazon or Awin link without rel="sponsored"
  - a post with affiliate links is missing the affiliate disclosure include
"""
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
PAGES = ROOT / "_pages"
PRODUCTS = ROOT / "_data" / "products.yml"

MARKDOWN_LINK = re.compile(
    r"\[[^\]\n]+\]\((https?://(?:amzn\.to|link\.amazon|(?:www\.)?amazon\.[a-z.]+|(?:www\.)?awin1\.com)[^\s)]*)\)(\s*\{:[^}]*\})?",
    re.I,
)
HTML_ANCHOR = re.compile(
    r"<a\b[^>]*href=[\"'](https?://(?:amzn\.to|link\.amazon|(?:www\.)?amazon\.[a-z.]+|(?:www\.)?awin1\.com)[^\"']*)[\"'][^>]*>",
    re.I | re.S,
)
PRODUCT_LINK = re.compile(r"\{%-?\s*include\s+product-link\.html\s+(.*?)-?%\}", re.S)
TO_PARAM = re.compile(r'\bto\s*=\s*"([^"]+)"')
# A plain link (Markdown or HTML) and the host it points at.
PLAIN_LINK = re.compile(r"""(?:\]\(|href=["'])(https?://([^/\s)"'?#]+)[^\s)"']*)""", re.I)
ID_PARAM = re.compile(r'\bid\s*=\s*"([^"]+)"')
VAR_ID_PARAM = re.compile(r"\bid\s*=\s*[A-Za-z_][\w.]*")
SPONSORED_REL = re.compile(r"\brel\s*=\s*([\"'])([^\"']*)\1", re.I)
DISCLOSURE = "{% include affiliate-disclosure.html %}"

products = yaml.safe_load(PRODUCTS.read_text(encoding="utf-8")) or []
product_ids = {str(p.get("id")) for p in products if isinstance(p, dict)}
products_by_id = {str(p.get("id")): p for p in products if isinstance(p, dict)}


def site_of(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def landing_site(link: str) -> str:
    """The partner site an Awin link lands on (its ued= address), or ''."""
    ued = (parse_qs(urlparse(link).query).get("ued") or [""])[0]
    return site_of(urlparse(ued).hostname or "")


# Partner sites we have an Awin link for (dazn.com -> "dazn"): a plain link to
# them would send readers there without our tracking.
partner_sites = {}
for p in products:
    if isinstance(p, dict) and "awin1.com" in str(p.get("affiliate_link", "")):
        site = landing_site(str(p["affiliate_link"]))
        if site:
            partner_sites.setdefault(site, str(p.get("id")))

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
                # A template may pass the id from data, e.g. id=p.affiliate on the
                # price tracker; check_prices_data.py validates those ids.
                if not VAR_ID_PARAM.search(match.group(1)):
                    errors.append(f"{relative}: product-link include without id=\"...\"")
            elif id_match.group(1) not in product_ids:
                errors.append(f"{relative}: product-link id {id_match.group(1)!r} is not in _data/products.yml")
            to = TO_PARAM.search(match.group(1))
            if to and id_match and id_match.group(1) in product_ids:
                link = str(products_by_id[id_match.group(1)].get("affiliate_link", ""))
                want = landing_site(link)
                got = site_of(urlparse(to.group(1)).hostname or "")
                if not want:
                    errors.append(f"{relative}: to=\"...\" only works for Awin partners, not {id_match.group(1)!r}")
                elif not to.group(1).startswith("https://") or got != want:
                    errors.append(f"{relative}: to={to.group(1)!r} must be an https page on {want}")

        for m in PLAIN_LINK.finditer(text):
            pid = partner_sites.get(site_of(m.group(2)))
            if pid:
                found = True
                errors.append(
                    f"{relative}: plain link to {m.group(1)} carries no tracking; use "
                    f"{{% include product-link.html id=\"{pid}\" text=\"...\" to=\"{m.group(1)}\" %}}"
                )

        raw = [(m.group(1), m.group(2) or "") for m in MARKDOWN_LINK.finditer(text)]
        raw += [(m.group(1), m.group(0)) for m in HTML_ANCHOR.finditer(text)]
        for url, attributes in raw:
            found = True
            raw_links += 1
            if is_post:
                errors.append(
                    f"{relative}: raw affiliate link {url}; add the product to _data/products.yml "
                    f"and use {{% include product-link.html id=\"...\" text=\"...\" %}}"
                )
            elif not has_sponsored(attributes):
                errors.append(f"{relative}: affiliate link missing rel=\"sponsored\": {url}")

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
