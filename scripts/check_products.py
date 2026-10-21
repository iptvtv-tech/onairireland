#!/usr/bin/env python3
"""Validate the affiliate product catalogue and its approved categories."""
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "_data" / "products.yml"
CONFIG = ROOT / "_config.yml"
APPROVED_CATEGORIES = {"Streaming Services", "Devices", "Installation Guides"}
# Post types a showcase can ask for: {% include product-showcase.html category="..." %}
SHOWCASE_CONTEXTS = {
    "Devices", "Installation Guides", "News", "Reviews", "Sports Streaming",
    "Streaming Services", "Troubleshooting", "Watch Guides",
}
REQUIRED_FIELDS = ("id", "name", "category", "image", "affiliate_link")
errors = []
products_per_context = {context: 0 for context in SHOWCASE_CONTEXTS}

try:
    products = yaml.safe_load(PRODUCTS.read_text(encoding="utf-8")) or []
except yaml.YAMLError as exc:
    print(f"ERROR: _data/products.yml is not valid YAML: {exc}")
    sys.exit(1)

if not isinstance(products, list):
    print("ERROR: _data/products.yml must contain a list of products")
    sys.exit(1)

seen_ids = set()
for row in products:
    if not isinstance(row, dict):
        errors.append("catalogue entry is not a mapping")
        continue
    product_id = str(row.get("id", "?")).strip()
    for field in REQUIRED_FIELDS:
        if not str(row.get(field, "")).strip():
            errors.append(f"{product_id}: missing required field {field}")
    if product_id in seen_ids:
        errors.append(f"{product_id}: duplicate product id")
    seen_ids.add(product_id)

    category = row.get("category")
    if category not in APPROVED_CATEGORIES:
        errors.append(
            f"{product_id}: category {category!r} is not approved; "
            f"use one of {', '.join(sorted(APPROVED_CATEGORIES))}"
        )

    show_on = row.get("show_on")
    # An empty list is allowed: the product is only linked inline in posts
    # (product-link include) and on Best Prices, not in the rotating cards.
    if not isinstance(show_on, list):
        errors.append(f"{product_id}: show_on must be a list of post types ([] for inline-only products)")
    else:
        for context in show_on:
            if context not in SHOWCASE_CONTEXTS:
                errors.append(
                    f"{product_id}: show_on value {context!r} is not a post type; "
                    f"use one of {', '.join(sorted(SHOWCASE_CONTEXTS))}"
                )
            else:
                products_per_context[context] += 1

    image = str(row.get("image", ""))
    if image and not image.startswith("/assets/images/products/"):
        errors.append(f"{product_id}: product image must be a local /assets/images/products/ path")
    elif image and not (ROOT / image.lstrip("/")).is_file():
        errors.append(f"{product_id}: product image does not exist: {image}")

    affiliate_link = str(row.get("affiliate_link", ""))
    if affiliate_link and not affiliate_link.startswith("https://"):
        errors.append(f"{product_id}: affiliate_link must use HTTPS")
    if "AFFILIATE_LINK_" in affiliate_link or "TODO" in affiliate_link.upper():
        errors.append(f"{product_id}: affiliate link contains a placeholder")

config_text = CONFIG.read_text(encoding="utf-8") if CONFIG.is_file() else ""
if not __import__("re").search(r"(?m)^show_prices:\s*false\s*(?:#.*)?$", config_text):
    errors.append("_config.yml must keep show_prices: false")

# Every post type that posts ask for must have at least one product, or its
# showcase silently disappears.
import re as _re
requested = set()
for folder in (ROOT / "_posts", ROOT / "_pages"):
    for path in folder.glob("*.md") if folder.is_dir() else []:
        requested.update(_re.findall(r'include product-showcase\.html[^%]*?category="([^"]+)"', path.read_text(encoding="utf-8")))
for context in sorted(requested):
    if context not in SHOWCASE_CONTEXTS:
        errors.append(f"a post asks for showcase category {context!r}, which is not a known post type")
    elif products_per_context[context] == 0:
        errors.append(f"no product has {context!r} in show_on, so those posts show no product cards")

for error in errors:
    print(f"ERROR: {error}")
print(f"Checked products: {len(products)} entries, {len(errors)} error(s)")
sys.exit(1 if errors else 0)
