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
    api_key = os.environ["ANTHROPIC_API_KEY"]

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
- Be factually cautious: where you are not certain of a current price or exact app menu
  wording, say so explicitly rather than inventing specifics, since a human will fact-check
  before publishing.
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
            "max_tokens": 3500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
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

    if len(summary) > 160:
        summary = summary[:155].rsplit(" ", 1)[0].rstrip(",;:") + "…"

    header = {
        "overlay_image": hero_image["overlay_image"],
        "overlay_image_small": hero_image["overlay_image_small"],
        "teaser": hero_image["teaser"],
        "og_image": hero_image["og_image"],
    }
    if hero_image.get("caption"):
        header["caption"] = hero_image["caption"]

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

    body = convert_affiliate_links(body, load_products())

    with open(filepath, "w") as f:
        f.write(front_matter + body + showcase_block + related_block)

    save_queue(queue)

    print(f"Draft written to {filepath}")
    set_output("post_path", filepath)
    set_output("post_title", title.replace("\n", " "))
    set_output("publish_by", str(topic.get("publish_by", "")))

    # --- Social content generation ---
    # Runs after the post is written. Failure here is non-fatal: the post PR
    # still opens, just without social drafts in the body.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from generate_social import generate_post_social, write_multiline_output

        video_angle = topic.get("video_angle") if topic.get("video") else None
        pillar = topic.get("pillar", "")
        # whatsapp: false suppresses WhatsApp copy for minor/niche posts
        want_whatsapp = topic.get("whatsapp", True)
        # Live address, from permalink /:categories/:title/ in _config.yml
        # (Jekyll lowercases the category; the slug comes from the filename).
        post_url = f"https://onairireland.ie/{category_slug_name.lower()}/{slug}/"
        social = generate_post_social(
            title, category, brief, body,
            pillar=pillar,
            video_angle=video_angle,
            want_whatsapp=want_whatsapp,
            post_url=post_url,
        )

        if not want_whatsapp:
            social["whatsapp_msg"] = "No WhatsApp post for this topic (whatsapp: false in the queue)."

        gh_out = os.environ.get("GITHUB_OUTPUT")
        write_multiline_output(gh_out, "x_post", social.get("x_post", ""))
        write_multiline_output(gh_out, "whatsapp_msg", social.get("whatsapp_msg", ""))

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
            set_output("youtube_script_path", yt_path)

        # An empty box means the model's reply didn't contain that section, so
        # flag it in the PR instead of showing a blank box as if all was well.
        missing = [k for k in ("x_post", "whatsapp_msg") if not social.get(k)]
        if missing:
            print(f"Social generation incomplete: empty {', '.join(missing)}")
            set_output("has_social", "false")
        else:
            set_output("has_social", "true")
            print("Social content generated.")
    except Exception as exc:
        print(f"Social generation skipped: {exc}")
        set_output("has_social", "false")


if __name__ == "__main__":
    main()
