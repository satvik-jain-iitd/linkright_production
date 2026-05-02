---
name: draft-content
description: Draft voice-matched social content (LinkedIn post, Twitter thread, or blog outline) using LinkRight's Pillar 4. Use when the user says "draft a post", "write a LinkedIn post", "tweet thread about X", or "content about Y".
---

# draft-content

Generate a voice-matched draft via the LinkRight Pillar 4 pipeline.

## When to use
- User asks for a LinkedIn post, Twitter/X thread, or blog outline
- User has `~/.linkright/profile/voice-samples.md` set up (otherwise a neutral voice is used)

## How it works
1. `extract_voice_profile()` reads voice samples → stats + tone adjectives + avoid_list
2. `draft_content()` calls `chat_with_fallback` with a voice-injected system prompt
3. Optional Oracle (gemma3:1b) tone-tightening pass (skipped gracefully if unavailable)
4. Draft saved to `~/.linkright/runs/<timestamp>/drafts/<kind>-<slug>.md` and persisted in MongoDB `content_items`

## CLI
```bash
# One-off draft
linkright content draft --topic "Why solo PMs should learn to ship" --kind linkedin_post

# Twitter thread
linkright content draft --topic "AI tools for PMs" --kind twitter_thread

# Plan a 4-week calendar around a theme
linkright content plan --weeks 4 --theme "AI career pivots"

# Schedule a persisted draft
linkright content schedule <content_id> --platform linkedin --at 2026-05-01T09:00:00Z
```

## Kinds
- `linkedin_post` — ~1200 chars, hook + 3-4 paragraph body + CTA
- `twitter_thread` — 5-8 tweets, each ≤ 280 chars
- `blog_outline` — H1 + thesis + 4-6 H2 sections with bullets

## Failure modes (handled)
- MongoDB down → writes to `~/.linkright/runs/<ts>/` as markdown/JSON
- Oracle unreachable → skips the normalization pass
- `voice-samples.md` missing → neutral default profile
