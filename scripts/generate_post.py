#!/usr/bin/env python3
"""
Pops the first topic off _data/topic_queue.yml, asks Claude to draft a
blog post from it, writes the draft into _posts/, and removes the topic
from the queue. Intended to run inside the GitHub Action -- never
publishes directly; the workflow opens a PR with the result so a human
reviews and merges before anything goes live.

Requires the ANTHROPIC_API_KEY secret to be set on the repo, and
PEXELS_API_KEY so the post can get a photo from the approved shortlist
(_data/photo_shortlist.yml), self-hosted and credited. Without the key, or when
no approved photo fits, the post gets a unique brand card instead (see
scripts/image_system.py and scripts/card_kit/README.md).
"""
import datetime
import os
import re
import sys
import unicodedata

import requests
import yaml

import image_system  # scripts/image_system.py: approved photos first, brand card as fallback
import site_facts  # scripts/site_facts.py: checked facts and prices for the prompt

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(REPO_ROOT, "_data", "topic_queue.yml")
POSTS_DIR = os.path.join(REPO_ROOT, "_posts")
PRODUCTS_PATH = os.path.join(REPO_ROOT, "_data", "products.yml")

CATEGORY_SLUGS = {
    "Streaming Services": "streaming-services",
    "Devices": "devices",
    "Installation Guides": "installation-guides",
    "News": "news",
    "Reviews": "reviews",
    "Sports Streaming": "sports-streaming",
    "Troubleshooting": "troubleshooting",
    "Watch Guides": "watch-guides",
}

