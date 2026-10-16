#!/usr/bin/env python3
"""Post-image selection for On Air Ireland.

Policy (see scripts/card_kit/README.md):
  * Brand cards are the default (scripts/image_cards.py): unique, no logos.
  * A licensed Pexels photo is used only when the category allows it, the post
    has a clear real-world scene, and a candidate passes the relevance,
    no-reuse and diversity checks. Photos are downloaded and self-hosted, so
    the live site never loads images from a third party.
  * _data/image_ledger.yml records every card and photo this system creates,
    and every image already used by any post counts as "taken", so nothing is
    ever reused site-wide.

Used by scripts/generate_post.py via choose_hero().
"""
import datetime
import io
import os
import re

import yaml

try:  # Pillow is only needed once an image is actually produced
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    Image = ImageOps = None

import image_cards

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "_posts")
LEDGER_PATH = os.path.join(ROOT, "_data", "image_ledger.yml")

LEDGER_HEADER = """# Image ledger. Written by scripts/image_system.py (and scripts/image_cards.py).
# Every brand card and self-hosted photo created for a post is recorded here so
# nothing is reused. `retired` lists images removed from the old teaser pool and
# why. Safe to read; edit by hand only to correct a mistake.
"""

# Photos are only considered for these categories. Streaming Services, Devices,
# News and Reviews stay on brand cards: stock photos of those topics tend to show
# other companies' logos or imply hands-on testing, which the site avoids.
PHOTO_CATEGORIES = {
    "Watch-Guides": {"viewing-room", "remote-closeup"},
    "Troubleshooting": {"router-cabling", "remote-closeup", "hands-hdmi"},
    "Installation-Guides": {"hands-hdmi", "router-cabling", "aerial-roof"},
    "Sports-Streaming": {"sport-viewing", "viewing-room"},
}

SCENES = {
    "viewing-room": {
        "queries": ["people watching television living room", "family watching tv sofa"],
        "keywords": {"television", "tv", "living", "room", "sofa", "couch", "watching", "family", "home", "screen"},
    },
    "remote-closeup": {
        "queries": ["hand holding tv remote control", "television remote control"],
        "keywords": {"remote", "control", "controller", "hand", "tv", "television"},
    },
    "router-cabling": {
        "queries": ["wifi router cables", "ethernet cable router"],
        "keywords": {"router", "cable", "cables", "ethernet", "wifi", "wi-fi", "network", "modem", "internet", "broadband"},
    },
    "hands-hdmi": {
        "queries": ["hdmi cable connecting tv", "plugging cable into television"],
        "keywords": {"hdmi", "cable", "plug", "plugging", "connector", "port", "ports", "tv", "television", "connecting"},
    },
    "aerial-roof": {
        "queries": ["tv aerial on roof", "television antenna rooftop"],
        "keywords": {"antenna", "aerial", "roof", "rooftop", "tv", "television"},
    },
    "sport-viewing": {
        "queries": ["friends watching sport on tv", "football fans watching television"],
        "keywords": {"watching", "sport", "sports", "football", "soccer", "fans", "tv", "television", "pub", "friends", "match", "game"},
    },
}

BANNED_WORDS = {
    "logo", "logos", "netflix", "disney", "amazon", "prime", "youtube", "hbo", "hulu", "spotify",
    "instagram", "facebook", "twitter", "tiktok", "social", "icon", "icons", "screenshot", "brand",
    "trademark", "watermark", "advert", "advertisement", "billboard",
}
PEOPLE_WORDS = {
    "man", "men", "woman", "women", "people", "person", "family", "boy", "girl", "child", "children",
    "kid", "kids", "couple", "friends", "couple", "teen", "teenager", "baby", "mother", "father",
}

# Diversity limits
SCENE_COOLDOWN = 6   # same scene may not recur within this many recent photos
PEOPLE_COOLDOWN = 3  # at most one people-photo in this many recent photos


