# LinkRight — QA Reference

> Authorized document. Last updated: 2026-05-08. Merges: KNOWN_BUGS.md, manual-qa-plan-v1-2026-05-03.md, static-qa-analysis-next-release-2026-05-05.md, fix-plan-v0.4.0-2026-05-05.md.

---

## Part 1 — Historical Bugs (All Fixed)

All bugs below are fixed as of v3.0.0 / v0.4.0. Recorded here for root-cause context.

### Bug 1: assemble_html Double-Nested Contact Links
- **Symptom:** Contact links rendered as `<a><a>...</a></a>` (double-wrapped)
- **Root cause:** Pre-linked `<a href="mailto:...">` tags in header contacts were re-wrapped by assemble_html's automatic link injection logic
- **Fix (v3.0.0):** Added check in `_replace_header_content` — if contact value already contains `<a `, skip wrapping
- **Status:** Fixed

### Bug 2: assemble_html Missing Section Wrappers
- **Symptom:** Assembled HTML sections lost their `<div class="section">` wrapper divs, breaking spacing
- **Root cause:** Section injection logic stripped outer container divs during template injection
- **Fix (v3.0.0):** `_replace_section_content` now wraps injected HTML in `<div class="section">` automatically
- **Status:** Fixed

### Bug 3: 14px Page Overflow After 6-Section Assembly
- **Symptom:** Resume overflowed by ~14px (~3.7mm) after assembling all 6 sections
- **Root cause:** Template defaults (`--section-spacing: 4mm`, `--entry-spacing: 3.5mm`) too generous for 6 sections with 15+ bullets
- **Fix (v3.0.0):** Reduced template defaults: `--section-spacing: 4mm → 3.5mm` and `--entry-spacing: 3.5mm → 3mm`
- **Status:** Fixed

### Bug 4: Bullet Overflow 110.5% on First Draft
- **Symptom:** Bullet text measured at 110.5% width on first draft
- **Root cause:** Initial text included too many details ("Google Workspace, Slack, and Salesforce implementation across 50+ volunteers...")
- **Fix:** 2 rounds of measure-rewrite: remove verbose detail, shorten phrasing → 99.3%
- **Status:** Fixed

### Bug 5: Edge-to-Edge Line Below 95% Floor
- **Symptom:** Edge-to-edge achievement line measured at 94.4%, below the 95% floor
- **Root cause:** Text slightly too short for edge-to-edge justified rendering
- **Fix:** Expanded phrase ("CBSE School Rank 1" → "CBSE School Rank 1") → 97.8%
- **Status:** Fixed

### Bug 6: Preview Server Serving Wrong Directory
- **Symptom:** `preview_start` served files from wrong directory
- **Root cause:** Claude Preview MCP tool reuses existing server instances, ignores `--directory` flag when server with same name was previously started
- **Fix:** Injected HTML directly via `preview_eval` with `document.documentElement.innerHTML`
- **Status:** Workaround (preview tool limitation)

### Bug 7: All Bullets Overflow on First Draft (Systemic)
- **Symptom:** Every bullet in every resume measures 105–130% width on first draft
- **Root cause:** LLM consistently writes bullets longer than the 101.4 character-unit budget; XYZ format + natural language verbosity produces ~120–140 CU text before measurement
- **Fix (v3.0.0):** Added character budget hints to Phase 4.2: "Bullet visible text target: 88–96 characters. Count before measuring, trim proactively." Combined with Bug 9 fix.
- **Status:** Mitigated (prompt + regex fix)

### Bug 8: CSS Inconsistencies Between Outputs
- **Symptom:** Different resumes had different `text-align` values on `.li-content` and `.edge-to-edge-line`
- **Root cause:** Template defaults were `text-align: left` while application outputs were manually set to `text-align: justify`
- **Fix (v3.0.0):** Standardized template CSS: both classes now use `text-align: justify; text-align-last: justify;` by default
- **Status:** Fixed

### Bug 9: html_parser Bold Regex Captures Only 1 Character
- **Symptom:** `<b>revenue growth of 40%</b>` parsed as bold segment containing only "r" (1 char)
- **Root cause:** Regex pattern used `.?` (0–1 chars) instead of `.+?` (1+ chars, non-greedy)
- **Fix (v3.0.0):** Changed regex from `.?` to `.+?` in `sync/utils/html_parser.py`
- **Impact:** Silent accuracy bug — bold text widths were under-counted, contributing to Bug 7's systemic overflow
- **Status:** Fixed

