# Content harness — self-correcting compose loop

## Added

- **`linkright content compose`**: grounds a topic in career memory, drafts, runs deterministic hard gates, scores on the rubric, and self-corrects until the draft clears the gates and meets the score threshold. Flags: `--topic`, `--kind`, `--length`, `--max-iters`, `--threshold`, `--no-ground`, `--json`.
- **`content/gates.py`**: config-driven deterministic gates (banned words, mobile-syntax punctuation, hook signature, forbidden openers, paragraph length). Generic defaults; an instance can enforce house style via `~/.linkright/content_style.json`. The voice profile `avoid_list` is always banned.
- **`content/grounding.py`**: topic-relevant fact and signal retrieval over the v2 profile store, hybrid cosine plus keyword fallback, drops stale facts, caveats thin-confidence facts, keeps ids for provenance.
- **`content/loop.py`**: the orchestration loop tying drafter, gates, and scorecard together with an injectable revise step. Draft and LLM functions are injectable for offline testing.
- **`tests/test_content_harness.py`**: 5 offline tests covering gate blocking, clean-draft pass, voice avoid_list enforcement, loop revision to gate-clean, and grounding stale-drop plus thin-fact caveat.

## Changed

- **`content/drafter.py`**: `draft_content` gained an optional `evidence` keyword. When present it appends the career-grounding block to the system prompt. Omitting it preserves the original behaviour exactly.
