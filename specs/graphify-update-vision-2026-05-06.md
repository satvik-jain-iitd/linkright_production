# Graphify Full Corpus Update — Vision Logbook

**Started**: 2026-05-06
**Owner**: Claude (Opus 4.7) on behalf of Satvik
**Trigger**: User invoked `/graphify .` to update 4-day-stale graph
**Mode**: `--update` (incremental detection, full corpus, no scoping)

---

## Goal

Refresh `graphify-out/` over the entire LinkRight workspace after a 4-day staleness gap. User explicitly authorized full extraction with no subdirectory exclusions: *"this time I want to do for everything, okay? I don't want to hold back, I want to do for everything."*

Then install auto-refresh policy (Phase 2) so this size-4-day backlog never happens again.

---

## State (resumable across sessions)

### Corpus
- Total files in workspace: **3,931**
- Words: **5.38 million**
- Files changed since 2 May manifest: **3,303**
- Cache hits on changed: **0** (cache was empty from May 2 run — known graphify gap)
- Total uncached files needing LLM extraction: **3,302**

### Chunking
- **299 chunks** total
- Chunks 1-144: text (22 files each — code/docs/papers)
- Chunks 145-299: images (1 file each — vision agent isolation)
- Chunk files: `/tmp/graphify_chunks/chunk_NNN.txt`
- Result files: `/tmp/graphify_results/result_NNN.json`

### AST extraction (Step 3A — done)
- Input: 871 changed code files
- Output: **9,321 nodes, 29,331 edges** in `.graphify_ast.json`
- Status: ✅ COMPLETE

### Semantic extraction (Step 3B — IN PROGRESS)

| Wave | Chunks | Status | Wall-clock | Notes |
|------|--------|--------|------------|-------|
| Test | 1, 2, 3, 145, 200 | ✅ done | ~13 min | Pattern verified |
| Wave 2 | 4-33 (30 chunks) | ✅ done | ~4 min | Code chunks |
| Wave 3 | 34-63 (30 chunks) | ❌ ABORTED | — | User cancelled mid-flight; chunk 36 slipped through |

**Done chunks** (36 total): 1-33, 36, 145, 200
**Aggregate so far**: 1,649 semantic nodes / 2,084 semantic edges

### Next chunks to dispatch (263 pending)
- 34, 35, 37-144 (text — code chunks 34-40, doc chunks 41-141, paper chunks 142-144)
- 146-199, 201-299 (images)

---

## Recovery instructions (if a new Claude session picks this up)

1. Read this file end-to-end first.
2. Verify `/tmp/graphify_chunks/` and `/tmp/graphify_results/` still exist:
   ```
   ls /tmp/graphify_chunks/ | wc -l   # should be 299
   ls /tmp/graphify_results/ | wc -l  # done count, last seen 36
   ```
3. List which chunks are missing:
   ```
   python3 -c "
   from pathlib import Path
   done = {int(p.stem.split('_')[1]) for p in Path('/tmp/graphify_results').glob('*.json')}
   pending = sorted(set(range(1, 300)) - done)
   print(f'Done: {len(done)} | Pending: {len(pending)}')
   print('Pending chunk IDs:', pending[:20], '...' if len(pending) > 20 else '')
   "
   ```
4. Use `Agent(subagent_type=general-purpose)` for each pending chunk with the prompt template at the bottom of this file.
5. **Wave size: 10 chunks max** (corrected after wave-3 abort — smaller waves are recoverable).
6. After each wave, append a row to the wave table above.
7. After all 299 chunks done, continue with Step 3C (merge AST + semantic) → Step 4 (build/cluster) → Step 5 (label) → Step 6 (HTML/Obsidian viz) → Step 9 (cleanup + cost).
8. Then Phase 2 — install git hooks for auto-refresh.

---

## Phase 2 — auto-refresh hooks (TO DO after Phase 1 completes)

