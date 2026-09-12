#!/usr/bin/env python3
"""
Pops the first topic off _data/topic_queue.yml, asks Claude to draft a
blog post from it, writes the draft into _posts/, and removes the topic
from the queue. Intended to run inside the GitHub Action -- never
publishes directly; the workflow opens a PR with the result so a human
reviews and merges before anything goes live.

Requires the ANTHROPIC_API_KEY secret to be set on the repo
(Settings -> Secrets and variables -> Actions).
"""
import datetime
import os
import random
import re
import sys

import requests
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(REPO_ROOT, "_data", "topic_queue.yml")
POSTS_DIR = os.path.join(REPO_ROOT, "_posts")

CATEGORY_SLUGS = {
    "Streaming Services": "streaming-services",
    "Devices": "devices",
    "Installation Guides": "installation-guides",
    "News": "news",
    "Reviews": "reviews",
    "Sports Streaming": "sports-streaming",
    "Troubleshooting": "troubleshooting",
}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_products():
    products_path = os.path.join(REPO_ROOT, "_data", "products.yml")
    with open(products_path, "r") as f:
        return yaml.safe_load(f) or []


def load_teaser_images():
    teasers_path = os.path.join(REPO_ROOT, "_data", "teaser_images.yml")
    with open(teasers_path, "r") as f:
        return yaml.safe_load(f) or {}


def pick_product_image(category: str) -> str:
    """Return the image path of a random image matching this category --
    pulled from both product photos AND the broader teaser_images.yml pool,
    so auto-drafted posts get real visual variety instead of repeating the
    same 1-2 product photos every time. Falls back to the placeholder if
    nothing matches yet."""
    products = load_products()
    pool = [p.get("image") for p in products if p.get("category") == category and p.get("image")]

    teasers = load_teaser_images()
    pool += teasers.get(category, [])

    if pool:
        return random.choice(pool)
    return "/assets/images/social-default.svg"


def load_queue():
    if not os.path.exists(QUEUE_PATH):
        print("topic_queue.yml is missing -- creating a fresh empty one.")
        save_queue([])
        return []
    with open(QUEUE_PATH, "r") as f:
        return yaml.safe_load(f) or []


def save_queue(queue):
    header = (
        "# Queue of topics for the daily auto-post GitHub Action.\n"
        "# The workflow pops the FIRST item each run, generates a draft post from it,\n"
        "# opens a PR, and removes it from this list once the PR is created.\n"
        "#\n"
        "# category must be one of: Streaming Services | Devices | Installation Guides |\n"
        "# News | Reviews | Sports Streaming | Troubleshooting\n"
        "# (add a new category name here anytime -- Jekyll auto-generates its listing page,\n"
        "# no other file needs to change. Just keep spelling consistent across posts.)\n"
        "# Add new topics to the bottom of this list whenever you like.\n\n"
    )
    with open(QUEUE_PATH, "w") as f:
        f.write(header)
        yaml.safe_dump(queue, f, sort_keys=False, allow_unicode=True)


