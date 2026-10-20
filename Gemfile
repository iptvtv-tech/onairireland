source "https://rubygems.org"

# Pinned so local builds match what GitHub Pages runs (older bundles break on Ruby 3.2+)
gem "github-pages", "~> 232", group: :jekyll_plugins

group :jekyll_plugins do
  gem "jekyll-paginate"
  gem "jekyll-sitemap"
  gem "jekyll-seo-tag"
  gem "jekyll-feed"
  gem "jekyll-include-cache"
end

gem "webrick", "~> 1.8" # needed for local `jekyll serve` on newer Ruby versions

# Timezone data for building on Windows (ignored on GitHub Pages)
gem "tzinfo-data", platforms: [:windows]
