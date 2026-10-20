#!/usr/bin/env python3
"""Post-image selection for On Air Ireland.

Policy (see scripts/card_kit/README.md):
  * Real photos are the main image. They come ONLY from the approved shortlist
    (_data/photo_shortlist.yml): Pexels photos a person has looked at and marked
    `status: approved`. Nothing is picked from a live search at post time.
  * Every photo gets the same treatment (2:1 crop, light colour grade in the
    post's category colour, accent bar on teasers, title on the share image),
    so the site looks organised while each photo stays real and unique.
  * A photo is downloaded only when a post uses it (never in bulk) and is
    self-hosted, so the live site never loads images from a third party.
  * When no approved, unused photo fits the post's scene, the post gets a
    unique brand card (scripts/image_cards.py) instead.
  * _data/image_ledger.yml records every card and photo, and every image used
    by any post counts as "taken", so nothing is ever reused site-wide.

Used by scripts/generate_post.py (choose_hero) and scripts/apply_photos.py.
"""
import datetime
import io
import os
import re

import yaml

try:  # Pillow is only needed once an image is actually produced
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps
except ImportError:  # pragma: no cover
    Image = ImageDraw = ImageEnhance = ImageOps = None

import image_cards

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "_posts")
LEDGER_PATH = os.path.join(ROOT, "_data", "image_ledger.yml")
SHORTLIST_PATH = os.path.join(ROOT, "_data", "photo_shortlist.yml")

LEDGER_HEADER = """# Image ledger. Written by scripts/image_system.py (and scripts/image_cards.py).
# Every brand card and self-hosted photo created for a post or page is recorded
# here so nothing is reused. `retired` lists images removed from the old teaser
# pool and why. Safe to read; edit by hand only to correct a mistake.
"""

SHORTLIST_HEADER = """# Approved photo shortlist (Pexels). The ONLY source of photos for posts.
#
# status:   pending  -> found by scripts/propose_photos.py or by hand, not yet checked
#           approved -> a person has looked at it: relevant, no logos, brands,
#                       watermarks, readable screens or identifiable children
#           rejected -> kept so it is never proposed again
# scene:    which kind of post it suits (see SCENES in scripts/image_system.py)
# focus:    optional vertical crop centre, 0 (top) to 1 (bottom); default 0.5
#
# Approve by changing `pending` to `approved` (in a PR, or ask Claude).
# A photo is downloaded only when a post uses it, then recorded in image_ledger.yml.
# Licence: Pexels licence (https://www.pexels.com/license/), free to use and
# modify; the photographer is credited on the post anyway.
"""

# What each scene shows. `queries` feed scripts/propose_photos.py; `keywords`
# must appear in Pexels' own description of a proposed photo.
SCENES = {
    "viewing-room": {
        "about": "a living room with a TV and no people (general streaming, prices, news)",
        "queries": ["living room wall mounted tv", "modern living room television"],
        "keywords": {"television", "tv", "living", "room", "sofa", "couch", "interior", "wall-mounted", "screen"},
    },
    "watching-together": {
        "about": "people watching TV at home, faces not the focus (watch guides, family viewing)",
        "queries": ["watching tv at home couch", "movie night living room"],
        "keywords": {"watching", "tv", "television", "movie", "sofa", "couch", "living", "night", "home"},
    },
    "laptop-streaming": {
        "about": "watching on a laptop, tablet or phone (apps, players, on-the-go viewing)",
        "queries": ["watching movie on laptop", "streaming on tablet at home"],
        "keywords": {"laptop", "tablet", "watching", "movie", "streaming", "bed", "sofa", "home"},
    },
    "remote-closeup": {
        "about": "a hand holding a TV remote (setup, settings, remote and pairing problems)",
        "queries": ["hand holding tv remote", "tv remote control close up"],
        "keywords": {"remote", "control", "hand", "tv", "television"},
    },
    "sport-viewing": {
        "about": "people watching sport on TV at home (where to watch a match)",
        "queries": ["friends watching sports on tv", "watching football at home"],
        "keywords": {"watching", "sport", "sports", "football", "soccer", "match", "game", "tv", "television", "cheering"},
    },
    "stadium": {
        "about": "a pitch, floodlights or stadium with no logos (sport rights, fixtures)",
        "queries": ["stadium floodlights", "football pitch night"],
        "keywords": {"stadium", "floodlights", "pitch", "field", "football", "soccer", "rugby", "lights", "sports"},
    },
    "router-network": {
        "about": "a home router or network cables (buffering, Wi-Fi, broadband fixes)",
        "queries": ["home wifi router", "ethernet cable router"],
        "keywords": {"router", "wifi", "wi-fi", "wireless", "ethernet", "cable", "cables", "network", "internet"},
    },
    "cables-hdmi": {
        "about": "HDMI or AV cables and ports (connecting devices, set-up guides)",
        "queries": ["hdmi cable", "tv ports cables"],
        "keywords": {"hdmi", "cable", "cables", "connector", "ports", "port", "plug"},
    },
    "aerial-roof": {
        "about": "a TV aerial or satellite dish on a roof (Saorview, Saorsat, reception)",
        "queries": ["tv antenna roof", "television aerial"],
        "keywords": {"antenna", "aerial", "roof", "rooftop", "satellite", "dish", "tv", "television"},
    },
    "tv-trouble": {
        "about": "a dark room with a blank or static TV (no signal, black screen fixes)",
        "queries": ["tv static dark room", "blank tv screen dark"],
        "keywords": {"static", "tv", "television", "dark", "screen", "blank", "room"},
    },
}

