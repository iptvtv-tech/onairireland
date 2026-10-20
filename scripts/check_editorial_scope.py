#!/usr/bin/env python3
"""Guard public copy against excluded streaming topics in the site brief."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_PATHS = [ROOT / "index.html", ROOT / "_pages", ROOT / "_posts", ROOT / "_includes"]
PATTERNS = [
    re.compile(r"\bvpn\b", re.I),
    re.compile(r"\biptv\b", re.I),
    re.compile(r"\bunlicensed\b", re.I),
    re.compile(r"\bunauthori[sz]ed\b", re.I),
    re.compile(r"\bpiracy\b", re.I),
    re.compile(r"\bdodgy[ -]?box(?:es)?\b", re.I),
    re.compile(r"\bfully[ -]loaded\s+(?:box|stick)s?\b", re.I),
]
errors = []
for target in PUBLIC_PATHS:
    files = [target] if target.is_file() else target.rglob("*") if target.is_dir() else []
    for path in files:
        if not path.is_file() or path.suffix.lower() not in {".md", ".markdown", ".html", ".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern in PATTERNS:
                match = pattern.search(line)
                if match:
                    errors.append(f"{path.relative_to(ROOT)}:{line_no}: excluded-topic wording: {match.group(0)!r}")
for error in errors:
    print(f"ERROR: {error}")
print(f"Checked editorial scope: {len(errors)} issue(s)")
sys.exit(1 if errors else 0)
