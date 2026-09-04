#!/usr/bin/env python3
"""
Pops the first topic off _data/topic_queue.yml, asks Claude to draft a
blog post from it, writes the draft into _posts/, and removes the topic
from the queue. Intended to run inside the GitHub Action — never
publishes directly; the workflow opens a PR with the result so a human
reviews and merges before anything goes live.

Requires the ANTHROPIC_API_KEY secret to be set on the repo
(Settings -> Secrets and variables -> Actions).
"""
import datetime
import os
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
}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_queue():
    with open(QUEUE_PATH, "r") as f:
        return yaml.safe_load(f) or []


def save_queue(queue):
    with open(QUEUE_PATH, "w") as f:
        f.write(
            "# Queue of topics for the daily auto-post GitHub Action.\n"
            "# The workflow pops the FIRST item each run, generates a draft post from it,\n"
            "# opens a PR, and removes it from this list once the PR is created.\n"
            "#\n"
            "# category must be one of: Streaming Services | Devices | Installation Guides\n"
            "# Add new topics to the bottom of this list whenever you like.\n\n"
        )
        yaml.safe_dump(queue, f, sort_keys=False, allow_unicode=True)


def call_claude(title: str, category: str, brief: str) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    prompt = f"""Write a Jekyll blog post in Markdown for an Irish blog about LEGAL
streaming services and devices. Never mention, link to, or describe
unauthorized/unlicensed IPTV or streaming resale services.

Title: {title}
Category: {category}
Brief: {brief}

Requirements:
- Start directly with the article body in Markdown (no front matter, no title heading repeated).
- Use ## and ### headings, short paragraphs, and a short "Related" links section at the end.
- Include a one-sentence meta-description-style summary as the very first line, prefixed
  with "SUMMARY:", then a blank line, then the article.
- 500-800 words.
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
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []))


def main():
    queue = load_queue()
    if not queue:
        print("Topic queue is empty — add more topics to _data/topic_queue.yml.")
        sys.exit(0)

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

    today = datetime.date.today().isoformat()
    slug = slugify(title)
    filename = f"{today}-{slug}.md"
    filepath = os.path.join(POSTS_DIR, filename)

    front_matter = f"""---
title: "{title}"
excerpt: "{summary}"
description: "{summary}"
categories:
  - {category}
tags:
  - {CATEGORY_SLUGS.get(category, slugify(category))}
seo:
  type: Article
toc: true
draft_generated: true
# affiliate_links: true  # TODO: uncomment and add {{% include affiliate-disclosure.html %}} below if you add affiliate links during review
---

"""

    with open(filepath, "w") as f:
        f.write(front_matter + body + "\n")

    save_queue(queue)

    print(f"Draft written to {filepath}")
    # Emit for the workflow to use in the PR title/body
    print(f"::set-output name=post_path::{filepath}")
    print(f"::set-output name=post_title::{title}")


if __name__ == "__main__":
    main()