def _category_key(category):
    return (category or "").strip().replace(" ", "-")


# --------------------------------------------------------------------------
# Ledger
# --------------------------------------------------------------------------
def load_ledger(path=LEDGER_PATH):
    data = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    for key in ("cards", "photos", "retired"):
        data.setdefault(key, [])
    return data


def save_ledger(ledger, path=LEDGER_PATH):
    with open(path, "w", encoding="utf-8") as f:
        f.write(LEDGER_HEADER)
        yaml.safe_dump(
            {k: ledger.get(k, []) for k in ("cards", "photos", "retired")},
            f, sort_keys=False, allow_unicode=True, width=1000,
        )


def norm_image(url):
    """A stable identity for an image URL: pexels photo id, or normalised path."""
    if not url:
        return ""
    url = str(url).strip()
    m = re.search(r"pexels-photo-(\d+)", url)
    if m:
        return "pexels:" + m.group(1)
    if url.startswith("http"):
        return url.split("?")[0]
    return "/" + url.lstrip("/")


def _front_matter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def images_in_use(posts_dir=POSTS_DIR):
    """Identities of every image referenced by any post's header."""
    used = set()
    if not os.path.isdir(posts_dir):
        return used
    for name in os.listdir(posts_dir):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(posts_dir, name), encoding="utf-8") as f:
            header = (_front_matter(f.read()).get("header") or {})
        for key in ("overlay_image", "teaser", "image", "og_image"):
            if header.get(key):
                used.add(norm_image(header[key]))
    return used


def taken_identities(ledger, posts_dir=POSTS_DIR):
    taken = images_in_use(posts_dir)
    for p in ledger.get("photos", []):
        taken.add("pexels:" + str(p.get("pexels_id")))
        for f in (p.get("files") or {}).values():
            taken.add(norm_image(f))
    for c in ledger.get("cards", []):
        for f in (c.get("files") or {}).values():
            taken.add(norm_image(f))
    return taken


def card_fingerprints(ledger):
    return {c["fingerprint"] for c in ledger.get("cards", []) if c.get("fingerprint")}


def _recent(ledger, n):
    photos = sorted(ledger.get("photos", []), key=lambda p: str(p.get("created", "")), reverse=True)
    return photos[:n]


# --------------------------------------------------------------------------
# Pexels
# --------------------------------------------------------------------------
def search_pexels(query, api_key, per_page=30):
    import requests
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": per_page, "orientation": "landscape"},
        timeout=20,
    )
    if not resp.ok:
        print(f"Pexels API error {resp.status_code}: {resp.text[:200]}")
        return []
    return resp.json().get("photos", [])


def download_bytes(url):
    import requests
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def _words(text):
    return set(re.findall(r"[a-z0-9+\-]+", (text or "").lower()))


def score_candidate(photo, scene):
    """Return (accepted, reason, is_people). Relevance comes from Pexels' own
    description of the photo, so an empty description is rejected."""
    alt = (photo.get("alt") or "").strip()
    words = _words(alt)
    if not words:
        return False, "no description", False
    if words & BANNED_WORDS:
        return False, "mentions a brand, logo or app", False
    hits = len(words & SCENES[scene]["keywords"])
    if hits < 2:
        return False, f"weak match ({hits})", False
    if photo.get("width", 0) < 1600:
        return False, "too small", False
    return True, f"{hits} keyword hits", bool(words & PEOPLE_WORDS)


