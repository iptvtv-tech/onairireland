#!/usr/bin/env python3
"""Give existing posts (or the static pages) a photo from the approved shortlist.

Reads _data/photo_assignments.yml:

  assignments:
    - target: static-pages          # every page that uses the shared header image
      photo: 7546648                # an approved shortlist id
    - target: _posts/2026-09-04-legal-streaming-services-ireland-2026.md
      scene: viewing-room           # best approved, unused photo for this scene
    - target: _posts/....md
      photo: 21792101               # or a specific approved photo

For each entry it downloads that one photo (Pexels API), applies the house
treatment, self-hosts the files, updates the front matter and the ledger, and
removes the entry from the list. A post whose scene has no approved, unused
photo gets a unique brand card instead, so it still leaves the old images.

Run by .github/workflows/apply-photos.yml (needs PEXELS_API_KEY), which opens a
PR for review. Nothing goes live until that PR is merged. At most MAX_ITEMS
(default 30) entries are processed per run, so each PR stays reviewable; run
the workflow again for the next batch. A post that already has a brand card
keeps it (and stays in the list) when no approved photo fits its scene; when it
does get a photo, its old card files and ledger entry are removed.
"""
import datetime
import io
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import image_cards  # noqa: E402
import image_system as s  # noqa: E402

ASSIGNMENTS = os.path.join(s.ROOT, "_data", "photo_assignments.yml")
PAGES_DIR = os.path.join(s.ROOT, "_pages")
PAGES_IMG_DIR = os.path.join(s.ROOT, "assets", "images", "pages")
SHARED_PAGE_IMAGE = "/assets/images/teasers/streaming-8.jpg"
ASSIGNMENTS_HEADER = """# Photos to apply to existing posts or the static pages. Each entry is processed
# by scripts/apply_photos.py (workflow "Apply photos"), which opens a PR and then
# removes the entry. Use `photo: <approved shortlist id>` or `scene: <scene>`.
# target: static-pages applies one photo to every page using the shared header.
"""