---

## Part 2 — Manual QA Plan (v1 Ship Gate)

> Date: 2026-05-03 (updated 2026-05-05)
> Structure: Section 1 = new user flow (must-pass). Admin sections = pre-ship verification by Satvik only.

---

### Section 1 — User Onboarding Flow (~10 min)

The exact journey a new job seeker takes after finding LinkRight on GitHub. If this breaks, nothing else matters.

#### 1.1 Install
```bash
pip install 'linkright[full]'
linkright --version
# Expect: linkright, version 0.4.0
```

#### 1.2 Setup wizard (one-time)
```bash
linkright setup
# Expect: interactive wizard — picks LLM provider, embedder, PDF renderer
# At minimum: enter one free Groq API key when prompted
# Should complete in ~1 min
```

#### 1.3 Health check
```bash
linkright doctor
# Expect: green ticks for config, API keys, deps, embedder, MongoDB
# Any RED item = stop and fix before continuing
```

#### 1.4 Profile creation
```bash
linkright profile create -r /path/to/your/resume.pdf
# Expect: ~30-60s, "Profile saved with N nuggets"
```

#### 1.5 Tailor a resume
```bash
linkright tailor -j /path/to/jd.md
# Expect: 16-step pipeline, ~2 min
# Final: "Score: XX.X (Grade: X)" + PDF path printed
# Open the PDF — verify it looks right
```

#### 1.6 Cover letter
```bash
linkright cl -j /path/to/jd.md
# Expect: ~250-word cover letter, ~90 sec
```

#### 1.7 Job search
```bash
linkright auth login
# Opens browser → OAuth → "Logged in as ..."

linkright jobs find
# Expect: ranked job table with scores
```

#### 1.8 Watch setup (passive job capture)
```bash
linkright watch setup
# Expect: Chrome alias written to ~/.zshrc + next steps shown
```

#### 1.9 Story Bank (interview prep)
```bash
linkright stories add
# Interactive prompts: Title, Situation, Task, Action, Result, Tags
# Expect: "✓ Story saved"

linkright stories list
# Expect: table with your story
```

**User Onboarding PASS = all 9 steps above work without error. This is the v1 ship bar.**

---

### Admin QA — Pre-ship Verification (Satvik only)

#### QA-0 — Pre-flight (~5 min)

```bash
# Editable install from source
/Library/Frameworks/Python.framework/Versions/3.13/bin/pip3 install -e \
  ~/Documents/linkright-wt/release-v04/context/cli/linkright/
linkright --version
# Expect: linkright, version 0.4.0

# Config file presence
ls -la ~/.linkright/
# Expect: .env (mode 600), config.yaml, profile/, runs/, cache/
```

#### QA-1 — Smoke tests (~5 min)

```bash
linkright --help
# Expect: command list including: auth, cl, content, cover-letter, critique,
#   doctor, fill, improve, init, interview, jobs, plan, profile, resume, score,
#   setup, stories, tailor, tldr, watch

linkright tldr
# Expect: one-page cheat sheet

linkright watch status
# Expect 4 lines: capture key (✓), endpoint (✓), chrome CDP (✗ if Chrome not started), worker health (✓)
```

#### QA-2 — Pillar 1: Resume + Cover Letter (~25 min)