def call_claude(title: str, category: str, brief: str) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]

    matching_products = [p for p in load_products() if p.get("category") == category]
    product_links_text = ""
    if matching_products:
        lines = [f"- [{p['name']}]({p['affiliate_link']})" for p in matching_products]
        product_links_text = (
            "\nRelevant product links you may naturally reference inline in the article "
            "(not just at the end) -- weave 1-2 of these into the body as normal markdown "
            "links where they fit naturally, using descriptive text, not a dumped list:\n"
            + "\n".join(lines) + "\n"
        )

    prompt = f"""Write a Jekyll blog post in Markdown for an Irish blog about LEGAL
streaming services and devices. Never mention, link to, or describe
unauthorized/unlicensed IPTV or streaming resale services.

Title: {title}
Category: {category}
Brief: {brief}
{product_links_text}
Requirements:
- Start directly with the article body in Markdown (no front matter, no title heading repeated).
- Use ## and ### headings, short paragraphs.
- Do NOT include a "Related" or "See also" section, and do not invent links to other posts
  or pages -- a real "Related" link gets appended automatically after your content.
- Include a one-sentence meta-description-style summary as the very first line, prefixed
  with "SUMMARY:", then a blank line, then the article.
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
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    if not resp.ok:
        print(f"Anthropic API error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []))


def parse_faqs(text: str):
    """Split FAQS: block out of the raw response and parse Q:/A: pairs.
    Returns (body_without_faqs, list_of_(question, answer)_tuples)."""
    if "FAQS:" not in text:
        return text, []
    body, _, faq_block = text.partition("FAQS:")
    pairs = re.findall(r"Q:\s*(.+?)\s*\nA:\s*(.+?)(?=\n\s*Q:|\Z)", faq_block.strip(), re.DOTALL)
    cleaned = [(q.strip(), a.strip()) for q, a in pairs if q.strip() and a.strip()]
    return body.strip(), cleaned


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

Topics should be genuinely useful to an Irish streaming audience -- specific
services (RTE Player, Virgin Media, Sky, NOW, Netflix, Disney+, GAA+, TG4),
specific devices (Fire TV Stick, Apple TV, Chromecast, smart TVs), or practical
troubleshooting/buying-guide angles.
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
            "max_tokens": 1500,
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
    for t, c, b in blocks:
        t, c, b = t.strip(), c.strip(), b.strip()
        if c not in CATEGORY_SLUGS:
            continue
        if t and b:
            topics.append({"title": t, "category": c, "brief": b})
    return topics


def main():
    queue = load_queue()
    if not queue:
        print("Topic queue is empty -- auto-generating a fresh batch of topics...")
        queue = generate_new_topics()
        if not queue:
            print("Could not generate new topics this run -- nothing to do.")
            sys.exit(0)
        save_queue(queue)
        print(f"Added {len(queue)} new topics to the queue.")

    topic = queue.pop(0)
    title = topic["title"]
    category = topic["category"]
    brief = topic.get("brief", "")

    raw = call_claude(title, category, brief)

    summary = ""
    body = raw
    if raw.startswith("SUMMARY:"):
        first_line, _, rest = raw.partition("\n")
        summary = first_line.replace("SUMMARY:", "").strip()
        body = rest.strip()

    body, faqs = parse_faqs(body)

    today = datetime.date.today().isoformat()
    slug = slugify(title)
    filename = f"{today}-{slug}.md"
    filepath = os.path.join(POSTS_DIR, filename)

    category_slug_name = category.replace(" ", "-")
    hero_image = pick_product_image(category)

    # Escape double quotes so AI-generated text can never break the YAML
    # front matter's quoted strings (this caused real build failures before).
    safe_title = title.replace('"', "'")
    safe_summary = summary.replace('"', "'")

    faqs_yaml = ""
    if faqs:
        faqs_yaml = "faqs:\n"
        for q, a in faqs:
            safe_q = q.replace('"', "'")
            safe_a = a.replace('"', "'")
            faqs_yaml += f'  - question: "{safe_q}"\n    answer: "{safe_a}"\n'

    front_matter = f"""---
title: "{safe_title}"
excerpt: "{safe_summary}"
description: "{safe_summary}"
categories:
  - {category_slug_name}
tags:
  - {CATEGORY_SLUGS.get(category, slugify(category))}
header:
  overlay_image: {hero_image}
  teaser: {hero_image}
seo:
  type: Article
toc: true
draft_generated: true
affiliate_links: true
{faqs_yaml}---

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
    )

    with open(filepath, "w") as f:
        f.write(front_matter + body + showcase_block + related_block)

    save_queue(queue)

    print(f"Draft written to {filepath}")
    print(f"::set-output name=post_path::{filepath}")
    print(f"::set-output name=post_title::{title}")


if __name__ == "__main__":
    main()
