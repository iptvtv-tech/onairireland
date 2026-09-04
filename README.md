# On Air Ireland

Jekyll blog (Minimal Mistakes theme) about **legal** streaming services,
devices, and installation guides for Ireland. Deployed via GitHub Pages
to `onairireland.com`.

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

## 3. Point onairireland.com at GitHub Pages

At your DNS registrar for `onairireland.com`:

**Apex domain (`onairireland.com`)** — four A records:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

**Or `www.onairireland.com`** — a CNAME record pointing to `YOURUSERNAME.github.io`

The `CNAME` file in this repo is already set to `onairireland.com` — GitHub
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
- Submit `https://onairireland.com/sitemap.xml` to Google Search Console

## 5. Writing posts manually

Add a file to `_posts/` named `YYYY-MM-DD-title.md`, following the front
matter pattern in the existing sample posts. Push to `main` and it's live
in a minute or two.

## 6. Daily auto-draft posts (PR-based, not auto-publish)

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
