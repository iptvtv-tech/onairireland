#!/usr/bin/env python3
"""Tell Bing (and the other IndexNow search engines) which pages changed.

IndexNow (https://www.indexnow.org) lets a site ping search engines when a
page is added, updated, redirected or deleted, instead of waiting for a
recrawl. Bing shares the pings with the engines that use its index, such as
DuckDuckGo and Ecosia. Google does not use IndexNow.

The key is public by design: it lives in the site root as <key>.txt
(e73c09cfe9264b47a4a3f9ab2d383077.txt), which proves we own the site.

Usage:
  python scripts/indexnow.py --from <sha> --to <sha>   # pages changed between two commits
  python scripts/indexnow.py --url https://onairireland.ie/... [--url ...]
  add --dry-run to print the list without sending it.

For each changed post it sends the post's address and any redirect_from
addresses; for a deleted or renamed post, its old address too (which now
redirects or returns 404, both of which IndexNow wants to hear about).
Changed pages in _pages/ are sent by their permalink.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request

import yaml

SITE = "https://onairireland.ie"
HOST = "onairireland.ie"
KEY = "e73c09cfe9264b47a4a3f9ab2d383077"
ENDPOINT = "https://api.indexnow.org/indexnow"
POST_NAME = re.compile(r"^_posts/\d{4}-\d{2}-\d{2}-(.+)\.md$")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def front_matter(sha, path):
    """Front matter of a file at a commit, or None if it isn't there."""
    try:
        text = git("show", f"{sha}:{path}")
    except subprocess.CalledProcessError:
        return None
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def urls_for(sha, path):
    fm = front_matter(sha, path)
    if fm is None or fm.get("published") is False:
        return []
    urls = []
    m = POST_NAME.match(path)
    if m:
        cats = fm.get("categories") or []
        if isinstance(cats, str):
            cats = [cats]
        if not cats:
            return []
        urls.append(f"{SITE}/{str(cats[0]).lower()}/{m.group(1)}/")
    elif path.startswith("_pages/") and fm.get("permalink"):
        urls.append(SITE + fm["permalink"])
    for extra in fm.get("redirect_from") or []:
        urls.append(SITE + extra)
    return urls


def changed_urls(old, new):
    out = git("diff", "--name-status", "-M", old, new, "--", "_posts", "_pages")
    urls = []
    for line in out.splitlines():
        parts = line.split("\t")
        status, paths = parts[0], parts[1:]
        if status.startswith("R"):
            urls += urls_for(old, paths[0]) + urls_for(new, paths[1])
        elif status == "D":
            urls += urls_for(old, paths[0])
        else:
            urls += urls_for(new, paths[0])
    seen, unique = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def submit(urls):
    body = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": f"{SITE}/{KEY}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="old")
    ap.add_argument("--to", dest="new", default="HEAD")
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    urls = list(args.url)
    if args.old:
        urls += changed_urls(args.old, args.new)
    urls = [u for u in dict.fromkeys(urls) if u.startswith(SITE + "/")]
    if not urls:
        print("No changed pages to submit.")
        return 0
    print(f"{len(urls)} URL(s):")
    for u in urls:
        print("  " + u)
    if args.dry_run:
        return 0
    status, text = 0, ""
    for i in range(0, len(urls), 10000):
        status, text = submit(urls[i:i + 10000])
        print(f"IndexNow answered {status} {text.strip()[:200]}")
        # 200 = received, 202 = received, key check pending. Anything else is a problem.
        if status not in (200, 202):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
