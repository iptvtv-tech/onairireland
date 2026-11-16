#!/usr/bin/env python3
"""
Price rules shared by the checks and the draft generator.

The site's rules for prices (project instructions, Nov 2026):
  - Prices of services in the tracker come from _data/prices.yml through
    Liquid, never typed by hand. Front matter can't run Liquid, so it points to
    the tracker instead of quoting a tracked price.
  - Time-limited offers live in _data/offers.yml and are shown with
    {% include offers.html %}, so they disappear when they end.
  - Amazon (and other retailer) prices are never typed anywhere: Amazon
    Associates only allows live prices from its API (show_prices stays false).
    Posts link the product and readers check the price on the retailer's page.

Used by scripts/check_posts.py, scripts/check_prices_data.py and
scripts/generate_post.py. Not run on its own.
"""
import datetime
import os
import re

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_PATH = os.path.join(REPO_ROOT, "_data", "prices.yml")
OFFERS_PATH = os.path.join(REPO_ROOT, "_data", "offers.yml")

# Providers' own sites: the only sources allowed for prices and offers
# (used by check_price_sources.py and check_prices_data.py).
APPROVED_HOSTS = {
    "netflix.com", "disneyplus.com", "aboutamazon.eu", "amazon.ie",
    "tv.apple.com", "apple.com", "help.hbomax.com", "hbomax.com",
    "paramountplus.com", "support.paramountplus.com", "hayu.com", "support.hayu.com",
    "nowtv.com", "gaa.ie", "rte.ie", "virginmediatelevision.ie", "tg4.ie",
    "citizensinformation.ie", "tvlicence.ie", "dazn.com",
}


def is_approved(host: str) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in APPROVED_HOSTS)

# Fields of a prices.yml row that hold a euro amount.
PRICE_FIELDS = ("monthly", "yearly", "day_pass", "saver_both")

# A typed euro amount: €8.99, € 160, €27, €1,234.
EURO = re.compile(r"€\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")

# Liquid tags and output blocks are not typed text: the price inside an include
# comes from the data files.
LIQUID = re.compile(r"\{%.*?%\}|\{\{.*?\}\}", re.S)

# Some service names are also hardware names. "Apple TV 4K box" is a device
# whose price (from eir, Apple, ...) is not the Apple TV streaming price.
NOT_THE_SERVICE = {
    "Apple TV": r"Apple TV(?:\s+(?:4K|HD|box|hardware|remote|device|app)\b|\s*\(\d)",
}

# Lines that quote a past price on purpose (e.g. a news post about a rise)
# carry this marker so the typed-price check leaves them alone.
TYPED_PRICE_OK = "<!-- typed price ok -->"

# Retailer products: inline links and product cards.
PRODUCT_INCLUDE = re.compile(r"\{%-?\s*include\s+product-(?:link|showcase)\.html\b")
# Deal wording that states or implies a retailer price.
DEAL_WORDING = re.compile(
    r"\b\d{1,3}\s?%\s?off\b|\bsave\s+(?:€|up to)|\bwas\s+€|\bnow\s+(?:only\s+)?€|\bhalf[- ]price\b"
    r"|\blowest(?:[- ]ever)?\s+price\b|\bprice\s+drop\b|\bcheapest[- ]ever\b|\bdeal\s+price\b"
    r"|\breduced\s+to\b|\bdown\s+to\s+€",
    re.I,
)

PRICE_INCLUDE = re.compile(r"\{%-?\s*include\s+price\.html\s+(.*?)-?%\}", re.S)
OFFERS_INCLUDE = re.compile(r"\{%-?\s*include\s+offers\.html\s*(.*?)-?%\}", re.S)
PARAM = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

# Draft-writer price tokens: [[price:NOW|Sports]] or [[price:Disney+|Standard|yearly]].
PRICE_TOKEN = re.compile(r"\[\[price:([^|\]]+?)(?:\|([^|\]]+?))?(?:\|(monthly|yearly|day_pass|saver_both))?\]\]")


def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or default


def load_prices() -> list:
    return [r for r in _load(PRICES_PATH, []) if isinstance(r, dict)]