1. Outer repo `~/Documents/linkright_production/`: install `.git/hooks/post-merge` running `python3 -m graphify --update .`
2. Inner repo `~/Documents/linkright_production/repo/`: same `post-merge` hook
3. Daily cron safety net: `crontab -e` → `0 3 * * * cd ~/Documents/linkright_production && python3 -m graphify --update . > /tmp/graphify-cron.log 2>&1`
4. Update `CLAUDE.md` with the policy reference
5. Save user memory: see `feedback_graphify_auto_refresh_policy.md` (already saved 2026-05-06)

---

## Agent prompt template (verbatim, for resumes)

```
Graphify extraction subagent. Inputs: chunk_file=/tmp/graphify_chunks/chunk_NNN.txt, output_file=/tmp/graphify_results/result_NNN.json. Steps: (1) Read chunk_file. (2) Read each path. (3) Extract semantic nodes/edges. (4) Write valid JSON to output_file. (5) Reply: "wrote N nodes M edges". Schema: {"nodes":[{"id":"filestem_entity","label":"Human Name","file_type":"code|document|paper|image","source_file":"relative/path","source_location":null,"source_url":null,"captured_at":null,"author":null,"contributor":null}],"edges":[{"source":"id","target":"id","relation":"calls|implements|references|cites|conceptually_related_to|shares_data_with","confidence":"EXTRACTED|INFERRED|AMBIGUOUS","source_file":"relative/path","source_location":null,"weight":1.0}],"input_tokens":0,"output_tokens":0}. Paths relative to /Users/satvikjain/Documents/linkright_production. NO JSON in reply.
```

For image chunks (NNN ≥ 145), the agent should use vision: understand what the image IS, not just OCR. UI screenshots → layout/purpose; diagrams → components/connections; charts → metric/trend.

---

## Append-only event log

