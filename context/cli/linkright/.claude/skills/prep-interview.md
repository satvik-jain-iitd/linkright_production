---
name: prep-interview
description: Run LinkRight Pillar 3 interview prep for a scheduled interview. Use when the user says "prep me for <company>", "get ready for interview", or references an interview_id.
---

# prep-interview

Orchestrate a full interview-prep cycle using the LinkRight CLI.

## Steps

1. If no interview exists, create one:
   ```bash
   linkright interview schedule --company "<Co>" --role "<Role>" --stage loop [--date <ISO>]
   ```
   Capture the printed ObjectId as `$IID`.

2. Run prep (writes `~/.linkright/runs/<ts>/prep-packet.md` + scorecard):
   ```bash
   linkright interview prep $IID [--jd-file /path/to/jd.txt] -n 10
   ```

3. Walk the user through the packet:
   - Company research (remind them of the LLM-generated disclaimer)
   - Top 3 highest-confidence predicted questions
   - Matched STAR stories — suggest gaps if star_coverage < 60

4. Offer a mock session (MCP-driven) or a debrief capture after the real thing:
   ```bash
   linkright interview mock $IID
   linkright interview debrief $IID --notes "..."
   ```

## Notes
- Falls back to disk (`~/.linkright/runs/<ts>/`) if MongoDB is down.
- Oracle embed fallback → substring text search on `user_context.body`.
- All persisted docs carry `user_id="local"` and `schema_version=1`.