# Which scenes suit which category. A post may only take a photo from these.
CATEGORY_SCENES = {
    "Streaming-Services": ["viewing-room", "watching-together", "laptop-streaming", "remote-closeup"],
    "Watch-Guides": ["watching-together", "laptop-streaming", "viewing-room", "remote-closeup"],
    "News": ["viewing-room", "laptop-streaming", "remote-closeup", "watching-together"],
    "Reviews": ["viewing-room", "remote-closeup", "cables-hdmi"],
    "Devices": ["cables-hdmi", "remote-closeup", "viewing-room"],
    "Installation-Guides": ["cables-hdmi", "router-network", "aerial-roof", "viewing-room", "remote-closeup"],
    "Troubleshooting": ["router-network", "remote-closeup", "tv-trouble", "cables-hdmi"],
    "Sports-Streaming": ["sport-viewing", "stadium", "watching-together"],
}

BANNED_WORDS = {
    "logo", "logos", "netflix", "disney", "amazon", "prime", "youtube", "hbo", "hulu", "spotify",
    "apple", "samsung", "sony", "lg", "roku", "google", "chromecast", "tp-link", "macbook", "iphone",
    "instagram", "facebook", "twitter", "tiktok", "social", "icon", "icons", "screenshot", "brand",
    "trademark", "watermark", "advert", "advertisement", "billboard", "vpn", "flag", "flags",
    "beer", "child", "children", "kid", "kids", "baby",
}
PEOPLE_WORDS = {
    "man", "men", "woman", "women", "people", "person", "family", "boy", "girl", "couple",
    "friends", "teen", "teenager", "mother", "father", "group", "senior",
}

# Scenes too specific to stand in for another one: used only when asked for.
NO_FALLBACK = {"aerial-roof", "tv-trouble", "stadium"}

SCENE_COOLDOWN = 2   # when falling back to another scene, avoid the last 2 used
PEOPLE_COOLDOWN = 2  # after a people-photo, prefer one without people next time

CREDIT_LINK = "https://www.pexels.com"


def _category_key(category):
    return (category or "").strip().replace(" ", "-")


def scene_list_for_prompt():
    return "\n".join(f"  {k}: {v['about']}" for k, v in SCENES.items())


# --------------------------------------------------------------------------
# Ledger and shortlist
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


def load_shortlist(path=SHORTLIST_PATH):
    if not os.path.isfile(path):
        return {"photos": []}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("photos", [])
    return data


def save_shortlist(shortlist, path=SHORTLIST_PATH):
    with open(path, "w", encoding="utf-8") as f:
        f.write(SHORTLIST_HEADER)
        yaml.safe_dump({"photos": shortlist.get("photos", [])}, f,
                       sort_keys=False, allow_unicode=True, width=1000)


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
        for key in ("overlay_image", "overlay_image_small", "teaser", "image", "og_image"):
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
    """The n most recently added photos (ledger order breaks same-day ties)."""
    photos = [(str(p.get("created", "")), i, p) for i, p in enumerate(ledger.get("photos", [])) if p.get("scene")]
    photos.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [p for _, _, p in photos[:n]]


