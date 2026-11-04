#!/usr/bin/env python3
"""
Fail the PR check while a post still lists wrong claims. Run by check-pr.yml.

In the Mon/Wed/Fri draft run, the claims list (scripts/fact_check.py) checks the
draft, sends any flagged claims back to the writer once and checks it again. A
claim still marked ❌ wrong after that is written into the post's front matter
as fact_check_wrong. With the merge lock (the `check` status is required), that
post can't be merged until someone fixes each line and deletes the list.

To clear it: correct or remove each claim in the post (or in the social draft
before posting it), then delete fact_check_wrong from the front matter.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def main() -> int:
    flagged = 0
    posts = sorted(glob.glob(os.path.join(ROOT, "_posts", "*.md")))
    for path in posts:
        with open(path, encoding="utf-8") as fh:
            m = FRONT_MATTER.match(fh.read())
        if not m:
            continue  # check_posts.py reports missing front matter
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue  # check_posts.py reports broken front matter
        wrong = fm.get("fact_check_wrong") if isinstance(fm, dict) else None
        if not wrong:
            continue
        items = wrong if isinstance(wrong, list) else [wrong]
        flagged += 1
        print(f"ERROR {os.path.relpath(path, ROOT)}: {len(items)} wrong claim(s) from the fact check:")
        for item in items:
            print(f"  ❌ {item}")
    if flagged:
        print("Fix each claim in the post (or the social draft), then delete fact_check_wrong "
              "from the post's front matter.")
    print(f"Checked fact-check flags: {len(posts)} post(s), {flagged} with wrong claims left")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
