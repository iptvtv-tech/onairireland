# Post image system

Every post gets its own header images, and no image is ever used twice. Real photos are the main
image; brand cards are the fallback.

## How a post gets its images

`scripts/generate_post.py` asks Claude for a scene (`IMAGE_SCENE`, from the scenes allowed for the
post's category), then calls `image_system.choose_hero()`:

1. **Photo from the approved shortlist.** `_data/photo_shortlist.yml` lists Pexels photos by id and
   scene. Only entries a person has marked `status: approved` are ever used. The requested scene is
   tried first; within it a photo without people is preferred if the last photo had people. If the
   scene has nothing left, another scene allowed for the category is used.
2. **Downloaded once, treated, self-hosted.** The chosen photo is fetched through the Pexels API (one
   photo, only when a post uses it: no bulk copying) and given the house treatment:
   - 2:1 crop (`focus:` on the shortlist entry moves the crop up or down)
   - calmer colour, a little more contrast and a 10% wash of the category colour
   - a 6px category-colour bar along the bottom of the teaser
   - a share image (og) with a dark left shade, category pill, title and logo
   The photographer is credited in `header.caption` ("Photo: Name on Pexels", linked), and the footer
   shows "Photos from Pexels" once any photo is in use.
3. **Otherwise a brand card** from `scripts/image_cards.py` (the site's own product icons, a unique
   composition fingerprint per post). No `PEXELS_API_KEY`, no approved photo for the scene, or a
   download error all fall back to a card.

Each post gets four files in `assets/images/posts/`: `<slug>-hero.webp` (1600x800),
`<slug>-hero-800.webp` (phones), `<slug>-teaser.webp` (600x400) and `<slug>-og.jpg` (1200x630, JPEG
for social apps). Front matter: `overlay_image`, `overlay_image_small`, `teaser`, `og_image`
(+ `caption` for photos). Every choice is recorded in `_data/image_ledger.yml`.

## Hero readability

`_includes/page__hero.html` overrides the theme's hero (theme commit 7c68402e) in two ways only:
posts without `header.overlay_filter` get `site.hero_overlay_filter` (a dark left-to-right
gradient in `_config.yml`) so titles read over any image, and `header.overlay_image_small` is
served to phones. If the theme pin is updated, compare this file with the theme's copy.

## Keeping the shortlist topped up

- **Propose Photos** workflow (1st of each month, or run it from Actions): searches Pexels for
  scenes running low, adds candidates as `pending`, and opens a PR with thumbnails. Change each to
  `approved` or `rejected` in that PR, then merge. Reject anything with a readable logo, brand, app
  on screen, watermark, flag or identifiable child.
- **Apply Photos** workflow: processes `_data/photo_assignments.yml` (photos for existing posts, or
  `target: static-pages` for the shared page header) and opens a PR. It runs whenever that file
  changes on main, at most 30 entries per run (`MAX_ITEMS`), so merging one batch's PR starts the
  next. A post that moves from a card to a photo has its card files and ledger entry removed; a post
  with no approved photo for its scene keeps its card and stays queued until the shortlist grows.
  Within a scene, photos whose description shares words with the post title are picked first;
  aerial, blank-TV and stadium photos are only used when a post asks for that scene.

## Checks

`scripts/check_posts.py` (every PR) fails if two posts share an image, a header file is missing or is
a different format from its extension, a social or logo image is used as a header, a file in
`assets/images/posts/` or `assets/images/pages/` is missing from the ledger, a photo has no Pexels
credit, a used photo is not approved in the shortlist, or a shortlist entry has an unknown status
or scene. Posts still on the old shared header images produce a warning.

## Licence notes (checked 16 Oct 2026)

Pexels licence: free to use and modify, credit optional. Pexels Terms allow downloading and copying
but ban bulk or systematic copying without permission, so photos are fetched one at a time when used.
The API guidelines ask for a link to Pexels and a photographer credit; both are on the site. If
Pexels or a photographer ever asks, delete the photo's files and swap the post to a card.

## Maintenance

- **Replace a post's image:** add it to `_data/photo_assignments.yml` with a `photo:` or `scene:`.
- **Add or change a product icon:** edit the SVG in `assets/images/products/`, then re-render the
  PNGs with `node scripts/card_kit/render_icons.js` (needs Playwright with Chromium). Add keywords in
  `ICON_KEYWORDS` in `image_cards.py`.
- **Retired images:** `_data/image_ledger.yml` -> `retired` lists the 39 old teaser-pool images
  removed and why.
- **Font:** Inter Bold (`fonts/Inter-Bold.otf`, SIL Open Font License, licence text alongside).