def choose_photo(scene, image_query, ledger, api_key, search=search_pexels, taken=None):
    """Best unused, relevant, diverse Pexels candidate for the scene, or None."""
    taken = taken if taken is not None else taken_identities(ledger)
    recent = _recent(ledger, max(SCENE_COOLDOWN, PEOPLE_COOLDOWN))
    if scene in {p.get("scene") for p in recent[:SCENE_COOLDOWN]}:
        print(f"Scene '{scene}' used recently -- using a card instead.")
        return None
    recent_people = any(p.get("people") for p in recent[:PEOPLE_COOLDOWN])

    queries = list(SCENES[scene]["queries"])
    if image_query and image_query.lower() not in [q.lower() for q in queries]:
        queries.append(image_query)
    best = None
    for q in queries:
        for photo in search(q, api_key):
            if "pexels:" + str(photo.get("id")) in taken:
                continue
            ok, reason, people = score_candidate(photo, scene)
            if not ok or (people and recent_people):
                continue
            hits = int(re.match(r"(\d+)", reason).group(1)) if re.match(r"\d+", reason) else 0
            rank = (hits, not people)
            if best is None or rank > best[0]:
                best = (rank, photo, people)
        if best and best[0][0] >= 4:
            break
    if not best:
        return None
    return {"photo": best[1], "people": best[2]}


def save_photo(slug, photo, download=download_bytes, out_dir=image_cards.POSTS_IMG_DIR):
    """Download the photo and write hero/teaser/og crops. Returns file paths."""
    src = photo.get("src", {})
    url = src.get("large2x") or src.get("large") or src.get("original")
    img = Image.open(io.BytesIO(download(url))).convert("RGB")
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    for kind, size in image_cards.SIZES.items():
        crop = ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.4))
        path = os.path.join(out_dir, f"{slug}-{kind}.jpg")
        crop.save(path, "JPEG", quality=82, optimize=True, progressive=True)
        files[kind] = "/" + os.path.relpath(path, ROOT).replace(os.sep, "/")
    return files


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def choose_hero(title, category, slug, scene="none", image_query="", post_file="",
                api_key=None, search=search_pexels, download=download_bytes,
                ledger_path=LEDGER_PATH, posts_dir=POSTS_DIR, out_dir=image_cards.POSTS_IMG_DIR):
    """Pick and create the header images for a post. Returns a dict with
    overlay_image / teaser / og_image (and caption for photos) ready for front
    matter, and records the choice in the ledger."""
    api_key = api_key if api_key is not None else os.environ.get("PEXELS_API_KEY", "")
    ledger = load_ledger(ledger_path)
    today = datetime.date.today().isoformat()
    cat = _category_key(category)
    scene = (scene or "none").strip().lower()

    if api_key and scene in PHOTO_CATEGORIES.get(cat, set()):
        found = choose_photo(scene, image_query, ledger, api_key, search=search,
                             taken=taken_identities(ledger, posts_dir))
        if found:
            photo = found["photo"]
            files = save_photo(slug, photo, download=download, out_dir=out_dir)
            credit = f"Photo: {photo.get('photographer')} / Pexels" if photo.get("photographer") else "Photo: Pexels"
            ledger["photos"].append({
                "id": f"photo-{slug}",
                "source": "pexels",
                "pexels_id": photo.get("id"),
                "pexels_url": photo.get("url"),
                "photographer": photo.get("photographer"),
                "licence": "Pexels licence (free to use; credit kept as a caption)",
                "description": photo.get("alt"),
                "scene": scene,
                "people": found["people"],
                "files": files,
                "created": today,
                "used_in": [post_file] if post_file else [],
            })
            save_ledger(ledger, ledger_path)
            return {"overlay_image": files["hero"], "teaser": files["teaser"],
                    "og_image": files["og"], "caption": credit, "kind": "photo"}

    card = image_cards.make_card(slug, title, category, card_fingerprints(ledger), out_dir=out_dir)
    ledger["cards"].append({
        "id": f"card-{slug}",
        "files": card["files"],
        "fingerprint": card["fingerprint"],
        "layout": card["layout"],
        "palette": card["palette"],
        "icons": card["icons"],
        "created": today,
        "used_in": [post_file] if post_file else [],
    })
    save_ledger(ledger, ledger_path)
    f = card["files"]
    return {"overlay_image": f["hero"], "teaser": f["teaser"], "og_image": f["og"], "kind": "card"}