def load_offers() -> list:
    return [o for o in _load(OFFERS_PATH, []) if isinstance(o, dict)]


def as_date(value):
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def find_row(prices: list, service: str, plan: str = None):
    """The prices.yml row for a service and plan. Without a plan, the service's
    only row (None if it has several)."""
    rows = [r for r in prices if str(r.get("service")) == service]
    if plan:
        rows = [r for r in rows if str(r.get("plan")) == plan]
    return rows[0] if len(rows) == 1 else None


def tracked_amounts(prices: list = None, offers: list = None) -> dict:
    """{service: {amount: description}} for every tracked price and live offer."""
    prices = load_prices() if prices is None else prices
    offers = load_offers() if offers is None else offers
    out = {}
    for r in prices:
        for field in PRICE_FIELDS:
            v = r.get(field)
            if isinstance(v, (int, float)) and v > 0:
                out.setdefault(str(r["service"]), {})[round(float(v), 2)] = f"{r['service']} {r.get('plan')} ({field})"
    for o in offers:
        v = o.get("offer_monthly")
        if isinstance(v, (int, float)) and v > 0 and o.get("service"):
            out.setdefault(str(o["service"]), {})[round(float(v), 2)] = f"offer {o.get('id')}"
    return out


def _service_pattern(service: str):
    return re.compile(r"(?<![\w-])" + re.escape(service) + r"(?![\w-])", re.I)


def names_service(sentence: str, service: str) -> bool:
    """True if the sentence names the streaming service (not a device that
    shares its name, like the Apple TV 4K box)."""
    exclude = NOT_THE_SERVICE.get(service)
    if exclude:
        sentence = re.sub(exclude, " ", sentence, flags=re.I)
    return bool(_service_pattern(service).search(sentence))


def _amount(text: str) -> float:
    return round(float(text.replace(",", "")), 2)


def sentences(text: str):
    """Rough sentence split; good enough to keep a price next to its service."""
    for para in re.split(r"\n\s*\n", text):
        for line in para.split("\n"):
            for s in re.split(r"(?<=[.!?])\s+(?=[A-Z*\[(])", line):
                if s.strip():
                    yield s


def typed_tracked_prices(text: str, amounts: dict = None) -> list:
    """[(service, amount, sentence)] for typed euro amounts that equal a tracked
    price (or live offer) of a service named in the same sentence."""
    amounts = tracked_amounts() if amounts is None else amounts
    found = []
    for line in text.split("\n"):
        if TYPED_PRICE_OK in line:
            continue
        clean = LIQUID.sub(" ", line)
        for sentence in sentences(clean):
            typed = [_amount(m.group(1)) for m in EURO.finditer(sentence)]
            if not typed:
                continue
            for service, by_amount in amounts.items():
                if not names_service(sentence, service):
                    continue
                for a in typed:
                    if a in by_amount:
                        found.append((service, a, sentence.strip()))
    return found


def retailer_price_problems(body: str) -> list:
    """Paragraphs that link a retailer product AND type a price or deal wording."""
    problems = []
    for para in re.split(r"\n\s*\n", body):
        if not PRODUCT_INCLUDE.search(para):
            continue
        clean = LIQUID.sub(" ", para)
        hit = EURO.search(clean) or DEAL_WORDING.search(clean)
        if hit:
            problems.append((hit.group(0), " ".join(para.split())[:120]))
    return problems


