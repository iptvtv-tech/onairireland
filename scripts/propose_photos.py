#!/usr/bin/env python3
"""Top up the photo shortlist with new candidates for a person to review.

For every scene with fewer than TARGET approved, unused photos, search Pexels
and add up to PER_SCENE new candidates to _data/photo_shortlist.yml as
`status: pending`. Nothing is downloaded: only the photo's id, description and
photographer are stored. Writes photo_review.md (thumbnails for the PR body),
which is not committed.

Run by .github/workflows/propose-photos.yml (needs PEXELS_API_KEY).
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import image_system as s  # noqa: E402

TARGET = 6      # approved, unused photos wanted per scene
PER_SCENE = 6   # most candidates added per scene per run
REVIEW_FILE = os.path.join(s.ROOT, "photo_review.md")


def main():
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        print("PEXELS_API_KEY is not set; nothing to do.")
        return 0
    shortlist = s.load_shortlist()
    ledger = s.load_ledger()
    taken = s.taken_identities(ledger)
    known = {str(e.get("id")) for e in shortlist["photos"]}
    today = datetime.date.today().isoformat()
    added = []

    for scene, spec in s.SCENES.items():
        ready = [e for e in shortlist["photos"]
                 if e.get("scene") == scene and e.get("status") == "approved" and not e.get("use")
                 and "pexels:" + str(e.get("id")) not in taken]
        pending = [e for e in shortlist["photos"] if e.get("scene") == scene and e.get("status") == "pending"]
        want = min(PER_SCENE, max(0, TARGET - len(ready) - len(pending)))
        if not want:
            continue
        for query in spec["queries"]:
            for photo in s.search_pexels(query, api_key):
                pid = str(photo.get("id"))
                if want == 0 or pid in known or "pexels:" + pid in taken:
                    continue
                ok, reason, people = s.score_candidate(photo, scene)
                if not ok:
                    continue
                entry = {
                    "id": photo["id"], "scene": scene, "status": "pending",
                    "description": (photo.get("alt") or "").strip(), "people": people,
                    "pexels_url": photo.get("url"), "photographer": photo.get("photographer"),
                    "added": today,
                }
                shortlist["photos"].append(entry)
                known.add(pid)
                added.append((entry, (photo.get("src") or {}).get("medium", "")))
                want -= 1
            if want == 0:
                break

    if not added:
        print("Every scene has enough approved or pending photos.")
        return 0
    s.save_shortlist(shortlist)
    lines = [
        f"{len(added)} new photo candidates. Look at each one, then in `_data/photo_shortlist.yml` "
        "change `pending` to `approved` or `rejected` before merging. Reject anything with a "
        "readable logo, brand, app on screen, watermark, flag, identifiable child, or that "
        "simply doesn't look right for an Irish legal-streaming site.",
        "",
        "| Photo | id | scene | description |",
        "| --- | --- | --- | --- |",
    ]
    for entry, thumb in added:
        img = f"![{entry['id']}]({thumb})" if thumb else ""
        lines.append(f"| {img} | [{entry['id']}]({entry['pexels_url']}) | {entry['scene']} | "
                     f"{entry['description'].replace('|', '/')} |")
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Added {len(added)} pending candidates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
