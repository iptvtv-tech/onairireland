#!/usr/bin/env python3
"""
Checks _data/seasonal_topics.yml against today's date and adds any in-season
topic to the front of _data/topic_queue.yml, unless it is already queued or
already published.

Run by the "Inject Seasonal Topics" workflow, which opens a PR with the
change -- nothing reaches the queue until that PR is merged. This script never
touches posts; it only curates the queue for the daily draft run.

The queue file is edited as text, not re-dumped, so its header notes and
section comments survive.
"""
import datetime
import os
import re
import unicodedata

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(REPO_ROOT, "_data", "topic_queue.yml")
SEASONAL_PATH = os.path.join(REPO_ROOT, "_data", "seasonal_topics.yml")
POSTS_DIR = os.path.join(REPO_ROOT, "_posts")

# Optional fields copied from a seasonal entry into the queue entry as-is.
PASSTHROUGH_FIELDS = ("pillar", "video", "video_angle", "whatsapp")


def load_yaml(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or default


def slugify(text: str) -> str:
    """Same rules as generate_post.slugify, so post filenames match."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("+", " plus").replace("'", "").replace("’", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def in_window(today_md: str, start: str, end: str) -> bool:
    if not start or not end:
        return False
    if start <= end:
        return start <= today_md <= end
    return today_md >= start or today_md <= end  # wraps across New Year


def window_end_date(today: datetime.date, start: str, end: str) -> datetime.date:
    """The actual date the current window closes (handles New Year wrap)."""
    month, day = (int(x) for x in end.split("-"))
    year = today.year
    if start > end and today.strftime("%m-%d") >= start:
        year += 1  # window started this year, ends next year
    return datetime.date(year, month, day)


def fill_placeholders(text: str, today: datetime.date) -> str:
    return text.replace("{month}", today.strftime("%B")).replace("{year}", str(today.year))


def published_slugs():
    slugs = set()
    if os.path.isdir(POSTS_DIR):
        for fname in os.listdir(POSTS_DIR):
            if fname.endswith(".md") and len(fname) > 14:
                slugs.add(fname[11:-3])  # strip "YYYY-MM-DD-" and ".md"
    return slugs


def insert_at_front(entries: list) -> None:
    """Insert entries before the first queue item, keeping every comment."""
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    block = yaml.safe_dump(entries, sort_keys=False, allow_unicode=True, width=1000)
    block = "# Added by inject_seasonal_topics.py\n" + block + "\n"

    for i, line in enumerate(lines):
        if line.startswith("- "):
            lines.insert(i, block)
            break
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append("\n" + block)

    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def set_output(name: str, value: str) -> None:
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if not gh_out:
        return
    with open(gh_out, "a", encoding="utf-8") as fh:
        fh.write(f"{name}<<OAIEOF\n{value}\nOAIEOF\n")


def main():
    today = datetime.date.today()
    today_md = today.strftime("%m-%d")
    seasonal = load_yaml(SEASONAL_PATH, [])
    queue = load_yaml(QUEUE_PATH, [])

    queued_titles = {t.get("title") for t in queue}
    posted = published_slugs()

    new_entries = []
    for topic in seasonal:
        start, end = topic.get("window_start", ""), topic.get("window_end", "")
        if not in_window(today_md, start, end):
            continue

        title = fill_placeholders(topic["title"], today)
        if title in queued_titles or slugify(title) in posted:
            continue

        entry = {
            "title": title,
            "category": topic["category"],
            "brief": fill_placeholders(topic.get("brief", ""), today),
        }
        for field in PASSTHROUGH_FIELDS:
            if field in topic:
                entry[field] = topic[field]
        entry["publish_by"] = window_end_date(today, start, end).isoformat()

        new_entries.append(entry)
        queued_titles.add(title)

    if not new_entries:
        print("No seasonal topics are in-window today, or all matches are already queued/posted.")
        set_output("added", "")
        return

    insert_at_front(new_entries)
    summary = "\n".join(f"- {e['title']} (publish by {e['publish_by']})" for e in new_entries)
    print(f"Added {len(new_entries)} seasonal topic(s) to the queue:\n{summary}")
    set_output("added", summary)


if __name__ == "__main__":
    main()
