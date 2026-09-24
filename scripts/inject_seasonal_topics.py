#!/usr/bin/env python3
"""
Checks _data/seasonal_topics.yml against today's date, and prepends any
currently-in-season topic to the front of _data/topic_queue.yml if it
isn't already queued or already published. Manually triggered via the
"Inject Seasonal Topics" GitHub Action -- does not touch posts directly,
just curates the queue so the next daily draft run picks it up.
"""
import datetime
import os
import re

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(REPO_ROOT, "_data", "topic_queue.yml")
SEASONAL_PATH = os.path.join(REPO_ROOT, "_data", "seasonal_topics.yml")
POSTS_DIR = os.path.join(REPO_ROOT, "_posts")


def load_yaml(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return yaml.safe_load(f) or default


def save_queue(queue):
    header = (
        "# Queue of topics for the daily auto-post GitHub Action.\n"
        "# The workflow pops the FIRST item each run, generates a draft post from it,\n"
        "# opens a PR, and removes it from this list once the PR is created.\n"
        "#\n"
        "# category must be one of: Streaming Services | Devices | Installation Guides |\n"
        "# News | Reviews | Sports Streaming | Troubleshooting | Watch Guides\n"
        "# (add a new category name here anytime -- Jekyll auto-generates its listing page,\n"
        "# no other file needs to change. Just keep spelling consistent across posts.)\n"
        "# Add new topics to the bottom of this list whenever you like.\n\n"
    )
    with open(QUEUE_PATH, "w") as f:
        f.write(header)
        yaml.safe_dump(queue, f, sort_keys=False, allow_unicode=True)


def in_window(today_md: str, start: str, end: str) -> bool:
    if start <= end:
        return start <= today_md <= end
    return today_md >= start or today_md <= end  # wraps across New Year


def existing_titles():
    titles = set()
    if os.path.isdir(POSTS_DIR):
        for fname in os.listdir(POSTS_DIR):
            if fname.endswith(".md"):
                titles.add(fname)  # rough dedupe by filename slug presence
    return titles


def main():
    today_md = datetime.date.today().strftime("%m-%d")
    seasonal = load_yaml(SEASONAL_PATH, [])
    queue = load_yaml(QUEUE_PATH, [])

    queued_titles = {t.get("title") for t in queue}
    posted_files = existing_titles()

    added = []
    for topic in seasonal:
        if not in_window(today_md, topic.get("window_start", ""), topic.get("window_end", "")):
            continue
        if topic["title"] in queued_titles:
            continue
        # Rough check: skip if a post file already contains this topic's slug
        slug_guess = re.sub(r"[^a-z0-9]+", "-", topic["title"].lower()).strip("-")
        if any(fname[11:-3] == slug_guess for fname in posted_files):
            continue

        entry = {
            "title": topic["title"],
            "category": topic["category"],
            "brief": topic["brief"],
        }
        queue.insert(0, entry)
        added.append(topic["title"])

    if added:
        save_queue(queue)
        print(f"Injected {len(added)} seasonal topic(s) into the queue:")
        for t in added:
            print(f"  - {t}")
    else:
        print("No seasonal topics are in-window today, or all matches are already queued/posted.")


if __name__ == "__main__":
    main()