# --------------------------------------------------------------------------
# Choosing from the approved shortlist
# --------------------------------------------------------------------------
def choose_from_shortlist(scene, category, ledger, shortlist, taken, title=""):
    """An approved, unused shortlist entry for the post, or None.

    Relevance first: the requested scene is always used when it has a photo
    left; within it, a photo without people is preferred if the last photo
    had people. Only when the scene has nothing left does it fall back to
    another scene allowed for the category (one not used in the last photos)."""
    allowed = CATEGORY_SCENES.get(_category_key(category), [])
    if scene not in allowed:
        return None
    recent = _recent(ledger, max(SCENE_COOLDOWN, PEOPLE_COOLDOWN))
    recent_scenes = [p.get("scene") for p in recent[:SCENE_COOLDOWN]]
    recent_people = any(p.get("people") for p in recent[:PEOPLE_COOLDOWN - 1 or 1])
    pool = [e for e in shortlist.get("photos", [])
            if e.get("status") == "approved" and not e.get("use")
            and "pexels:" + str(e.get("id")) not in taken]

    title_words = {w for w in _words(title) if len(w) > 3}

    def best_in(s_name):
        options = [e for e in pool if e.get("scene") == s_name]
        # Prefer a photo whose description shares words with the title
        # (a rugby post gets the rugby pitch), then one without people if the
        # last photo had people.
        options.sort(key=lambda e: (-len(title_words & _words(e.get("description"))),
                                    bool(e.get("people")) if recent_people else False))
        return options[0] if options else None

    found = best_in(scene)
    if found:
        return found
    others = [x for x in allowed if x != scene and x not in NO_FALLBACK]
    for s_name in [x for x in others if x not in recent_scenes] + [x for x in others if x in recent_scenes]:
        found = best_in(s_name)
        if found:
            return found
    return None


# --------------------------------------------------------------------------
# Pexels (photo details and download happen only for a photo being used)
# --------------------------------------------------------------------------
def fetch_photo(photo_id, api_key):
    import requests
    resp = requests.get(f"https://api.pexels.com/v1/photos/{photo_id}",
                        headers={"Authorization": api_key}, timeout=20)
    resp.raise_for_status()
    return resp.json()


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
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def image_url(photo, width=2000):
    original = (photo.get("src") or {}).get("original", "")
    return f"{original}?auto=compress&cs=tinysrgb&w={width}" if original else ""


def _words(text):
    return set(re.findall(r"[a-z0-9+\-]+", (text or "").lower()))


def score_candidate(photo, scene):
    """For proposals: (accepted, reason, is_people), judged on Pexels' own
    description. Approval by a person is still required before use."""
    words = _words(photo.get("alt"))
    if not words:
        return False, "no description", False
    if words & BANNED_WORDS:
        return False, "mentions a brand, logo, flag, child or app", False
    hits = len(words & SCENES[scene]["keywords"])
    if hits < 2:
        return False, f"weak match ({hits})", False
    if photo.get("width", 0) < 2000:
        return False, "too small", False
    return True, f"{hits} keyword hits", bool(words & PEOPLE_WORDS)


def credit_markdown(photo):
    name = photo.get("photographer") or "a Pexels photographer"
    url = photo.get("url") or CREDIT_LINK
    return f"Photo: [{name}]({url}) on [Pexels]({CREDIT_LINK})"


# --------------------------------------------------------------------------
# The house photo treatment
# --------------------------------------------------------------------------
def _grade(img, palette):
    """One consistent finish for every photo: slightly calmer colour, a touch
    more contrast, and a 10% wash of the category colour."""
    pal = image_cards.PALETTES[image_cards.normalise_category(palette)]
    img = ImageEnhance.Color(img).enhance(0.88)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    tint = Image.new("RGB", img.size, image_cards._hex(pal["bg"][1]))
    return Image.blend(img, tint, 0.10)


def _left_shade(img, strength=0.82, floor=0.18):
    """Dark left-to-right shade so text on the share image reads."""
    w, h = img.size
    shade = Image.new("RGBA", (w, h), (8, 15, 30, 0))
    px = []
    for x in range(w):
        t = x / max(1, w - 1)
        a = strength - (strength - floor) * min(1.0, t / 0.75)
        px.append(int(255 * a))
    row = Image.new("L", (w, 1))
    row.putdata(px)
    shade.putalpha(row.resize((w, h)))
    base = img.convert("RGBA")
    base.alpha_composite(shade)
    return base