def load_products():
    """Load the product catalog from _data/products.yml as a list of dicts."""
    if not os.path.isfile(PRODUCTS_PATH):
        return []
    with open(PRODUCTS_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data or []


# Markdown links to Amazon, with or without a {: ...} attribute list after them.
_AMAZON_MD_LINK = re.compile(
    r"\[([^\]\n]+)\]\((https?://(?:amzn\.to|link\.amazon|(?:www\.)?amazon\.[a-z.]+)[^\s)]*)\)(?:\{:[^}]*\})?"
)


def convert_affiliate_links(markdown: str, products) -> str:
    """Turn every Amazon link the AI wrote into the product-link include, which
    reads the address from _data/products.yml and adds rel="sponsored". Links to
    products not in the catalogue are unlinked (text kept), so drafts always
    pass scripts/check_affiliate_links.py."""
    link_to_id = {}
    for p in products:
        if p.get("affiliate_link") and p.get("id"):
            link_to_id.setdefault(p["affiliate_link"], p["id"])

    def replace(match):
        text, url = match.group(1), match.group(2)
        product_id = link_to_id.get(url)
        if not product_id:
            return text
        safe_text = text.replace('"', "'")
        return '{% include product-link.html id="' + product_id + '" text="' + safe_text + '" %}'

    return _AMAZON_MD_LINK.sub(replace, markdown)


def is_price_news(category: str, title: str) -> bool:
    """Same rule as scripts/check_price_news_links.py."""
    return category == "News" and re.search(r"\b(?:price|prices|pricing)\b", title, re.I) is not None


def slugify(text: str) -> str:
    """Turn a post title into a URL-safe filename slug."""
    # Transliterate accents (RTÉ -> rte), keep "+" meaningful (Disney+ ->
    # disney-plus) and drop apostrophes (What's -> whats) before slugging.
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("+", " plus").replace("'", "").replace("\u2019", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_queue():
    if not os.path.exists(QUEUE_PATH):
        print("topic_queue.yml is missing -- creating a fresh empty one.")
        save_queue([])
        return []
    with open(QUEUE_PATH, "r") as f:
        return yaml.safe_load(f) or []


DEFAULT_QUEUE_HEADER = (
    "# Queue of topics for the daily auto-post GitHub Action.\n"
    "# The workflow pops the FIRST item each run, generates a draft post from it,\n"
    "# opens a PR, and removes it from this list once the PR is created.\n"
    "#\n"
    "# category must be one of: Streaming Services | Devices | Installation Guides |\n"
    "# News | Reviews | Sports Streaming | Troubleshooting | Watch Guides\n"
    "# Add new topics to the bottom of this list whenever you like.\n"
)


def existing_queue_header() -> str:
    """The comment block at the top of topic_queue.yml (field notes etc.),
    up to the first section divider or entry, so a rewrite keeps it."""
    if not os.path.exists(QUEUE_PATH):
        return DEFAULT_QUEUE_HEADER
    header = []
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("- ") or line.startswith("# ---"):
                break
            header.append(line)
    text = "".join(header).rstrip() + "\n"
    return text if text.strip() else DEFAULT_QUEUE_HEADER


def save_queue(queue):
    header = existing_queue_header()
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        yaml.safe_dump(queue, f, sort_keys=False, allow_unicode=True, width=1000)


def parse_faqs(text: str):
    """Split FAQS: block out of the raw response and parse Q:/A: pairs.
    Returns (body_without_faqs, list_of_(question, answer)_tuples)."""
    if "FAQS:" not in text:
        return text, []
    body, _, faq_block = text.partition("FAQS:")
    pairs = re.findall(r"Q:\s*(.+?)\s*\nA:\s*(.+?)(?=\n\s*Q:|\Z)", faq_block.strip(), re.DOTALL)
    cleaned = [(q.strip(), a.strip()) for q, a in pairs if q.strip() and a.strip()]
    return body.strip(), cleaned


def call_claude(title: str, category: str, brief: str):
    """Returns raw article text (with SUMMARY:/IMAGE_QUERY:/FAQS: markers
    still embedded -- main() splits those out)."""

    # Products list the post types they suit in show_on (see _data/products.yml).
    matching_products = [p for p in load_products() if category in (p.get("show_on") or [])]
    product_links_text = ""
    if matching_products:
        lines = [f"- [{p['name']}]({p['affiliate_link']})" for p in matching_products]
        product_links_text = (
            "\nRelevant product links you may naturally reference inline in the article "
            "(not just at the end) -- if (and only if) any are directly relevant, "
            "weave at most 1-2 into the body as normal markdown links using descriptive text:\n"
            + "\n".join(lines) + "\n"
        )

    watch_guide_instructions = ""
    if category == "Watch Guides":
        watch_guide_instructions = """
This is a "Watch Guide" post about a specific TV show or movie. Special rules:
- Only name a specific streaming service as carrying this title if you are
  genuinely confident that's accurate for Ireland. If you are not certain,
  say plainly that availability should be confirmed on the service's own
  site/app, rather than guessing or inventing a platform.
- Include a short section on which devices/apps to watch on (weaving in 1-2
  device product links from the list above where natural), since that's
  useful regardless of which service carries the title.
"""

    scene_list = image_system.scene_list_for_prompt()
    category_scenes = ", ".join(image_system.CATEGORY_SCENES.get(category.replace(" ", "-"), [])) or "none"

    # The writer has no web access, and its memory of Irish rights and prices is
    # out of date or mixed up with the UK's (PR #118 said Premier Sports doesn't
    # show the Premier League). So it gets the facts and prices the site has
    # checked, and may only state those. A broken facts file raises here: no
    # draft is better than one written from memory.
    facts_text = site_facts.facts_for_prompt()
    prices_text = site_facts.prices_for_prompt()

    prompt = f"""Write a Jekyll blog post in Markdown for an Irish blog about LEGAL
streaming services and devices. Never mention, link to, or describe
unauthorized/unlicensed IPTV or streaming resale services.

NEVER recommend, mention, or imply using a VPN, proxy, or any geo-unblocking
method to access content -- this applies to every post, not just ones about
a specific show. If a topic naturally involves a "content not available in
your country" type error, only explain LEGITIMATE causes and fixes (account
region settings, correct app store/region, network configuration, contacting
the service's own support) -- never suggest bypassing geo-restrictions.

NEVER claim first-hand testing, hands-on use, time spent with a product,
or personal experience (no "we tested", "over a fortnight", "in our
experience"). Write as a researched guide, not a review diary.

Recommend whatever genuinely suits the reader, even when no product link is
available for it. Only link products that are directly relevant to this
post's topic -- it is fine to include no product links at all.

FACTS WE HAVE CHECKED for Ireland (they override anything you remember):

{facts_text}

PRICES WE HAVE CHECKED, in euro, from each provider's own Irish page:
{prices_text}

Rules for facts and prices:
- When you say which service, channel or broadcaster shows a competition, or what
  a membership, package or app includes, use ONLY the checked facts above.
- If the post needs a fact that isn't above, don't rely on memory: say plainly
  that readers should check with the provider, and name the provider.
- Never say a service does NOT show or include something unless the checked
  facts say so.
- Only give a price that is in the checked prices above, and say prices can change.
- Use only the facts that matter for this post's topic.

Title: {title}
Category: {category}
Brief: {brief}
{product_links_text}{watch_guide_instructions}
Requirements:
- Start directly with the article body in Markdown (no front matter, no title heading repeated).
- Use ## and ### headings, short paragraphs.
- Do NOT include a "Related" or "See also" section, and do not invent links to other posts
  or pages -- a real "Related" link gets appended automatically after your content.
- Include a one-sentence meta-description-style summary (max 155 characters) as the very
  first line, prefixed with "SUMMARY:", then a blank line, then the article.
- Open the article with a one or two sentence direct answer to the title's question.
- Immediately after the SUMMARY line (still before the blank line and article), add a
  second line prefixed "IMAGE_SCENE:" followed by exactly one of these scene names (or
  "none"), choosing the plain real-world photo that would best suit THIS post:
{scene_list}
  Pick from the scenes that fit the post's category: {category_scenes}.
  Most posts fit one of them; use "none" only if none of those would look right.
- After the article body, add a line that says exactly "FAQS:" on its own, then exactly
  4 question-and-answer pairs, each formatted as:
  Q: question text
  A: answer text
  with nothing else on those lines, and nothing after the last answer.
- 500-800 words for the article body (not counting the FAQ section).
- Be factually cautious: where you are not certain of an exact detail (a date, app menu
  wording, a device feature), say so explicitly rather than inventing specifics. Every draft
  gets an automatic fact check against the facts above and the providers' own pages.
"""
    return ask_writer(prompt)


def ask_writer(prompt: str, max_tokens: int = 3500) -> str:
    """One call to the writer model (no tools, no web access)."""
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-5",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=180,
    )
    if not resp.ok:
        print(f"Anthropic API error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    raw = "".join(block.get("text", "") for block in data.get("content", []))

    if not raw.strip():
        print("Anthropic response had no usable text content. Full response was:")
        print(data)

    return raw


# The writer can't look anything up, so a topic outside the checked facts gets
# written from memory (PR #123 explained RTÉ Player error codes no RTÉ page
# lists). The claims list catches those; this sends them back to the writer
# once, before the PR opens, so they're removed or turned into "check with the
# provider" instead of waiting for someone to spot them in review.
REVISE_PROMPT = """You wrote the draft below for On Air Ireland (onairireland.ie), an
independent Irish site about LEGAL streaming. An automatic fact check, using our
checked facts and the providers' own pages, flagged the claims listed under
FLAGGED CLAIMS. Revise the draft so that none of them stays as it is:

- ❌ wrong: correct it only if the note gives the right fact AND that fact is in
  our checked facts or prices below. Otherwise remove the claim.
- ⚠️ unconfirmed: remove it, or replace it with a plain line telling readers to
  check with the provider (name the provider). Never swap in a different
  specific detail (a number, code, date, price, menu name or quote) instead.
- Claims flagged in the X, WhatsApp or video drafts came from the article, so
  make sure the article doesn't state them either.
- If a heading, list or FAQ answer only existed for a removed claim, rewrite it
  or drop it, but keep exactly 4 FAQ pairs.
- Change nothing else: keep the structure, wording, links and product links.
- The usual rules still apply: licensed services only; never mention VPNs,
  proxies or unofficial IPTV; no first-hand testing claims; prices only from
  our checked prices.

Reply in exactly this shape, with nothing before or after it:
SUMMARY: the one-sentence summary (max 155 characters), corrected if needed

the article body in Markdown

FAQS:
Q: question
A: answer

OUR CHECKED FACTS:
<<FACTS>>

OUR CHECKED PRICES (euro):
<<PRICES>>

Title: <<TITLE>>

FLAGGED CLAIMS:
<<FLAGGED>>

=== DRAFT ===
SUMMARY: <<SUMMARY>>

<<BODY>>

FAQS:
<<FAQS>>
"""


def revise_draft(title: str, summary: str, body: str, faqs: list, flagged: list):
    """Send the flagged claims back to the writer once. Returns the new
    (summary, body, faqs), or raises ValueError if the reply isn't usable."""
    where = {"article": "article", "faq": "FAQ", "x": "X post",
             "whatsapp": "WhatsApp", "video": "video script"}
    flagged_text = "\n".join(
        f"- {'❌ wrong' if c['status'] == 'wrong' else '⚠️ unconfirmed'} "
        f"({where.get(c['where'], 'article')}): {c['claim']}"
        + (f" -- note: {c['note']}" if c.get("note") else "")
        for c in flagged)
    parts = {
        "<<FACTS>>": site_facts.facts_for_prompt(),
        "<<PRICES>>": site_facts.prices_for_prompt(),
        "<<TITLE>>": title,
        "<<FLAGGED>>": flagged_text,
        "<<SUMMARY>>": summary,
        "<<BODY>>": body.strip(),
        "<<FAQS>>": "\n".join(f"Q: {q}\nA: {a}" for q, a in faqs) or "(none)",
    }
    prompt = REVISE_PROMPT
    for key, value in parts.items():
        prompt = prompt.replace(key, value)

    raw = ask_writer(prompt, max_tokens=4000).strip()
    new_summary = summary
    if raw.startswith("SUMMARY:"):
        first_line, _, raw = raw.partition("\n")
        new_summary = first_line.replace("SUMMARY:", "").strip() or summary
        raw = raw.strip()
    new_body, new_faqs = parse_faqs(raw)
    # A reply that lost most of the article or its FAQ is worse than the
    # original with its flags, so keep the original.
    if len(new_faqs) < 3:
        raise ValueError(f"the revised draft has {len(new_faqs)} FAQ pairs")
    if len(new_body) < 0.5 * len(body):
        raise ValueError("the revised draft lost more than half the article")
    return new_summary, new_body, new_faqs


def prioritise_queue(queue: list) -> list:
    """Float entries with publish_by within the next 14 days to the top,
    sorted earliest-deadline first. Evergreen entries keep their original order."""
    today = datetime.date.today()
    cutoff = today + datetime.timedelta(days=14)
    urgent, normal = [], []
    for entry in queue:
        pb = entry.get("publish_by")
        if pb:
            try:
                d = datetime.date.fromisoformat(str(pb))
                if d <= cutoff:
                    urgent.append((d, entry))
                    continue
            except ValueError:
                pass
        normal.append(entry)
    urgent.sort(key=lambda x: x[0])
    return [e for _, e in urgent] + normal


def existing_post_titles():
    """Read titles from existing post files so we can ask Claude to avoid
    repeating topics that already exist."""
    titles = []
    if os.path.isdir(POSTS_DIR):
        for fname in os.listdir(POSTS_DIR):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(POSTS_DIR, fname)
            with open(path, "r") as f:
                content = f.read()
            m = re.search(r'^title:\s*"(.+?)"', content, re.MULTILINE)
            if m:
                titles.append(m.group(1))
    return titles


def generate_new_topics(count: int = 8):
    """Ask Claude to brainstorm a fresh batch of topics when the queue runs
    dry, so the daily workflow never just goes idle. Returns a list of
    {title, category, brief} dicts, or an empty list if generation fails."""
    api_key = os.environ["ANTHROPIC_API_KEY"]
    existing = existing_post_titles()
    existing_text = "\n".join(f"- {t}" for t in existing) if existing else "(none yet)"
    categories = " | ".join(CATEGORY_SLUGS.keys())

    prompt = f"""You are planning new blog post topics for an Irish blog about LEGAL
streaming services and devices. Never suggest anything about unauthorized
IPTV or streaming resale services.

Existing post titles already published (do NOT repeat or closely duplicate these):
{existing_text}

Generate exactly {count} new topic ideas. For each, output exactly this format,
one block per topic, with a blank line between blocks, and nothing else:

TITLE: <specific, clear title>
CATEGORY: <one of: {categories}>
BRIEF: <one sentence describing what the post should cover>

Title variety is important -- do NOT default to the same structure every
time (e.g. always "X: Y" with a colon, or always "Where to Watch X Legally
in Ireland", or always starting with "How to"). Mix it up across the batch:
some short and punchy (4-6 words), some as direct questions, some as plain
statements, some comparisons ("X vs Y"), some numbered/list-style. Vary
sentence structure and opening words so the {count} titles don't all read
like they came from the same template. Most titles should be on the
shorter side -- aim for under 8 words where the topic allows it, reserving
longer titles only for when real specificity requires it.

Topics should be genuinely useful to an Irish streaming audience -- specific
services (RTE Player, Virgin Media, Sky, NOW, Netflix, Disney+, GAA+, TG4),
specific devices (Fire TV Stick, Fire TV Cube, Roku, Chromecast, smart TVs),
practical troubleshooting/buying-guide angles, or "Watch Guide" topics about
a specific well-known TV show or movie and which LICENSED service carries
it in Ireland (e.g. "Where to Watch [Show] Legally in Ireland"). For Watch
Guide topics, only suggest titles you are reasonably confident are
currently available on a real, mainstream licensed service -- do not invent
or guess availability.

Include a mix of these high-search-intent formats where they genuinely fit:
- "Is [Service] Available in Ireland?" -- direct-answer format people
  actually type into Google (category: Streaming Services or News)
- "[Service/App] Not Working: Common Fixes" -- targets real error-message
  searches (category: Troubleshooting)

Do not suggest news topics about launches, prices or rights deals unless
they are well established -- a human will check each topic before drafting.
"""
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-5",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    if not resp.ok:
        print(f"Anthropic API error generating new topics {resp.status_code}: {resp.text}")
        return []
    resp.raise_for_status()
    data = resp.json()
    raw = "".join(block.get("text", "") for block in data.get("content", []))

    blocks = re.findall(
        r"TITLE:\s*(.+?)\s*\nCATEGORY:\s*(.+?)\s*\nBRIEF:\s*(.+?)(?=\n\s*TITLE:|\Z)",
        raw,
        re.DOTALL,
    )
    topics = []
    for ti, c, b in blocks:
        ti, c, b = ti.strip(), c.strip(), b.strip()
        if c not in CATEGORY_SLUGS:
            continue
        if ti and b:
            topics.append({"title": ti, "category": c, "brief": b})

    if not topics:
        print("Topic parsing found zero valid blocks. Raw response was:")
        print("--- START RAW RESPONSE ---")
        print(raw)
        print("--- END RAW RESPONSE ---")

    return topics


def set_output(name: str, value: str):
    """Write a step output (replaces the deprecated ::set-output command)."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def main():
    queue = load_queue()
    if not queue:
        # New AI-suggested topics go into a PR for a human to review and edit
        # BEFORE anything is drafted from them.
        print("Topic queue is empty -- generating topic ideas for review...")
        queue = generate_new_topics()
        if not queue:
            print("Could not generate new topics this run -- nothing to do.")
            sys.exit(0)
        save_queue(queue)
        print(f"Added {len(queue)} new topics to the queue for review.")
        set_output("post_title", "New topic ideas for review (edit or delete before merging)")
        set_output("fact_check", "No article in this PR, so there's no fact check.")
        return

    queue = prioritise_queue(queue)
    topic = queue.pop(0)
    title = topic["title"]
    category = topic["category"]
    brief = topic.get("brief", "")

    raw = call_claude(title, category, brief)

    summary = ""
    image_query = ""
    body = raw
    if raw.startswith("SUMMARY:"):
        first_line, _, rest = raw.partition("\n")
        summary = first_line.replace("SUMMARY:", "").strip()
        body = rest.strip()
    if body.startswith("IMAGE_QUERY:"):
        first_line, _, rest = body.partition("\n")
        image_query = first_line.replace("IMAGE_QUERY:", "").strip()
        body = rest.strip()
    image_scene = "none"
    if body.startswith("IMAGE_SCENE:"):
        first_line, _, rest = body.partition("\n")
        image_scene = first_line.replace("IMAGE_SCENE:", "").strip().lower() or "none"
        body = rest.strip()

    body, faqs = parse_faqs(body)

    today = datetime.date.today().isoformat()
    slug = slugify(title)
    filename = f"{today}-{slug}.md"
    filepath = os.path.join(POSTS_DIR, filename)

    category_slug_name = category.replace(" ", "-")
    hero_image = image_system.choose_hero(
        title, category, slug,
        scene=image_scene, image_query=image_query, post_file=filename,
    )

    seo_type = "HowTo" if category in ("Installation Guides", "Troubleshooting") else "Article"

    header = {
        "overlay_image": hero_image["overlay_image"],
        "overlay_image_small": hero_image["overlay_image_small"],
        "teaser": hero_image["teaser"],
        "og_image": hero_image["og_image"],
    }
    if hero_image.get("caption"):
        header["caption"] = hero_image["caption"]

    products = load_products()

    def write_post(summary: str, body: str, faqs: list, wrong: list = None) -> None:
        """Write the post file. Called again if the draft is revised, and with
        wrong set when ❌ claims are left after the recheck."""
        if len(summary) > 160:
            summary = summary[:155].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        fm = {
            "title": title,
            "excerpt": summary,
            "description": summary,
            "categories": [category_slug_name],
            "tags": [CATEGORY_SLUGS.get(category, slugify(category))],
            "header": header,
            "seo": {"type": seo_type},
            "toc": True,
            "draft_generated": True,
            "affiliate_links": True,
        }
        if faqs:
            fm["faqs"] = [{"question": q, "answer": a} for q, a in faqs]
        if wrong:
            # check_fact_flags.py fails the PR check while this list is here.
            fm["fact_check_wrong"] = list(wrong)

        # yaml.safe_dump quotes/escapes AI-generated text properly, so colons,
        # quotes or '#' in a title can never break the front matter again.
        front_matter = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000) + f"""---

{{% include last-updated.html %}}

{{% include affiliate-disclosure.html %}}

{{% include share-buttons.html %}}

"""

        showcase_block = f'\n\n{{% include product-showcase.html category="{category}" %}}\n'
        faq_block = "\n{% include faq-section.html %}\n" if faqs else ""
        related_block = (
            f"{faq_block}"
            "\n{% include related-posts.html %}\n"
            "\n### Related\n\n"
            "Read our [full guide to legal streaming services in Ireland]"
            "(/streaming-services/legal-streaming-services-ireland-2026/).\n"
            + (
                "\nSee every current Irish streaming price in one place on our "
                "[streaming prices tracker](/streaming-prices/), or add up your own bill "
                "with the [streaming cost calculator](/streaming-cost-calculator/).\n"
                if is_price_news(category, title) else ""
            )
            + "\n{% include whatsapp-cta.html %}\n"
        )

        with open(filepath, "w") as f:
            f.write(front_matter + convert_affiliate_links(body, products) + showcase_block + related_block)

    def read_post() -> str:
        with open(filepath, encoding="utf-8") as fh:
            return fh.read()

    write_post(summary, body, faqs)
    save_queue(queue)

    print(f"Draft written to {filepath}")
    set_output("post_path", filepath)
    set_output("post_title", title.replace("\n", " "))
    set_output("publish_by", str(topic.get("publish_by", "")))

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # Live address, from permalink /:categories/:title/ in _config.yml
    # (Jekyll lowercases the category; the slug comes from the filename).
    post_url = f"https://onairireland.ie/{category_slug_name.lower()}/{slug}/"
    social_args = dict(title=title, category=category, brief=brief, topic=topic,
                       slug=slug, today=today, filepath=filepath, post_url=post_url)
    social, social_out = build_social(body=body, **social_args)

    # --- Claims list for the PR, with one send-back pass ---
    # Checks the article, its FAQ and the social drafts against the checked
    # facts and the providers' own pages. Flagged claims go back to the writer
    # once and the draft is checked again. ❌ claims still left go into the
    # front matter, where check_fact_flags.py fails the PR check. If the fact
    # check itself fails, the PR says so and the review checks everything by hand.
    try:
        from fact_check import check_post, format_markdown, wrong_lines, write_fact_check_output

        result = check_post(read_post(), social, pr_note="")
        print(f"First pass: {result['summary']}")
        flagged = [c for c in result["claims"] if c["status"] != "ok"]
        if flagged:
            first = result["counts"]
            try:
                summary, body, faqs = revise_draft(title, summary, body, faqs, flagged)
            except Exception as exc:
                print(f"Send-back skipped: {exc}")
                reason = " ".join(str(exc).split())[:150]
                result["markdown"] = format_markdown(
                    result["claims"],
                    f"The flagged claims couldn't go back to the writer ({reason}), so this "
                    "list is the first pass and the draft is unchanged.")
            else:
                write_post(summary, body, faqs)
                print("Flagged claims sent back to the writer; draft revised.")
                # The social drafts came from the old article, so write them again.
                social, social_out = build_social(body=body, **social_args)
                result = check_post(
                    read_post(), social,
                    pr_note=(f"The first pass found {first['wrong']} wrong and "
                             f"{first['unconfirmed']} unconfirmed; those went back to the "
                             "writer once, and this list is the recheck."))
                print(f"Recheck: {result['summary']}")
        wrong = wrong_lines(result["claims"])
        if wrong:
            write_post(summary, body, faqs, wrong)
            print(f"{len(wrong)} wrong claim(s) left; listed as fact_check_wrong in the front matter.")
        write_fact_check_output(os.environ.get("GITHUB_OUTPUT"), result)
        print(result["summary"])
    except Exception as exc:
        print(f"Fact check skipped: {exc}")
        reason = " ".join(str(exc).split())[:150]
        set_output("fact_check", f"> ⚠️ **The fact check didn't run** ({reason}). "
                                 "Check every service, price, date and channel by hand.")

    # Social outputs go out once, after any rewrite, so the PR shows the final drafts.
    from generate_social import write_multiline_output
    gh_out = os.environ.get("GITHUB_OUTPUT")
    for kind, name, value in social_out:
        if kind == "multi":
            write_multiline_output(gh_out, name, value)
        else:
            set_output(name, value)


def build_social(title, category, brief, body, topic, slug, today, filepath, post_url):
    """Social drafts for the post: X, WhatsApp, and for video topics the YouTube
    script and Short spec (written as files in the PR). Failure here is
    non-fatal: the post PR still opens, just without social drafts in the body.
    Returns (social, outputs), where outputs is a list of (kind, name, value)
    step outputs for main() to write once, after any rewrite."""
    social = {}
    outputs = []
    try:
        from generate_social import generate_post_social

        video_angle = topic.get("video_angle") if topic.get("video") else None
        pillar = topic.get("pillar", "")
        # whatsapp: false suppresses WhatsApp copy for minor/niche posts
        want_whatsapp = topic.get("whatsapp", True)
        social = generate_post_social(
            title, category, brief, body,
            pillar=pillar,
            video_angle=video_angle,
            want_whatsapp=want_whatsapp,
            post_url=post_url,
        )

        if not want_whatsapp:
            social["whatsapp_msg"] = "No WhatsApp post for this topic (whatsapp: false in the queue)."

        outputs.append(("multi", "x_post", social.get("x_post", "")))
        outputs.append(("multi", "whatsapp_msg", social.get("whatsapp_msg", "")))

        # YouTube script → committed as a separate file in the same PR.
        # _video_scripts/ starts with _ so Jekyll ignores it.
        yt_script = social.get("youtube_script", "")
        if yt_script:
            scripts_dir = os.path.join(REPO_ROOT, "_video_scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            yt_path = os.path.join(scripts_dir, f"{today}-{slug}.md")
            with open(yt_path, "w", encoding="utf-8") as fh:
                fh.write(f"# YouTube Script: {title}\n\n")
                fh.write(f"_Generated {today}. Edit before recording._\n\n")
                if pillar:
                    fh.write(f"**Pillar:** {pillar}  \n")
                fh.write(f"**Angle:** {video_angle}\n\n---\n\n")
                fh.write(yt_script)
                fh.write("\n")
            print(f"YouTube script written to {yt_path}")
            # Repo-relative, so the PR body names the file in the PR
            # (not /home/runner/work/... on the Actions runner).
            outputs.append(("single", "youtube_script_path", os.path.relpath(yt_path, REPO_ROOT)))

            # The YouTube Short: scenes, voiceover and upload text, reviewed in
            # this PR. After merge, youtube-short.yml renders the MP4 from it.
            try:
                from generate_short import generate_short_spec, short_text_for_fact_check, write_spec

                spec = generate_short_spec(title, body, yt_script, post_url,
                                           os.path.relpath(filepath, REPO_ROOT))
                short_path = os.path.join(scripts_dir, f"{today}-{slug}.short.yml")
                write_spec(spec, short_path, today)
                outputs.append(("single", "short_path", os.path.relpath(short_path, REPO_ROOT)))
                # The claims list checks the Short's words too.
                social["youtube_script"] = yt_script + "\n\n" + short_text_for_fact_check(spec)
                print(f"YouTube Short spec written to {short_path}")
            except Exception as exc:
                print(f"YouTube Short spec skipped: {exc}")
                outputs.append(("single", "short_failed", " ".join(str(exc).split())[:200]))

        # An empty box means the model's reply didn't contain that section, so
        # flag it in the PR instead of showing a blank box as if all was well.
        missing = [k for k in ("x_post", "whatsapp_msg") if not social.get(k)]
        if missing:
            print(f"Social generation incomplete: empty {', '.join(missing)}")
            outputs.append(("single", "has_social", "false"))
        else:
            outputs.append(("single", "has_social", "true"))
            print("Social content generated.")
    except Exception as exc:
        print(f"Social generation skipped: {exc}")
        outputs = [("single", "has_social", "false")]
    return social, outputs


if __name__ == "__main__":
    main()
