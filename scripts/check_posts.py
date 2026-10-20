#!/usr/bin/env python3
"""Validates every post's front matter. Run by .github/workflows/check-pr.yml.
Fails (exit 1) on errors; prints warnings for things worth fixing."""
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "_posts")
LEDGER = os.path.join(ROOT, "_data", "image_ledger.yml")
SHORTLIST = os.path.join(ROOT, "_data", "photo_shortlist.yml")
POST_IMAGES = os.path.join(ROOT, "assets", "images", "posts")
PAGE_IMAGES = os.path.join(ROOT, "assets", "images", "pages")
SCENES = {"viewing-room", "watching-together", "laptop-streaming", "remote-closeup", "sport-viewing",
          "stadium", "router-network", "cables-hdmi", "aerial-roof", "tv-trouble"}
VALID_CATEGORIES = {
    "Streaming-Services", "Devices", "Installation-Guides", "News",
    "Reviews", "Sports-Streaming", "Troubleshooting", "Watch-Guides",
}

errors, warnings = [], []


def image_identity(url):
    """Same image => same identity: Pexels photo id, or a normalised local path."""
    m = re.search(r"pexels-photo-(\d+)", url)
    if m:
        return "pexels:" + m.group(1)
    if url.startswith("http"):
        return url.split("?")[0]
    return "/" + url.lstrip("/")


def sniff_format(path):
    """jpg / png / webp / svg from the file's first bytes (not its extension)."""
    with open(path, "rb") as fh:
        head = fh.read(16)
    if head.startswith(b"\xff\xd8"):
        return "jpg"
    if head.startswith(b"\x89PNG"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.lstrip().startswith((b"<svg", b"<?xml")):
        return "svg"
    return "unknown"


try:
    ledger = yaml.safe_load(open(LEDGER, encoding="utf-8")) or {}
except FileNotFoundError:
    ledger = {}
ledger_files = {}
for kind in ("cards", "photos"):
    for entry in ledger.get(kind, []) or []:
        for f in (entry.get("files") or {}).values():
            ledger_files[image_identity(f)] = (kind, entry)

try:
    shortlist = (yaml.safe_load(open(SHORTLIST, encoding="utf-8")) or {}).get("photos") or []
except FileNotFoundError:
    shortlist = []

image_users = {}  # identity -> [post names]
pexels_hotlinks = 0
legacy_images = 0
for name in sorted(os.listdir(POSTS)):
    if not name.endswith(".md"):
        continue
    path = os.path.join(POSTS, name)
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        errors.append(f"{name}: missing front matter block")
        continue
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        errors.append(f"{name}: invalid YAML front matter: {e}")
        continue
    body = m.group(2)

    title = str(fm.get("title", "")).strip()
    if not title:
        errors.append(f"{name}: no title")
    elif title.lower().startswith("title:"):
        errors.append(f"{name}: title starts with 'title:' ({title!r})")
    cats = fm.get("categories") or []
    if not cats:
        errors.append(f"{name}: no category")
    elif cats[0] not in VALID_CATEGORIES:
        errors.append(f"{name}: unknown category {cats[0]!r}")
    desc = str(fm.get("description", "") or "")
    if not desc:
        warnings.append(f"{name}: no description")
    elif len(desc) > 160:
        warnings.append(f"{name}: description is {len(desc)} chars (aim for <= 155)")
    if "AFFILIATE_LINK_" in body or "TODO" in body:
        errors.append(f"{name}: contains a placeholder (AFFILIATE_LINK_ or TODO)")
    header = fm.get("header") or {}
    seen_here = set()
    for key in ("overlay_image", "overlay_image_small", "teaser", "og_image"):
        url = str(header.get(key) or "").strip()
        if not url:
            continue
        if url.endswith(")"):
            errors.append(f"{name}: image URL ends with ')': {url}")
        if url.startswith("http"):
            if "pexels.com" in url and key == "overlay_image":
                pexels_hotlinks += 1
        else:
            local = os.path.join(ROOT, url.lstrip("/"))
            if not os.path.exists(local):
                errors.append(f"{name}: image not found: {url}")
            else:
                ext = os.path.splitext(url)[1].lower().lstrip(".").replace("jpeg", "jpg")
                actual = sniff_format(local)
                if actual != ext:
                    errors.append(f"{name}: {url} is really a {actual} file (extension says {ext})")
            if re.search(r"/assets/images/(social-|logo)", "/" + url.lstrip("/")):
                errors.append(f"{name}: {key} uses a social/brand image ({url}); use the post's own card or photo")
        if key in ("overlay_image", "teaser"):
            ident = image_identity(url)
            if ident not in seen_here:
                seen_here.add(ident)
                image_users.setdefault(ident, []).append(name)
    hero = str(header.get("overlay_image") or "")
    entry = ledger_files.get(image_identity(hero)) if hero else None
    if entry and entry[0] == "photos" and "Pexels" not in str(header.get("caption") or ""):
        errors.append(f"{name}: photo header needs a 'Photo: ... on Pexels' credit in header.caption")
    if re.search(r"/assets/images/(headers|teasers)/", hero):
        legacy_images += 1

for ident, users in sorted(image_users.items()):
    if len(users) > 1:
        errors.append(f"image used by {len(users)} posts ({', '.join(u[:10] for u in users)}): {ident}")

# Ledger integrity: every generated image is recorded, and nothing recorded is missing.
for folder, web in ((POST_IMAGES, "/assets/images/posts/"), (PAGE_IMAGES, "/assets/images/pages/")):
    if os.path.isdir(folder):
        on_disk = {web + f for f in os.listdir(folder) if not f.startswith(".")}
        for path in sorted(on_disk - set(ledger_files)):
            errors.append(f"{path}: in {web.strip('/')} but not listed in _data/image_ledger.yml")
for ident in sorted(i for i in ledger_files if i.startswith("/") and not os.path.exists(os.path.join(ROOT, i.lstrip("/")))):
    errors.append(f"ledger lists a file that does not exist: {ident}")
fingerprints = [c.get("fingerprint") for c in ledger.get("cards", []) or []]
if len(fingerprints) != len(set(fingerprints)):
    errors.append("image_ledger.yml: two cards share the same composition fingerprint")
photo_ids = [p.get("pexels_id") for p in ledger.get("photos", []) or []]
if len(photo_ids) != len(set(photo_ids)):
    errors.append("image_ledger.yml: the same Pexels photo is recorded twice")
# Photo shortlist: only approved photos may be used, and entries must be valid.
statuses = {}
for e in shortlist:
    pid = str(e.get("id"))
    if pid in statuses:
        errors.append(f"photo_shortlist.yml: photo {pid} is listed twice")
    statuses[pid] = e.get("status")
    if e.get("status") not in ("pending", "approved", "rejected"):
        errors.append(f"photo_shortlist.yml: photo {pid} has unknown status {e.get('status')!r}")
    if e.get("scene") not in SCENES:
        errors.append(f"photo_shortlist.yml: photo {pid} has unknown scene {e.get('scene')!r}")
for p in ledger.get("photos", []) or []:
    if statuses.get(str(p.get("pexels_id"))) != "approved":
        errors.append(f"image_ledger.yml: photo {p.get('pexels_id')} is used but not approved in photo_shortlist.yml")
if legacy_images:
    warnings.append(f"{legacy_images} post(s) still use old shared header/teaser images; see _data/photo_assignments.yml")
if pexels_hotlinks:
    warnings.append(f"{pexels_hotlinks} post(s) still hotlink Pexels images (older posts; new posts self-host)")

for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)
print(f"Checked posts: {len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(1 if errors else 0)