def price_include_problems(text: str, prices: list = None, offers: list = None) -> list:
    """price.html / offers.html includes that point at data that doesn't exist."""
    prices = load_prices() if prices is None else prices
    offers = load_offers() if offers is None else offers
    problems = []
    for m in PRICE_INCLUDE.finditer(text):
        params = dict(PARAM.findall(m.group(1)))
        service, plan = params.get("service"), params.get("plan")
        field = params.get("field", "monthly")
        if not service:
            problems.append(f"{m.group(0)[:70]}: needs service=\"...\"")
            continue
        row = find_row(prices, service, plan)
        if not row:
            problems.append(f"{m.group(0)[:70]}: no single row for service {service!r} plan {plan!r} in _data/prices.yml")
        elif field not in PRICE_FIELDS:
            problems.append(f"{m.group(0)[:70]}: field must be one of {', '.join(PRICE_FIELDS)}")
        elif row.get(field) in (None, ""):
            problems.append(f"{m.group(0)[:70]}: {service} {row.get('plan')} has no {field} price")
    known = {str(r.get("service")) for r in prices} | {str(o.get("service")) for o in offers}
    for m in OFFERS_INCLUDE.finditer(text):
        service = dict(PARAM.findall(m.group(1))).get("service")
        if service and service not in known:
            problems.append(f"{m.group(0)[:70]}: no service {service!r} in prices.yml or offers.yml")
    return problems


def price_include(service: str, plan: str = None, field: str = "monthly") -> str:
    parts = [f'service="{service}"']
    if plan:
        parts.append(f'plan="{plan}"')
    if field and field != "monthly":
        parts.append(f'field="{field}"')
    return "{% include price.html " + " ".join(parts) + " %}"


def tokens_for_prompt(prices: list = None) -> str:
    """The price tokens the draft writer may use, one line per plan."""
    prices = load_prices() if prices is None else prices
    lines = []
    for r in prices:
        fields = [f for f in PRICE_FIELDS if isinstance(r.get(f), (int, float)) and r.get(f) > 0]
        if not fields:
            continue
        tokens = ", ".join(
            f"[[price:{r['service']}|{r.get('plan')}{'' if f == 'monthly' else '|' + f}]] ({f.replace('_', ' ')})"
            for f in fields)
        lines.append(f"- {r['service']} {r.get('plan')}: {tokens}")
    return "\n".join(lines)


def _format_euro(amount) -> str:
    return f"€{float(amount):,.2f}"


def render_price_includes(text: str, prices: list = None) -> str:
    """The text with price.html includes and [[price:...]] tokens replaced by the
    figures they print, for readers that can't run Liquid (the fact check, the
    social drafts)."""
    prices = load_prices() if prices is None else prices

    def from_include(m):
        params = dict(PARAM.findall(m.group(1)))
        row = find_row(prices, params.get("service", ""), params.get("plan"))
        value = row.get(params.get("field", "monthly")) if row else None
        return _format_euro(value) if isinstance(value, (int, float)) else "the current price"

    def from_token(m):
        row = find_row(prices, m.group(1).strip(), (m.group(2) or "").strip() or None)
        value = row.get(m.group(3) or "monthly") if row else None
        return _format_euro(value) if isinstance(value, (int, float)) else "the current price"

    return PRICE_TOKEN.sub(from_token, PRICE_INCLUDE.sub(from_include, text))


def replace_price_tokens(text: str, prices: list = None, in_front_matter: bool = False):
    """Turn the writer's [[price:...]] tokens into price.html includes.
    Returns (text, unknown_tokens). In front matter (FAQs) a token becomes a
    pointer to the tracker, because front matter can't run Liquid."""
    prices = load_prices() if prices is None else prices
    unknown = []

    def repl(m):
        service, plan, field = m.group(1).strip(), (m.group(2) or "").strip() or None, m.group(3) or "monthly"
        row = find_row(prices, service, plan)
        if in_front_matter:
            return "the current price (see our streaming price tracker)"
        if not row or row.get(field) in (None, ""):
            unknown.append(m.group(0))
            return "the current price (see our [streaming price tracker](/streaming-prices/))"
        return price_include(service, row.get("plan"), field)

    return PRICE_TOKEN.sub(repl, text), unknown