def _evening(img):
    """'mood: evening' on a shortlist entry: turns a bright daytime room into a
    dim, evening-lit one (darker, cooler walls, soft vignette) so it matches
    the site's dark heroes."""
    img = ImageEnhance.Brightness(img).enhance(0.6)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    navy = Image.new("RGB", img.size, (12, 24, 44))
    img = Image.blend(img, navy, 0.22)
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-w * 0.15, -h * 0.25, w * 1.15, h * 1.25), fill=255)
    from PIL import ImageFilter
    mask = mask.filter(ImageFilter.GaussianBlur(max(w, h) // 8))
    dark = ImageEnhance.Brightness(img).enhance(0.55)
    return Image.composite(img, dark, mask)


def treat_photo(img, palette, title, focus=0.5, mood=None):
    """Return {hero, hero_small, teaser, og} images from one photo."""
    img = img.convert("RGB")
    if mood == "evening":
        img = _evening(img)
    sizes = image_cards.SIZES
    centering = (0.5, max(0.0, min(1.0, float(focus))))
    hero = _grade(ImageOps.fit(img, sizes["hero"], Image.LANCZOS, centering=centering), palette)
    teaser = _grade(ImageOps.fit(img, sizes["teaser"], Image.LANCZOS, centering=centering), palette)
    pal = image_cards.PALETTES[image_cards.normalise_category(palette)]
    d = ImageDraw.Draw(teaser)
    w, h = teaser.size
    d.rectangle((0, h - 6, w, h), fill=image_cards._hex(pal["accent"]))
    og = _grade(ImageOps.fit(img, sizes["og"], Image.LANCZOS, centering=centering), palette)
    og = _left_shade(og)
    image_cards.draw_og_text(og, palette, title)
    return {
        "hero": hero,
        "hero_small": hero.resize(sizes["hero_small"], Image.LANCZOS),
        "teaser": teaser,
        "og": og.convert("RGB"),
    }


def make_photo_set(slug, photo, palette, title, focus=0.5, download=None,
                   out_dir=image_cards.POSTS_IMG_DIR, mood=None):
    raw = (download or download_bytes)(image_url(photo))
    img = Image.open(io.BytesIO(raw))
    return image_cards.save_set(treat_photo(img, palette, title, focus, mood), slug, out_dir)


def photo_ledger_entry(slug, photo, entry, files, used_in, today, palette):
    return {
        "id": f"photo-{slug}",
        "source": "pexels",
        "pexels_id": photo.get("id"),
        "pexels_url": photo.get("url"),
        "photographer": photo.get("photographer"),
        "licence": "Pexels licence (free to use and modify; credit kept as a caption)",
        "description": photo.get("alt") or entry.get("description"),
        "scene": entry.get("scene"),
        "people": bool(entry.get("people")),
        "palette": image_cards.normalise_category(palette),
        "files": files,
        "created": today,
        "used_in": used_in,
    }


# --------------------------------------------------------------------------
# Public entry point for new posts
# --------------------------------------------------------------------------
def choose_hero(title, category, slug, scene="none", image_query="", post_file="",
                api_key=None, fetch=None, download=None,
                ledger_path=LEDGER_PATH, shortlist_path=SHORTLIST_PATH,
                posts_dir=POSTS_DIR, out_dir=image_cards.POSTS_IMG_DIR):
    """Pick and create the header images for a post. Returns front-matter
    values (overlay_image, overlay_image_small, teaser, og_image, and caption
    for photos) and records the choice in the ledger."""
    api_key = api_key if api_key is not None else os.environ.get("PEXELS_API_KEY", "")
    ledger = load_ledger(ledger_path)
    shortlist = load_shortlist(shortlist_path)
    today = datetime.date.today().isoformat()
    scene = (scene or "none").strip().lower()
    used_in = [post_file] if post_file else []

    entry = None
    if api_key and scene != "none":
        entry = choose_from_shortlist(scene, category, ledger, shortlist,
                                      taken_identities(ledger, posts_dir), title=title)
        if not entry:
            print(f"No approved, unused photo for scene '{scene}' in {category}: using a card.")
    if entry:
        try:
            photo = (fetch or fetch_photo)(entry["id"], api_key)
            files = make_photo_set(slug, photo, category, title, entry.get("focus", 0.5),
                                   download=download, out_dir=out_dir, mood=entry.get("mood"))
        except Exception as exc:  # network or API trouble: fall back to a card
            print(f"Photo {entry['id']} could not be used ({exc}); using a card.")
        else:
            ledger["photos"].append(photo_ledger_entry(slug, photo, entry, files, used_in, today, category))
            save_ledger(ledger, ledger_path)
            return {"overlay_image": files["hero"], "overlay_image_small": files["hero_small"],
                    "teaser": files["teaser"], "og_image": files["og"],
                    "caption": credit_markdown(photo), "kind": "photo"}

    card = image_cards.make_card(slug, title, category, card_fingerprints(ledger), out_dir=out_dir)
    ledger["cards"].append({
        "id": f"card-{slug}",
        "files": card["files"],
        "fingerprint": card["fingerprint"],
        "layout": card["layout"],
        "palette": card["palette"],
        "icons": card["icons"],
        "created": today,
        "used_in": used_in,
    })
    save_ledger(ledger, ledger_path)
    f = card["files"]
    return {"overlay_image": f["hero"], "overlay_image_small": f["hero_small"],
            "teaser": f["teaser"], "og_image": f["og"], "kind": "card"}
