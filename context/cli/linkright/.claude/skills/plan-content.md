---
name: plan-content
description: Produce a multi-week content calendar for LinkRight Pillar 4. Loads the user's voice profile, takes a theme + week count, calls the content planner to generate post/thread ideas, lets the user edit before persisting to MongoDB. Use when user says "plan my content", "give me a content calendar", "what should I post next month", or "build a content plan around [theme]".
---

# Plan Content — LinkRight skill

You are building a dated content calendar the user can execute against. Voice-matched ideas, not generic "LinkedIn post prompts". Nothing is persisted until the user approves.

## When to invoke

- User says "plan my content for the next N weeks"
- User gives a theme ("PM career", "AI tooling", "my launch") and asks for a calendar
- User has already run voice onboarding (VoiceProfile exists)

Do NOT invoke for single-post drafting — that's `draft-content`.

## How to execute

1. **Load voice profile**
   - Read the user's `VoiceProfile` (tone adjectives, sentence cadence, topics they own, off-limits topics).
   - If missing: bail and tell the user to run voice onboarding first.

2. **Collect plan inputs**
   - Theme / pillar (required)
   - Number of weeks (default 4)
   - Posts per week per platform (default: LI 3/wk, Twitter thread 1/wk)
   - Existing commitments (launches, events, dates to seed posts around)

3. **Call the content planner**
   Invoke `linkright.content.planner` with voice profile + inputs. It returns a list of planned items: `{date, platform, kind, working_title, hook_idea, angle, target_len}`.

4. **Render calendar for review**
   Print as a week-grouped markdown table. Mark items that overlap with `similar_past_items` from the user's history (originality risk).

5. **Interactive edit loop**
   - Ask user to approve / tweak any row (swap topic, move date, change platform).
   - Apply edits in-memory. Re-render the table.
   - Repeat until user says "ship it" / "save".

6. **Persist to MongoDB**
   - Upsert each item as a `ContentPlanItem` doc linked to the user + plan-run id.
   - Emit `plan.md` + `plan.json` to the run dir as a local backup.

## Hard constraints

- Never persist before user approves.
- Every item must be voice-matched — if the planner returns something off-voice, flag it and ask before keeping.
- Respect off-limits topics from the voice profile (hard skip, no warnings needed).
- Dates must be future-only and skip the user's configured off-days.
- Never exceed the user's cadence cap (posts/week) — offer to drop lowest-confidence items instead.

## Output

```
~/.linkright/content/plans/<run_id>/
├── plan.md         # human-readable calendar
├── plan.json       # machine-readable ContentPlanItem list
└── voice_used.json # snapshot of VoiceProfile at plan time (audit)
```

Finish with a one-line summary: "Planned N items across W weeks. Run `draft-content <item_id>` when you're ready to write."