def replace_unambiguous_typed_prices(text: str, prices: list = None) -> str:
    """Swap a typed tracked price for its include when the sentence names the
    service and the amount belongs to exactly one of its plans/fields."""
    prices = load_prices() if prices is None else prices
    out_lines = []
    for line in text.split("\n"):
        if TYPED_PRICE_OK in line or line.lstrip().startswith(("{%", "|")):
            out_lines.append(line)
            continue
        new = line
        for sentence in sentences(LIQUID.sub(" ", line)):
            for m in EURO.finditer(sentence):
                amount = _amount(m.group(1))
                matches = []
                for r in prices:
                    if not names_service(sentence, str(r["service"])):
                        continue
                    for field in PRICE_FIELDS:
                        v = r.get(field)
                        if isinstance(v, (int, float)) and round(float(v), 2) == amount:
                            matches.append((r, field))
                if len(matches) == 1:
                    r, field = matches[0]
                    new = new.replace(m.group(0), price_include(str(r["service"]), str(r.get("plan")), field), 1)
        out_lines.append(new)
    return "\n".join(out_lines)


def offer_problems(offers: list, prices: list, today: datetime.date, approved_host) -> tuple:
    """(errors, warnings) for _data/offers.yml."""
    errors, warnings = [], []
    seen = set()
    for i, o in enumerate(offers, 1):
        oid = o.get("id") or f"entry {i}"
        where = f"offers.yml {oid}"
        for key in ("id", "service", "plan", "offer_monthly", "months", "terms", "show_until", "checked", "source", "url"):
            if o.get(key) in (None, ""):
                errors.append(f"{where}: missing {key}")
        if oid in seen:
            errors.append(f"{where}: id listed twice")
        seen.add(oid)
        row = find_row(prices, str(o.get("service")), str(o.get("plan")))
        if o.get("service") and o.get("plan") and not row:
            errors.append(f"{where}: no row for {o.get('service')} / {o.get('plan')} in _data/prices.yml")
        price = o.get("offer_monthly")
        if price is not None and (not isinstance(price, (int, float)) or price <= 0):
            errors.append(f"{where}: offer_monthly {price!r} is not a euro amount")
        elif row and isinstance(row.get("monthly"), (int, float)) and price is not None and price >= row["monthly"]:
            errors.append(f"{where}: offer_monthly {price} is not below the regular {row['monthly']}")
        months = o.get("months")
        if months is not None and (not isinstance(months, int) or not 1 <= months <= 24):
            errors.append(f"{where}: months should be a whole number from 1 to 24")
        terms = str(o.get("terms") or "")
        if re.search(r"\b(?:code|voucher|coupon)\b", terms, re.I):
            errors.append(f"{where}: terms mention a code or voucher; don't publish promo codes")
        checked, until, ends = as_date(o.get("checked")), as_date(o.get("show_until")), as_date(o.get("ends")) if o.get("ends") else None
        for key, val in (("checked", checked), ("show_until", until)):
            if o.get(key) not in (None, "") and val is None:
                errors.append(f"{where}: {key} must be a YYYY-MM-DD date")
        if checked and checked > today:
            errors.append(f"{where}: checked {checked} is in the future")
        if checked and until and (until - checked).days > 21 and not (ends and until <= ends and (ends - checked).days <= 45):
            errors.append(f"{where}: show_until {until} is more than 21 days after checked {checked}; "
                          "re-check sooner (or give the provider's own end date in ends:)")
        if ends and until and until > ends:
            errors.append(f"{where}: show_until {until} is after the provider's end date {ends}")
        if until and until < today:
            warnings.append(f"{where}: ended {until} (hidden on the site); remove it or re-check it")
        url = str(o.get("url") or "")
        if url and not url.startswith("https://"):
            errors.append(f"{where}: url should start with https://")
        elif url and not approved_host(re.sub(r"^https://([^/]+).*$", r"\1", url).lower()):
            errors.append(f"{where}: {url} is not a provider page on the primary-source allowlist")
        if "dazn." in url and o.get("checked_by") != "hand":
            errors.append(f"{where}: DAZN offers are checked by hand (its terms forbid scraping); add checked_by: hand")
        if o.get("affiliate") is not None:
            ids = {str(p.get("id")) for p in _load(os.path.join(REPO_ROOT, "_data", "products.yml"), []) if isinstance(p, dict)}
            if str(o["affiliate"]) not in ids:
                errors.append(f"{where}: affiliate {o['affiliate']!r} is not an id in _data/products.yml")
    return errors, warnings
