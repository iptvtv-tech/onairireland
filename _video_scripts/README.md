# _video_scripts/

Auto-generated YouTube video scripts, one per blog post where `video: true` in `_data/topic_queue.yml`.

Each file is created by the [Daily Draft Post](.github/workflows/daily-draft-post.yml) workflow and committed in the same PR as the blog post draft. Edit the script before recording.

**Jekyll ignores this directory** (starts with `_`) so nothing here is published to the site.

File naming: `YYYY-MM-DD-post-slug.md` — matches the corresponding post in `_posts/`.

`YYYY-MM-DD-post-slug.short.yml` — the YouTube Short for the same post: scenes, voiceover and the
YouTube title, description and tags. The [YouTube Short](../.github/workflows/youtube-short.yml)
workflow renders the MP4 when one of these lands on main. Format: `scripts/video/short_spec.py`.