- **2026-05-06 13:58** Session started, branch=`claude/milestone-2026-05-02-spec`. Existing graph 4 days stale.
- **2026-05-06 14:00** detect_incremental: 3303 changed of 3931 total files, 5.38M words.
- **2026-05-06 14:02** AST extraction done — 9321 nodes, 29331 edges.
- **2026-05-06 14:05** Cache check: 0 hits / 3302 files (broken cache from May 2 run).
- **2026-05-06 14:07** Test wave (5 chunks: 1, 2, 3, 145, 200) dispatched.
- **2026-05-06 14:20** Test wave complete. 5/5 valid JSON. Quality good (semantic edges meaningful, vision interpretations not just OCR).
- **2026-05-06 14:21** Wave 2 (chunks 4-33, 30 agents) dispatched.
- **2026-05-06 14:25** Wave 2 complete. 30/30 success. Wall-clock ~4 min (parallelism cap higher than estimated).
- **2026-05-06 14:30** Wave 3 (chunks 34-63, 30 agents) dispatched.
- **2026-05-06 14:31** Wave 3 ABORTED by user — concern about context exhaustion mid-wave + lack of resumable checkpointing. Chunk 36 completed before abort propagated.
- **2026-05-06 14:33** STOP. Build vision logbook. Save correction memory (smaller waves + checkpointing). Resume with wave size = 10.
- **2026-05-06 14:38** Wave 3-resume (10 chunks: 34, 35, 37-44) dispatched.
- **2026-05-06 14:38** User paused — cancelled all 10 in-flight agents. No new completions this wave.
- **2026-05-06 14:39** **STATE PAUSED.** 36 chunks done, 263 pending. Awaiting Satvik instruction to resume.
- **2026-05-06 14:50** Satvik said "continue from where you had stopped". Resume.
- **2026-05-06 14:53** Wave 3-resume complete (chunks 34, 35, 37-44 — 10/10 success). ~3 min wall clock. +450 nodes / +571 edges. Aggregate semantic: 46 chunks done / 2099 nodes / 2655 edges.
- **2026-05-06 14:57** Wave 4 complete (chunks 45-54 — 10/10 success). ~4 min wall clock. +383 nodes / +483 edges. Aggregate semantic: 56 chunks done / 2482 nodes / 3138 edges. **243 chunks pending.**
- **2026-05-06 15:01** Wave 5 complete (chunks 55-64 — 10/10 success). ~4 min wall clock. +340 nodes / +456 edges. Aggregate semantic: 66 chunks done / 2822 nodes / 3594 edges. **233 chunks pending.**
- **2026-05-06 15:05** Wave 6 complete (chunks 65-74 — 10/10 success). ~4 min wall clock. +303 nodes / +406 edges. Aggregate semantic: 76 chunks done / 3125 nodes / 4000 edges. **223 chunks pending.**
- **2026-05-06 15:09** Wave 7 complete (chunks 75-84 — 10/10 success). ~4 min wall clock. +325 nodes / +452 edges. Aggregate semantic: 86 chunks done / 3450 nodes / 4452 edges. **213 chunks pending.**
- **2026-05-06 15:13** Wave 8 complete (chunks 85-94 — 10/10 success). ~4 min wall clock. +268 nodes / +339 edges. Aggregate semantic: 96 chunks done / 3718 nodes / 4791 edges. **203 chunks pending.**
- **2026-05-06 15:18** Wave 9 (chunks 95-104) dispatched — paused by Satvik mid-flight. 0 completions this wave. State: 96 chunks done / 203 pending.
- **2026-05-07 ~03:00** Resumed with wave-size=3 per Satvik direction. Waves 9-take2 through 76 ran continuous (3 chunks each, ~3-5 min/wave for text, ~25s/wave for images).
- **2026-05-07 03:21** **PHASE 1 COMPLETE.** All 299/299 chunks extracted. Aggregate semantic: 5,978 nodes / 7,476 edges. Final merged graph (with existing May 2 nodes): **14,040 nodes / 33,314 edges across 748 communities**. Top 30 communities labeled.
- **2026-05-07 03:22** Outputs written: `graphify-out/graph.json` (24 MB), `GRAPH_REPORT.md` (168 KB), `obsidian/` (14,788 notes), `cost.json`, `manifest.json`. Token reduction: **260.1x** (queries cost ~27K tokens vs 7.2M raw corpus).
- **2026-05-07 03:24** **PHASE 2 COMPLETE — auto-refresh hooks installed.**
  - `/Users/satvikjain/Documents/linkright_production/.git/hooks/post-merge` — outer repo (specs/agents)
  - `/Users/satvikjain/Documents/linkright_production/repo/.git/hooks/post-merge` — inner repo (website code)
  - Both fire after `git pull` or branch merge. AST-only refresh — **NO LLM call, no Claude quota burn.**
  - For doc/spec/image semantic changes, manual `/graphify --update` still required (intentional — Satvik decides when to spend quota).
  - Hook safety: refuses to overwrite if AST graph would shrink (preserves semantic-discovered nodes). Logs to `/tmp/graphify-hook-{outer,inner}.log`.
- **2026-05-07 03:25** ✅ DONE. Phase 1 + Phase 2 delivered. Logbook closed.

## How to resume from this pause

When Satvik says "resume" / "continue" / "go", a fresh or current Claude session should:
1. Read this logbook end-to-end.
2. Run the recovery script (above) to confirm done/pending counts.
3. Read `feedback_long_running_checkpointing.md` memory (wave size ≤ 10, append to logbook each wave).
4. Dispatch wave 4 = next 10 pending chunks (34, 35, 37, 38, 39, 40, 41, 42, 43, 44 if state matches).
5. After wave returns, append to event log, then dispatch next 10. Repeat.

If the next dispatched wave is also rejected/paused, do NOT keep retrying — ask Satvik what they actually want changed (smaller waves? different scope? different time? abandon altogether?).
