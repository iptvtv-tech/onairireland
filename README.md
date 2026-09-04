# On Air Ireland

Jekyll blog (Minimal Mistakes theme) about **legal** streaming services,
devices, and installation guides for Ireland. Deployed via GitHub Pages
to `iptvirelandtv.com`.

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

## 3. Point iptvirelandtv.com at GitHub Pages

At your DNS registrar for `iptvirelandtv.com`:

**Apex domain (`iptvirelandtv.com`)** — four A records:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

**Or `www.iptvirelandtv.com`** — a CNAME record pointing to `YOURUSERNAME.github.io`

The `CNAME` file in this repo is already set to `iptvirelandtv.com` — GitHub
Pages reads it automatically, you don't need to re-enter the domain unless
it gets reset.

Back in **Settings → Pages**, tick **Enforce HTTPS** once DNS has propagated
(can take minutes to hours).

## 4. SEO setup already included

- `jekyll-seo-tag` — auto-generates title tags, meta description, Open
  Graph tags, Twitter Card tags, and JSON-LD structured data on every
  page/post from the front matter
- `jekyll-sitemap` — auto-generates `/sitemap.xml`
- `robots.txt` — points crawlers to the sitemap
- Per-post `description`, `excerpt`, `categories`, `tags`, and `seo.type`
  front matter fields for structured data

**Still to do manually:**
- Add a real logo at `assets/images/logo.png`
- Add a real default social share image at `assets/images/social-default.png` (1200×630px)
- Set `google_site_verification` in `_config.yml` once you register the
  site with Google Search Console
- Update `twitter.username` and `social.links` in `_config.yml`
- Submit `https://iptvirelandtv.com/sitemap.xml` to Google Search Console

## 5. Affiliate links

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

## 6. Writing posts manually

Add a file to `_posts/` named `YYYY-MM-DD-title.md`, following the front
matter pattern in the existing sample posts. Push to `main` and it's live
in a minute or two.

## 7. Daily auto-draft posts (PR-based, not auto-publish)

`.github/workflows/daily-draft-post.yml` runs daily, pulls the next topic
from `_data/topic_queue.yml`, asks Claude to draft a post, and opens a
**Pull Request** — it never publishes directly. You review the draft for
accuracy (prices, app steps, current availability), then merge to publish.

**Setup required:**
1. Get an Anthropic API key from [console.anthropic.com](https://console.anthropic.com)
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `ANTHROPIC_API_KEY`
   - Value: your key
3. Add topics anytime by appending to `_data/topic_queue.yml`
4. To run it on demand instead of waiting for the daily schedule: **Actions tab → Daily Draft Post → Run workflow**

## Local preview

```bash
bundle install
bundle exec jekyll serve
```
Visit `http://localhost:4000`.