```bash
# Full pipeline
linkright resume tailor \
  -j ~/Documents/linkright_production/context/data/assets/resume-applications/highlevel_pm-workflows/jd.md \
  --run-id qa_test_$(date +%s)
# Expect: 16-step pipeline, ~2 min wall time
# Final: "Score: XX.X (Grade: X)" + PDF path
# Open PDF: header not clipped, bullets have metric bolds only, 1-page output

# Score
linkright score -r ~/.linkright/runs/qa_test_*/15_final_resume.pdf -j .../jd.md
# Expect: 16-dimension scorecard, total ≥ 90

# Critique
linkright critique --run-id qa_test_*
# Expect: 5 issues + 3 fix options each

# Fill metrics
linkright fill --run-id qa_test_*
# Expect: prompts for bullets with X% / $YM placeholders; no fabricated numbers

# Cover letter
linkright cl -j .../jd.md
# Expect: ~250-word cover letter PDF, 90 sec

# Brand-color resume (interactive)
linkright resume brand --run-id qa_test_*
# Prompts: Primary hex (#635BFF), Secondary (#00D4FF), Accent (skip)
# Expect: branded PDF — ONLY metric bolds + section dividers colored; all other text black

# Brand-color (power-user flags)
linkright resume brand --run-id qa_test_* --primary "#635BFF" --secondary "#00D4FF" --accent "#FF6B6B" --yes

# Hex validation
linkright resume brand --run-id qa_test_* --primary "not-a-hex" --yes
# Expect: Error — invalid hex

# B&W default unchanged
# Open original PDF: must be pure B&W. Brand command must NOT modify original.
```

#### QA-3 — Pillar 2: Job Search (~15 min)

```bash
# Auth
linkright auth login
linkright auth status
# Expect: "Logged in as <email>"

# Captures-only (no auth)
linkright auth logout
linkright jobs find --top 5
# Expect: "⚠ not logged in — showing captures only..."
linkright auth login

# Both sources
linkright jobs find --top 10
# Expect: table with Rank / Grade / Title / Company / Score / Source
# Bottom: "X scored + Y from captures"

# Filters
linkright jobs find --location bangalore --top 5
linkright jobs find --grade A --top 5
linkright jobs find --top 5 --json | jq '.[].job_discoveries.title'

# Show / apply / status
linkright jobs show <id-prefix>
linkright jobs apply <id-prefix>          # full tailor pipeline runs
linkright jobs status <id-prefix> interviewing
```

#### QA-4 — Watch / Passive Capture (~20 min)

```bash
# Setup
linkright watch setup
source ~/.zshrc
which chrome

# Chrome CDP
chrome    # quit Chrome first with cmd-Q, then relaunch via alias
curl -sS http://localhost:9222/json/version
# Expect: JSON with webSocketDebuggerUrl

# All-green status
linkright watch status
# Expect: 4 ✓ lines

# Foreground listener
linkright watch -v
# Browse a Naukri job page in Chrome
# Expect log: "✓ <title> — 201 dedup=new"
# ctrl-C → exit 0

# Capture list
linkright watch list --since "5 minutes" --top 5

# Background daemon
linkright watch install-service
launchctl list | grep linkright     # Expect: "0  -  in.linkright.watch"
tail -f ~/.linkright/watch.log      # ctrl-C to stop
linkright watch uninstall-service
```

