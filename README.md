# On Air Ireland

Jekyll blog (Minimal Mistakes theme) about **legal** streaming services,
devices, and installation guides for Ireland. Deployed via GitHub Pages
to `onairireland.ie`.

## 1. Push this repo to GitHub

```bash
git init
git add .
git commit -m "Initial site scaffold"
git branch -M main
git remote add origin https://github.com/YOURUSERNAME/onairireland.git
git push -u origin main
```

Update `repository:` in `_config.yml` to match your actual GitHub path.

## 2. Enable GitHub Pages

Repo → **Settings → Pages** → Source: `main` branch, `/ (root)` → Save.

## 3. Point onairireland.ie at GitHub Pages

At your DNS registrar for `onairireland.ie`:

**Apex domain (`onairireland.ie`)** — four A records:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

**Or `www.onairireland.ie`** — a CNAME record pointing to `YOURUSERNAME.github.io`

The `CNAME` file in this repo is already set to `onairireland.ie` — GitHub
Pages reads it automatically, you don't need to re-enter the domain unless
it gets reset.

Back in **Settings → Pages**, tick **Enforce HTTPS** once DNS has propagated
(can take minutes to hours).

## 4. SEO setup already included

- The Minimal Mistakes theme's own `_includes/seo.html` generates the title
  tag, meta description (from each page's `description`), Open Graph and
  Twitter tags, and canonical URLs. The default share image is `og_image`
  in `_config.yml`.
- `_includes/head/custom.html` adds favicons, verification tags,
  Organization and BreadcrumbList JSON-LD.
- `jekyll-sitemap` generates `/sitemap.xml`; `robots.txt` points to it.
  Add `sitemap: false` to a page's front matter to leave it out.
- Per-post `description`, `excerpt`, `categories`, `tags` and optional
  `faqs` (rendered by `faq-section.html` with FAQPage schema).

## 4b. Checks before publishing

Run these locally before opening or reviewing a publishing PR:

```bash
python scripts/check_posts.py
python scripts/check_prices_data.py
python scripts/check_site_facts.py
python scripts/check_products.py
python scripts/check_affiliate_links.py
python scripts/check_editorial_scope.py
python scripts/check_price_news_links.py
python scripts/check_price_sources.py
python scripts/check_shorts.py
```

- `check_posts.py` validates post front matter, required image metadata,
  image-ledger integrity, and leftover `TODO`/`AFFILIATE_LINK_` placeholders.
- `check_prices_data.py` validates price data structure and warns when a row
  has not been checked recently. It does **not** confirm prices against live
  provider pages; that remains an editorial fact-check.
- `check_site_facts.py` validates `_data/site_facts.yml` (every entry needs
  facts, https sources and a checked date) and warns when an entry hasn't been
  confirmed for 100 days.
- `check_products.py` enforces approved product categories, local product image
  paths, HTTPS affiliate URLs, unique IDs, and `show_prices: false`.
- `check_affiliate_links.py` checks that Amazon affiliate links in Markdown/HTML
  declare `rel="sponsored"` and that posts containing them include the affiliate
  disclosure. It covers source markup; still inspect rendered HTML after changes.
- `check_editorial_scope.py` flags excluded-topic wording in public copy.
- `check_price_news_links.py` makes price-change news posts link to the canonical
  `/streaming-prices/` tracker.
- `check_price_sources.py` guards the price table against unapproved domains; the
  allowlist does not replace checking that each current rate is actually stated at
  the source URL.
- `check_shorts.py` checks the YouTube Short specs (`_video_scripts/*.short.yml`):
  the shape the renderer needs, YouTube's title, description and tag limits, the
  article link in the description, and excluded-topic wording.
- `.github/workflows/check-pr.yml` runs the repository's automated checks and a
  full GitHub Pages build on every pull request. The draft workflow checks posts
  before it opens its PR.

## 4c. Prices

`show_prices: false` in `_config.yml` hides the hand-typed `price` values in
`_data/products.yml` everywhere (cards, Best Prices, quiz, hover previews).
Amazon's Associates rules only allow showing prices pulled live from their
Product Advertising API, so leave this off unless you add that.

## 5. Affiliate product showcase (Amazon Associates + others)

Posts now show a **colorful product card grid** ("Recommended for This Guide") that auto-pulls relevant products by category. This replaces manually hunting through post files to update a link.

**How it works:**
- `_data/products.yml` is the single source of truth — every product's name, image, price, badge, blurb, and affiliate link lives here **once**
- Each post includes a showcase matched to its own category, e.g.:
  ```liquid
  {% raw %}{% include product-showcase.html category="Devices" title="Our Picks: Streaming Devices" %}{% endraw %}
  ```
- **Update a link, price, or image in `_data/products.yml` and it updates on every post that shows that category — no need to touch individual posts.**
- Product images are generic SVG illustrations in `assets/images/products/` (one per product type, made to match the site). To use your own photo of a device you own, save it as e.g. `assets/images/products/fire-tv-stick-4k.jpg` (4:3, about 800x600) and point that product's `image:` at it. Don't download Amazon's product photos: the Associates licence doesn't allow storing them on your site.
- The `category="..."` in a showcase is the **post type** asking for products. Every product whose `show_on` list includes that post type is placed in the page, and `assets/js/product-shuffle.js` shows a random three on each load, so all matching products rotate. Without JavaScript the first three in file order show.
- The disclosure line under each product grid is required by Ireland's CCPC/ASAI advertising rules — don't remove it

**To find every affiliate link that still needs a real URL:**
```bash
grep -n "AFFILIATE_LINK_" _data/products.yml
```

**To add a new product:** copy an existing entry in `_data/products.yml`, give it a unique `id`, set its `category` to one of `Streaming Services`, `Devices`, or `Installation Guides` (what the product is), and set `show_on` to the post types it suits, e.g. `show_on: ["Troubleshooting", "Installation Guides"]`. It then joins the rotation on those posts, the quiz and the Best Prices page. Run `python scripts/check_products.py` to catch typos.

**To add the showcase to a new post:** just add `{% raw %}{% include product-showcase.html category="Devices" %}{% endraw %}` anywhere in the post body — it renders nothing if there are no matching products yet.

**To link a product inside a sentence:** never paste an Amazon link into a post. Use `{% raw %}{% include product-link.html id="fire-tv-stick-4k" text="Fire TV Stick 4K" %}{% endraw %}` — the address comes from `_data/products.yml` (so changing it there updates every post) and the link is always marked `rel="nofollow sponsored noopener"`. If the product isn't in the catalogue yet, add it first. `scripts/check_affiliate_links.py` fails on raw Amazon links in posts and on unknown ids, and the draft generator converts links automatically.

## 6. Plain affiliate link placeholders (older/simpler pattern)

The sample posts already include placeholder affiliate links and a
disclosure notice, ready to swap in real links once you're approved for a
program (e.g. Amazon Associates, a retailer's affiliate program).

**How it works:**
- `_includes/affiliate-disclosure.html` — a reusable disclosure box,
  included at the top of any post that has affiliate links via
  `{% raw %}{% include affiliate-disclosure.html %}{% endraw %}`.
  Ireland's CCPC/ASAI rules require this disclosure on any post with
  affiliate or sponsored links — don't remove it.
- Each post with affiliate links has `affiliate_links: true` in its
  front matter, so you can filter/find them later if needed.
- Inline links use placeholder text like `AFFILIATE_LINK_FIRE_TV_STICK`
  — search the repo for `AFFILIATE_LINK_` and `TODO` to find every spot
  that needs a real link:
  ```bash
  grep -rn "AFFILIATE_LINK_\|TODO" _posts/
  ```
- Not every company runs an affiliate program — if one doesn't, remove
  the link and leave the product/service as plain text rather than
  linking to a non-affiliate URL for no reason.

**Adding affiliate links to new posts:** copy the same pattern —
`affiliate_links: true` in front matter, the disclosure include right
after the front matter, and `AFFILIATE_LINK_...` placeholders (or real
links) wherever you mention a purchasable product or service.

## 7. Writing posts manually

Add a file to `_posts/` named `YYYY-MM-DD-title.md`, following the front
matter pattern in the existing sample posts. Push to `main` and it's live
in a minute or two.

## 8. Daily auto-draft posts (PR-based, not auto-publish)

`.github/workflows/daily-draft-post.yml` runs Monday, Wednesday and Friday, pulls the next topic
from `_data/topic_queue.yml`, asks Claude to draft a post, and opens a
**Pull Request** — it never publishes directly. You review the draft for
accuracy (prices, app steps, current availability), then merge to publish.

**Setup required:**
1. Get an Anthropic API key from [console.anthropic.com](https://console.anthropic.com)
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `ANTHROPIC_API_KEY`
   - Value: your key
3. Add topics anytime by appending to `_data/topic_queue.yml`. When the
   queue is empty, the workflow opens a PR with AI-suggested topics instead
   of a post — edit or delete them before merging.
4. To run it on demand instead of waiting for the daily schedule: **Actions tab → Daily Draft Post → Run workflow**

**Checked facts and the fact check:** the writer has no web access, so it gets
the facts in `_data/site_facts.yml` (who shows each competition in Ireland,
what the NOW sport memberships include) and the prices in `_data/prices.yml`,
and may only state those. After the draft and its social posts are written,
`scripts/fact_check.py` lists every service, channel, price and date claim with
a source, checking our facts first and then the providers' own pages (web
search and fetch). The PR shows the list at the top, with ❌ wrong and
⚠️ unconfirmed lines first. It never blocks a merge. To check any post by hand:
`python scripts/fact_check.py _posts/<post>.md` (needs `ANTHROPIC_API_KEY`).
When a deal changes or a guide is re-checked, update its entry and `checked`
date in `_data/site_facts.yml`; it's part of the quarterly fact check.

**YouTube Shorts:** for topics with `video: true`, the draft PR also gets
`_video_scripts/<date>-<slug>.short.yml` (written by `scripts/generate_short.py`):
the scenes and voiceover of a 40–55 second vertical Short, and its YouTube
title, description and tags. Review it with the article; the claims list checks
its words too. When it reaches main (on merge, or after a later correction),
`.github/workflows/youtube-short.yml` renders the MP4 with
`scripts/video/render_short.py` (computer voice, word-by-word captions, the
channel's look and end card) and comments on the merged PR with a link to a zip
holding the MP4 and `<slug>.youtube.md` (paste-ready title, description, tags
and settings). Nothing is uploaded to YouTube. To re-render: **Actions → YouTube
Short → Run workflow** with the spec's path. To render locally: run
`bash scripts/video/fetch_assets.sh` once (about 350 MB of voice files), then
`python scripts/video/render_short.py <spec> --out video-out` (needs ffmpeg,
the Inter fonts, and `pip install onnxruntime numpy pillow pyyaml`). If the run
log or PR comment lists words that were spelled out letter by letter, add them
to `FIXED` in `scripts/video/tts.py`.

## Local preview

```bash
bundle install
bundle exec jekyll serve
```
Visit `http://localhost:4000`.

## 7. WhatsApp channel posts

The channel's promise is "price changes, new launches, and deals as they
happen". Full plan: the *Social & WhatsApp Content Strategy* doc.

- **Every post** is under 60 words, has one link and names its source. Legal
  services and licensed devices only.
- **Limit:** at most 3 posts a week, not counting the Thursday
  "Sport on TV this week" message.
- **Price change:** update `_data/prices.yml` first (`monthly`, `changed`,
  `checked`, `source`), then post, so the channel and `/streaming-prices/`
  agree. Template:
  `PRICE CHANGE: {Service} {Plan} / {old} -> {new} a month from {date} / {what to do} / onairireland.ie/streaming-prices/`
- **New launch:** `NEW: {Service} / what it is, price, start date / who it suits / link`
- **Deal:** `DEAL: {Offer} / price, what it replaces, ends {date} / who should skip it / link`.
  WhatsApp deal posts never use affiliate links. They always link to an
  on-site page that carries the affiliate links and the disclosure.
- **Log:** add each alert to `_data/whatsapp_posts.yml` so the monthly
  "Price check" recap can be written from it.
- **Every blog post** ends with `{% raw %}{% include whatsapp-cta.html %}{% endraw %}`
  (the daily draft script adds it automatically; add it by hand to any
  post written manually).