def load_assignments():
    if not os.path.isfile(ASSIGNMENTS):
        return []
    with open(ASSIGNMENTS, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("assignments") or []


def save_assignments(items):
    with open(ASSIGNMENTS, "w", encoding="utf-8") as f:
        f.write(ASSIGNMENTS_HEADER)
        yaml.safe_dump({"assignments": items}, f, sort_keys=False, allow_unicode=True, width=1000)


def split_front_matter(text):
    m = re.match(r"^(---\n)(.*?)(\n---\n)(.*)$", text, re.S)
    if not m:
        raise ValueError("no front matter")
    return m.group(1), m.group(2), m.group(3), m.group(4)


def set_header(path, values, drop=("overlay_image", "overlay_image_small", "teaser", "og_image", "caption")):
    """Rewrite the header: block of a post/page, keeping keys not in `drop`."""
    text = open(path, encoding="utf-8").read()
    a, front, b, body = split_front_matter(text)
    hm = re.search(r"^header:\n((?:[ \t]+.*\n?)+)", front + "\n", re.M)
    kept = []
    if hm:
        kept = [ln for ln in hm.group(1).splitlines() if ln.strip().split(":")[0] not in drop]
    new = "header:\n" + "".join(f"  {k}: {_yaml_scalar(v)}\n" for k, v in values.items()) \
        + "".join(ln + "\n" for ln in kept)
    if hm:
        front2 = (front + "\n").replace(hm.group(0), new, 1).rstrip("\n")
    else:
        front2 = front.rstrip("\n") + "\n" + new.rstrip("\n")
    open(path, "w", encoding="utf-8").write(a + front2 + b + body)


def _yaml_scalar(v):
    return yaml.safe_dump(v, default_flow_style=True, width=1000).strip().removesuffix("...").strip()


def shortlist_entry(shortlist, photo_id):
    for e in shortlist["photos"]:
        if str(e.get("id")) == str(photo_id):
            return e
    return None


def apply_static_pages(item, shortlist, ledger, api_key, today):
    entry = shortlist_entry(shortlist, item["photo"])
    if not entry or entry.get("status") != "approved":
        raise SystemExit(f"Photo {item['photo']} is not approved in the shortlist.")
    photo = s.fetch_photo(entry["id"], api_key)
    images = s.treat_photo(s.Image.open(io.BytesIO(s.download_bytes(s.image_url(photo)))),
                           "Streaming-Services", "", entry.get("focus", 0.5), entry.get("mood"))
    images.pop("og")  # pages keep their designed social images
    files = image_cards.save_set(images, "site-hero", PAGES_IMG_DIR)
    changed = []
    for name in sorted(os.listdir(PAGES_DIR)):
        path = os.path.join(PAGES_DIR, name)
        if not name.endswith(".md"):
            continue
        text = open(path, encoding="utf-8").read()
        if "teasers/streaming-8.jpg" not in text:
            continue
        values = {"overlay_image": files["hero"], "overlay_image_small": files["hero_small"],
                  "teaser": files["teaser"], "image_description": entry.get("description", "")}
        set_header(path, values, drop=("overlay_image", "overlay_image_small", "teaser", "image_description"))
        changed.append(name)
    ledger["photos"].append(s.photo_ledger_entry("site-hero", photo, entry, files,
                                                 ["static pages (" + str(len(changed)) + ")"], today,
                                                 "Streaming-Services"))
    print(f"Static pages: {len(changed)} pages now use photo {entry['id']}.")


def apply_post(item, shortlist, ledger, api_key, today):
    path = os.path.join(s.ROOT, item["target"])
    text = open(path, encoding="utf-8").read()
    fm = s._front_matter(text)
    title = fm.get("title", "")
    category = (fm.get("categories") or ["Streaming-Services"])[0]
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(path)[:-3])
    taken = s.taken_identities(ledger)
    entry = None
    if item.get("photo"):
        entry = shortlist_entry(shortlist, item["photo"])
        if not entry or entry.get("status") != "approved" or "pexels:" + str(entry["id"]) in taken:
            print(f"{item['target']}: photo {item['photo']} is not approved or already used.")
            entry = None
    elif item.get("scene") and api_key:
        entry = s.choose_from_shortlist(item["scene"], category, ledger, shortlist, taken, title=title)
    old_cards = [c for c in ledger["cards"] if os.path.basename(path) in (c.get("used_in") or [])]
    if not entry and old_cards:
        print(f"{item['target']}: no approved, unused photo for scene {item.get('scene')!r}; "
              "keeps its card and stays in the list.")
        return False
    values = None
    if entry:
        try:
            photo = s.fetch_photo(entry["id"], api_key)
            files = s.make_photo_set(slug, photo, category, title, entry.get("focus", 0.5), mood=entry.get("mood"))
        except Exception as exc:
            print(f"{item['target']}: photo {entry['id']} failed ({exc}); using a card.")
        else:
            ledger["photos"].append(s.photo_ledger_entry(slug, photo, entry, files,
                                                         [os.path.basename(path)], today, category))
            values = {"overlay_image": files["hero"], "overlay_image_small": files["hero_small"],
                      "teaser": files["teaser"], "og_image": files["og"],
                      "caption": s.credit_markdown(photo)}
            retire_cards(old_cards, files, ledger)
    if values is None:
        card = image_cards.make_card(slug, title, category, s.card_fingerprints(ledger))
        ledger["cards"].append({"id": f"card-{slug}", "files": card["files"], "fingerprint": card["fingerprint"],
                                "layout": card["layout"], "palette": card["palette"], "icons": card["icons"],
                                "created": today, "used_in": [os.path.basename(path)]})
        f = card["files"]
        values = {"overlay_image": f["hero"], "overlay_image_small": f["hero_small"],
                  "teaser": f["teaser"], "og_image": f["og"]}
    set_header(path, values)
    print(f"{item['target']}: {'photo ' + str(entry['id']) if 'caption' in values else 'brand card'}")
    return True


def retire_cards(cards, new_files, ledger):
    """A post that moved from a brand card to a photo: drop the card from the
    ledger and delete its files (unless the photo reused the same file name)."""
    keep = set(new_files.values())
    for card in cards:
        for f in (card.get("files") or {}).values():
            if f not in keep:
                full = os.path.join(s.ROOT, f.lstrip("/"))
                if os.path.exists(full):
                    os.remove(full)
        ledger["cards"].remove(card)


def main():
    items = load_assignments()
    if not items:
        print("No photo assignments.")
        return 0
    api_key = os.environ.get("PEXELS_API_KEY", "")
    shortlist = s.load_shortlist()
    ledger = s.load_ledger()
    today = datetime.date.today().isoformat()
    limit = int(os.environ.get("MAX_ITEMS", "30"))  # keep each PR reviewable
    remaining = []
    done = 0
    for item in items:
        target = item.get("target", "")
        if done >= limit:
            remaining.append(item)
            continue
        if target == "static-pages":
            if not api_key:
                print("static-pages needs PEXELS_API_KEY; left in the list.")
                remaining.append(item)
                continue
            apply_static_pages(item, shortlist, ledger, api_key, today)
        elif target.startswith("_posts/") and os.path.isfile(os.path.join(s.ROOT, target)):
            if not apply_post(item, shortlist, ledger, api_key, today):
                remaining.append(item)
                continue
        else:
            print(f"Unknown target {target!r}; left in the list.")
            remaining.append(item)
            continue
        done += 1
        s.save_ledger(ledger)  # after every item, so a later failure loses nothing
    save_assignments(remaining)
    if remaining:
        print(f"{len(remaining)} assignment(s) left for the next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
