#!/usr/bin/env python3
"""Checks every _video_scripts/*.short.yml (the YouTube Short specs) before merge:
the shape the renderer needs, YouTube's limits, the article link in the
description, and no words the site never uses. Exits 1 on any problem."""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "video"))
import short_spec  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    failed = 0
    paths = sorted(glob.glob(os.path.join(REPO_ROOT, "_video_scripts", "*.short.yml")))
    for path in paths:
        rel = os.path.relpath(path, REPO_ROOT)
        try:
            spec = short_spec.load(path)
        except Exception as exc:
            print(f"❌ {rel}: doesn't parse: {exc}")
            failed += 1
            continue
        problems = short_spec.problems(spec)
        post = (spec or {}).get("post") if isinstance(spec, dict) else None
        if post and not os.path.isfile(os.path.join(REPO_ROOT, post)):
            problems.append(f"its post {post} doesn't exist")
        if problems:
            failed += 1
            for p in problems:
                print(f"❌ {rel}: {p}")
    print(f"Checked {len(paths)} YouTube Short spec(s): {failed} with problems.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