**QA-4.7 — Multi-portal (7 portals, PR #57):**

Browse one job page per portal; confirm each appears in `linkright watch list`:

| Portal | URL pattern | Expected source_type |
|---|---|---|
| Naukri | `naukri.com/job-listings-*` | capture_naukri |
| LinkedIn | `linkedin.com/jobs/view/<id>` | capture_linkedin |
| Indeed | `indeed.com/viewjob?jk=<key>` | capture_indeed |
| Greenhouse | `boards.greenhouse.io/<tenant>/jobs/<id>` | capture_greenhouse |
| Lever | `jobs.lever.co/<tenant>/<uuid>` | capture_lever |
| Ashby | `jobs.ashbyhq.com/<tenant>/<uuid>` | capture_ashby |
| Wellfound | `wellfound.com/jobs/<id>-<slug>` | capture_wellfound |

```bash
linkright watch list --json | jq -r '.[].source_type' | sort -u
# Expect: all 7 capture_* types listed
```

**QA-4.8 — Privacy regression:**
```bash
# Browse linkedin.com/messaging/ or naukri.com/notifications in Chrome
linkright watch list --since "1 minute" --json | jq '.[].job_url'
# Expect: NO private-path URLs
```

#### QA-5 — Pillar 3: Story Bank (~8 min)

```bash
# Practice cards
linkright practice
# Expect: STAR-format prep cards from career nuggets

# CRUD
linkright stories list                         # empty state: "No stories yet"
linkright stories add                          # fill 6 prompts → "✓ Story saved"
linkright stories add --from-nugget "AML"      # pre-fills result from nugget
linkright stories list                         # populated table
linkright stories search "AML"                 # matching stories printed
linkright stories edit "My Test"               # change one field → "✓ Updated 1 fields"
linkright stories delete "My Test"             # type n → "Cancelled."
linkright stories delete "My Test" --yes       # "✓ Deleted"

# Interview prep bridge
linkright interview prep
# Expect: prep cards surface Story Bank entries (PR #62)

# Duplicate-title guard
linkright stories add --yes --title "Dup Test" --action "x" --result "y"
linkright stories add --yes --title "Dup Test" --action "diff" --result "diff"
# Expect: ClickException — title already exists
linkright stories delete "Dup Test" --yes

# Whitespace rejection
linkright stories add --yes --title "   " --action "A" --result "R"
# Expect: ClickException — title + action + result required and non-empty
```

#### QA-6 — Pillar 4: Content (~3 min)

```bash
linkright content plan
linkright content draft
# Expect: commands run without error, output is a reasonable draft
```

#### QA-7 — Regression (~5 min)

```bash
# Dedup: apply a job via QA-3.3, then browse same URL in Chrome
# linkright jobs find must NOT show it twice

# watch list filters
linkright watch list --since "1 day"
linkright watch list --source capture_naukri
linkright watch list --since "1 day; DROP TABLE x"
# Last: expect "✗ invalid --since value..." (SQL injection guard)
```

#### QA-8 — Known Limitations (skip-verify)

| Limitation | Reason | Fix |
|---|---|---|
| LinkedIn SPA URLs may miss | pushState pattern not empirically validated | Phase 2 |
| Mobile browsing not captured | No CLI on iOS/Android | v2 |
| Render cold start 30–60s | Free plan idle | Render paid eventually |
| ats_provider=NULL for Indian unicorns | Tier3 iframe pattern mismatch | Phase 2 |
| Story Bank tailor bridge | Deferred to v0.5 per scope lock | Next sprint |
| Mock Interview / Negotiation | v2 deferred | v2 |

#### Ship Readiness Checklist

- [ ] Section 1 (User Onboarding) — full happy path works
- [ ] QA-2 Pillar 1 — resume + CL + brand all pass
- [ ] QA-3 Pillar 2 — jobs find dual-read + apply + status pass
- [ ] QA-4 Sprint D — watch listener + daemon + 7 portals + privacy pass
- [ ] QA-5 Pillar 3 — Story Bank CRUD + interview bridge pass
- [ ] QA-6 Pillar 4 — content commands run
- [ ] QA-7 Regression — dedup + SQL injection guard pass
- [ ] Infra checks pass (below)

#### Admin — Infrastructure Checks (~15 min)

```bash
# Backend reachability
curl -sS -m 30 https://sync-resume-engine.onrender.com/health
# Expect: {"status":"ok","service":"linkright-sync-worker", ...}

# Oracle PG counts
set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
python3 -c "
import asyncio, asyncpg, os
async def main():
    pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
    async with pool.acquire() as conn:
        c = await conn.fetchval('SELECT COUNT(*) FROM companies')
        j = await conn.fetchval('SELECT COUNT(*) FROM job_discoveries')
        print(f'companies={c} | job_discoveries={j}')
    await pool.close()
asyncio.run(main())
"

# Privacy filter test
curl -sS -X POST https://sync-resume-engine.onrender.com/api/captures \
  -H "Content-Type: application/json" \
  -H "X-LinkRight-Capture-Key: $(grep '^LINKRIGHT_CAPTURE_KEY=' ~/.linkright/.env | cut -d= -f2-)" \
  -d '{"source":"naukri","job_url":"https://www.naukri.com/messages/inbox/123","title":"x","company_name":"x","captured_at":"2026-05-03T12:00:00Z"}' \
  -w "\nHTTP %{http_code}\n"
# Expect: HTTP 403 + "blocked by privacy filter..."

# Slug discovery
linkright admin slug-discovery single Anthropic
linkright admin slug-discovery stats
linkright admin slug-discovery validate-all --max 3

# Companies stats
linkright admin companies stats
```

---

## Part 3 — Static QA Analysis (v0.4.0 Pre-ship Gate)

> Branch SHA: `ef0f20a` (PR #68 merged). Date: 2026-05-05.
> Scope: Static path-tree analysis. No code execution. 65 commands across 11 CLI modules (~4205 LOC).
> Calibration: v0.4.0 NOT on PyPI at analysis time. Latest = 0.3.0. v0.4.0 IS the next release.

### Executive Summary

**Ship verdict**: 🟡 **GO with caveats** — v0.4.0 shippable, BUT:
1. **Wizard upgrade migration** (B2-1): existing 0.3.0 users silently keep agent-mode config after upgrade.
2. **Backend deployment readiness** (B4-1, B4-2): `/api/discoveries` POST not deployed; Layer 4 validator cron not deployed.

**Bucket 1 (data corruption):** ✅ Zero findings. Truth Engine guards solid; cascade discipline enforced.

### Command Inventory (65 commands)

**Pillar 1: Resume + Profile (20 commands)**

| # | Command | File:line | Status |
|---|---------|-----------|--------|
| 1 | `resume tailor` | resume/cli.py:40 | shipped 0.3.0, changed 0.4.0+PR#68 |
| 2 | `resume score` | resume/cli.py:185 | stub |
| 3 | `resume batch` | resume/cli.py:194 | stub |
| 4 | `resume iterate` | resume/cli.py:205 | shipped 0.3.0 |
| 5 | `resume improve` | resume/cli.py:219 | new 0.4.0 |
| 6 | `resume fill-metrics` | resume/cli.py:247 | new 0.4.0 |
| 7 | `resume practice` | resume/cli.py:282 | new 0.4.0 |
| 8 | `resume strategy-review` | resume/cli.py:313 | new 0.4.0 |
| 9 | `resume critique` | resume/cli.py:342 | new 0.4.0 |
| 10 | `resume hypothesis-test` | resume/cli.py:375 | new 0.4.0 |
| 11 | `resume verify` | resume/cli.py:159 | new 0.4.0 |
| 12 | `profile create` | profile/cli.py:48 | changed 0.4.0 |
| 13 | `profile show` | profile/cli.py:126 | shipped 0.3.0 |
| 14 | `profile status` | profile/cli.py:139 | shipped 0.3.0 |
| 15 | `profile edit-contact` | profile/cli.py:166 | new 0.4.0 |
| 16 | `profile delete-nugget` | profile/cli.py:185 | new 0.4.0 |
| 17 | `profile enrich` | profile/cli.py:197 | new 0.4.0 |
| 18 | `profile refresh` | profile/cli.py:215 | new 0.4.0 |
| 19 | `profile rebuild` | profile/cli.py:234 | new 0.4.0 |
| 20 | `profile delete` | profile/cli.py:259 | new 0.4.0 |

**Pillar 2: Jobsearch + Watch + Auth + Admin (23 commands)** — `jobs find/show/apply/status/import/evaluate/recommend/find-slug`, `watch run/setup/install-service/uninstall-service/list/status`, `auth login/status/logout`, `admin companies import/stats`, `admin slug-discovery single/batch/validate-all/stats`

**Pillar 3+4 + Ops + Legacy (22 commands)** — `stories list/add/edit/delete/search`, `interview schedule/prep/mock/debrief`, `content plan/draft/schedule/performance`, `cover-letter`, `setup`, `init`, `tldr`, `doctor`, `mcp serve`, `optimize/validate/assisted` (legacy hidden)

### Key Failure Patterns

**Pattern 1: API key cascade** — Happy: GROQ_API_KEY → 200 → done. Sad: all keys empty → `LLMError("All LLM providers exhausted")` — loud, acceptable. 429 → 60s cooldown + multi-key rotation. `LR_LLM_MODE=agent` shortcuts to subprocess.

**Pattern 2: MongoDB-required commands** — Happy: Mongo up → ok. Sad: `_mongo_ok()` returns False → red error + exit 1. Stories CRUD hard-requires Mongo; interview/content has disk fallback (inconsistency — defer).

**Pattern 3: Auth-required commands** — Happy: session.json valid → 200. Sad: no session → login hint. Edge: JWT missing `exp` field → misleading "JWT is already expired" (should say "invalid JWT — missing exp").

**Pattern 4: Oracle PG commands** — `asyncpg` missing → actionable install hint. `ORACLE_PG_URL` not set → ValueError → points to `.env`. `admin companies import` lacks connection timeout — can hang indefinitely (B3-3).

**Pattern 5: Wizard / setup (PR #68)** — `gsk_...` format check gates save. Network down → key saved on format-valid, smoke fails, warning printed, user can `--check` later. Re-run with existing `.env` — in-place update works.

**Pattern 6: Stub commands** — `interview mock`, `content performance`, `resume score`, `resume batch` exit 0 with informational message. Should be exit 2. (Defer.)

### Prioritized Issue Buckets

#### 🚨 Bucket 1 — Data corruption / silent wrong output
**Count: 0** — no silent fabrication detected, cascade discipline enforced.

#### 🚨 Bucket 2 — Crash with unactionable error in happy/upgrade path (SHIP BLOCKERS)

**B2-1: v0.3.0 → v0.4.0 silent agent-mode persistence** (HIGH)
- Evidence: `setup_wizard.py:330-345` (`existing.update` preserves `agent_backend`); `resume/cli.py:124-125` (env vars set from old config); `direct.py:1189` (agent shortcut)
- Result: upgraded users keep agent mode, get none of the v0.4.0 Groq BYOK benefits. Worst case: opencode uninstalled → tailor crashes with no migration hint.
- Fix: detect `existing.get("default_llm_mode") == "agent"` in wizard, prompt user to migrate, strip `agent_backend` if they agree.

**B2-2: First-time user has no profile, every tailor pays 30–60s cost** (MEDIUM)
- Evidence: `setup_wizard.py:359-364` (post-setup message omits `profile create`); `resume/cli.py:83-106` (cache check silent if profile missing)
- Fix: append profile-create hint to wizard success message.

#### ⚠️ Bucket 3 — Crash with actionable error in sad path (acceptable)

**B3-1: `jobs apply` 401 mid-pipeline silently drops mark-applied POST** (MEDIUM) — `jobsearch/cli.py:451-463` catches exception, logs it, but user believes job is marked when it isn't.

**B3-2: `watch run` 403 silently drops all future captures** (HIGH) — `watch/poster.py:114-115` returns False on 4xx, no notification. User discovers only via `watch list` after browsing for hours.

**B3-3: `admin companies import` asyncpg pool hangs on unreachable Oracle PG** (MEDIUM) — `admin/cli.py:150` has no timeout on `asyncpg.create_pool()`.

**B3-4: `stories add --from-nugget` silent fallback when profile missing** (LOW) — `stories/cli.py:114-144` catches missing file silently, continues with empty result.

**B3-5: Generic "All LLM providers exhausted" doesn't mention setup** (LOW) — `direct.py:1338-1342`.

**B3-6: JWT missing `exp` field triggers misleading "JWT is expired"** (LOW) — `auth/cli.py:149`.

#### 🟡 Bucket 4 — Deployment dependencies / behavior changes

**B4-1: `/api/discoveries` POST not deployed → `jobs import` returns 405** — new command broken until endpoint deployed.

**B4-2: Layer 4 slug-discovery validator cron not deployed** — slugs go stale without manual `validate-all` runs.

**B4-3: `default_llm_mode: agent` → `direct` is a BREAKING change** — needs CHANGELOG callout.

**B4-4: Wizard removed `default_skill_mode` write** — existing 0.3.0 configs preserve old value; no impact until skill mode is wired (v0.5+).

**B4-5: `setup --check` exit code 0 even on smoke failure** — design choice; document in `--help`.

**B4-6: PR #64 pythonpath fix is incomplete for non-test paths** — developer-only gotcha; end users unaffected.

#### 🟡 Bucket 5 — Cosmetic / stubs (defer)

B5-1: Stub commands exit 0 instead of 2 | B5-2: Captures never pass `--grade` filter (null `auto_score_grade`) | B5-3: Stories CRUD hard-requires Mongo while interview/content has fallbacks | B5-4: Cover-letter silent generic on empty profile | B5-5: Legacy commands `optimize/validate/assisted` need deprecation timeline | B5-6: `_check_bin` dead code in `setup_wizard.py` | B5-7: macOS service install permission errors show raw traceback | B5-8: Watch `localhost:9222/health` timeout hardcoded.

---

## Part 4 — Fix Plan (v0.4.0 Tag Readiness)

> Source: static-qa-analysis-next-release-2026-05-05.md
> Goal: ship v0.4.0 to PyPI. Fix true blockers, defer polish, document known limitations.

### Stage 1 — MUST FIX before v0.4.0 tag (3 PRs, ~3 hours)

**PR-1: Wizard migration + post-setup profile hint** (`fix/wizard-migration-v040`)
- Issues: B2-1 + B2-2
- Files: `src/linkright/setup_wizard.py`
- Changes:
  1. After loading existing config, detect `existing.get("default_llm_mode") == "agent"`. If yes, prompt user to migrate. If agreed: strip `agent_backend`, write `default_llm_mode: direct`. If declined: preserve both.
  2. Append to wizard success message: "Recommended next step (one-time): `linkright profile create -r path/to/resume.pdf` → caches resume so every tailor is 30–60s faster."
- Verification: (a) No config → no prompt → writes direct. (b) agent config + Y → strips agent_backend, writes direct. (c) agent config + N → preserves agent. (d) direct config → no prompt.
- Risk: LOW (additive logic, gated on config detection)

**PR-2: CHANGELOG accuracy + BREAKING callout** (`docs/changelog-v040-accuracy`)
- Issues: B4-1 + B4-2 + B4-3
- Files: `CHANGELOG.md`
- Changes:
  1. Add BREAKING callout near top of v0.4.0 entry: "⚠️ BREAKING for users upgrading from 0.3.0: Default LLM mode changed from `agent` to `direct` (Groq BYOK). Run `linkright setup` after upgrading."
  2. Move `jobs import` from "Added" to "Known limitations": endpoint `/api/discoveries` POST not yet deployed; returns 405.
  3. Strengthen Layer 4 entry: "manual only; run `linkright admin slug-discovery validate-all [--max N]` as needed."
- Risk: ZERO (docs only)

**PR-3: Watch 403 notification** (`fix/watch-403-notification`)
- Issues: B3-2 (promoted to Stage 1 — silent failure of flagship feature)
- Files: `src/linkright/watch/poster.py`
- Changes: Module-level `_consecutive_403_count` counter. After 3 consecutive 403s, write to stderr: "⚠ Capture key rejected (N consecutive 403s). Verify: `linkright watch status`." Counter resets on 200/201 or after notification.
- Verification: Bad capture key → 3 page browses → warning fires. Fix key → success → counter resets.
- Risk: MEDIUM (touches daemon behavior; threshold tunable to 5 if too noisy)

**Stage 1 wrap-up:**
1. Bump `pyproject.toml` to 0.4.0 (already done at SHA f93a203)
2. Tag `v0.4.0` on main of inner repo
3. PyPI upload: `cd context/cli/linkright && python -m build && twine upload dist/*` (Satvik's manual op — needs PyPI token)
4. Verify `pip index versions linkright` shows 0.4.0
5. Manual QA pass per Section 2 above

### Stage 2 — STRONGLY RECOMMEND (v0.4.0 or v0.4.1 fast-follow, ~4 hours)

**PR-4: Auth/cascade error message polish** (`fix/auth-cascade-error-polish`)
- Issues: B3-1 + B3-5 + B3-6
- Files: `jobsearch/cli.py:451-463`, `llm/direct.py:1338-1342`, `auth/cli.py:149`
- Changes:
  - B3-1: On 401 mid-apply, print actionable warning: "Tailor done but mark-applied failed. Re-login: `linkright auth login`, then: `linkright jobs status <id> applied`."
  - B3-5: At cascade exhaustion, if ALL keys missing: suggest "Run `linkright setup` to add your free Groq key."
  - B3-6: Distinguish `exp` missing (invalid JWT) from `exp` in past (expired JWT) — different error messages.

**PR-5: Admin asyncpg connection timeout** (`fix/admin-asyncpg-timeout`)
- Issue: B3-3
- Files: `admin/cli.py:150` (and `watch/db.py` if same pattern)
- Change: `asyncpg.create_pool(..., timeout=10.0, command_timeout=30.0)`. Wrap in try/except TimeoutError + OSError with user-friendly messages. Make timeout configurable via `LINKRIGHT_PG_TIMEOUT` env (default 10).

**PR-6: stories add --from-nugget hard-check** (`fix/stories-from-nugget-profile-check`)
- Issue: B3-4
- Files: `stories/cli.py:114-144`
- Change: Hard-error if `~/.linkright/profile/nuggets.jsonl` doesn't exist. ClickException with `profile create` hint.

### Stage 3 — v0.4.2 cleanup (within 1 month, ~2.5 hours)

**PR-7:** Stub commands (`interview mock`, `content plan/draft/performance`, `resume score/batch`) exit 2 instead of 0. ClickException: "Not yet implemented."

**PR-8:** Dead code + minor polish — remove `_check_bin` (dead after PR #68), wrap macOS service install in try/except PermissionError, make `/health` timeout configurable via env.

**PR-9:** `jobs find --include-unscored` flag — capture rows with null `auto_score_grade` pass through when flag set.

### Stage 4 — Indefinite defer / docs only

| Issue | Action |
|---|---|
| B4-4: `default_skill_mode` silent | Wait until skill mode wired (v0.5+) |
| B4-5: `setup --check` exit 0 design | Keep; document in `--help` |
| B4-6: pythonpath dev gotcha | Add to CLAUDE.md dev-onboarding section |
| B5-3: stories Mongo vs disk fallback inconsistency | Resolve in v0.5 schema revisit |
| B5-4: cover-letter generic on empty profile | Low impact; defer |
| B5-5: legacy command deprecation timeline | Add note to inner CLAUDE.md |

### Global Ship Checklist

```
[ ] PR-1 merged (wizard migration + profile hint)
[ ] PR-2 merged (CHANGELOG accuracy + BREAKING callout)
[ ] PR-3 merged (watch 403 notification)
[ ] pyproject.toml version = 0.4.0
[ ] setup_wizard.py unit-tested across 4 config fixtures
[ ] Manual QA pass (Section 2 above, ~75-95 min)
[ ] Tag v0.4.0 on main of inner repo
[ ] PyPI upload via twine
[ ] pip index versions linkright shows 0.4.0
[ ] Smoke test: pip install in fresh venv → setup → resume tailor
[ ] GitHub release notes copy-pasted from CHANGELOG v0.4.0 entry
```

### Rollout Order

PRs 1, 2, 3 are independent (different files) and can open simultaneously. Stage 2 can start in parallel from separate worktrees. Recommended sequencing:

1. Stage 1 → tag v0.4.0 within 24 hours
2. Stage 2 → v0.4.1 patch within 1 week (bundle 3 PRs into one tag)
3. Stage 3 → v0.4.2 cleanup within 1 month
4. Stage 4 → docs PR any time, no version bump needed

### Critical Files Map

| File | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|
| `src/linkright/setup_wizard.py` | PR-1 | — | PR-8 |
| `src/linkright/watch/poster.py` | PR-3 | — | — |
| `src/linkright/watch/cli.py` | — | — | PR-8 |
| `src/linkright/watch/service.py` | — | — | PR-8 |
| `src/linkright/jobsearch/cli.py` | — | PR-4 | PR-9 |
| `src/linkright/llm/direct.py` | — | PR-4 | — |
| `src/linkright/auth/cli.py` | — | PR-4 | — |
| `src/linkright/admin/cli.py` | — | PR-5 | — |
| `src/linkright/stories/cli.py` | — | PR-6 | — |
| `src/linkright/interview/cli.py` | — | — | PR-7 |
| `src/linkright/content/cli.py` | — | — | PR-7 |
| `src/linkright/resume/cli.py` | — | — | PR-7 |
| `CHANGELOG.md` | PR-2 | — | — |

### Anti-scope

No new features. No backend deployments (Oracle VPS + Supabase = Satvik's manual operator tasks). No migration scripts. No website/worker changes. No version skipping. Agent mode stays functional for explicit opt-in. Legacy `optimize/validate/assisted` stay functional through v0.4.x.

---

## Bug-Reporting Template

```
[BUG] <one-line summary>

Section: <e.g. QA-4.5>
Command: <exact command>
Expected: <what QA plan said>
Got: <actual output — paste it>

Reproduction:
  1. ...
  2. ...

Severity: blocker | major | minor
```
