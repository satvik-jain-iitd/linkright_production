# LinkRight v1 — Manual QA Plan

> **Date**: 2026-05-03 (updated 2026-05-05)
> **Structure**: Section 1 = what a real new user runs. Admin sections (QA + Infra) = what only Satvik runs for pre-ship verification.

---

## 1 — User Onboarding Flow (~10 min)

> This is the exact journey a new job seeker will take after finding LinkRight on GitHub. Run this first — if this breaks, nothing else matters.

### 1.1 Install

```bash
pip install 'linkright[full]'
linkright --version
# Expect: linkright, version 0.4.0
```

### 1.2 Setup wizard (one-time)

```bash
linkright setup
# Expect: interactive wizard — picks LLM provider, embedder, PDF renderer
# At minimum: enter one free Groq API key when prompted
# Should complete in ~1 min
```

### 1.3 Health check

```bash
linkright doctor
# Expect: green ticks for config, API keys, deps, embedder, MongoDB
# Any RED item = stop and fix before continuing
```

### 1.4 Profile creation

```bash
linkright profile create -r /path/to/your/resume.pdf
# Expect: ~30-60s, "Profile saved with N nuggets"
```

### 1.5 Tailor a resume

```bash
linkright tailor -j /path/to/jd.md
# Expect: 16-step pipeline, ~2 min
# Final: "Score: XX.X (Grade: X)" + PDF path printed
# Open the PDF — verify it looks right
```

### 1.6 Cover letter

```bash
linkright cl -j /path/to/jd.md
# Expect: ~250-word cover letter, ~90 sec
```

### 1.7 Job search

```bash
linkright auth login
# Opens browser → OAuth → "Logged in as ..."

linkright jobs find
# Expect: ranked job table with scores
```

### 1.8 Watch setup (passive job capture)

```bash
linkright watch setup
# Expect: Chrome alias written to ~/.zshrc + next steps shown
```

### 1.9 Story Bank (interview prep)

```bash
linkright stories add
# Interactive prompts: Title, Situation, Task, Action, Result, Tags
# Expect: "✓ Story saved"

linkright stories list
# Expect: table with your story
```

**User Onboarding PASS = all 9 steps above work without error. This is the v1 ship bar.**

---
---

# Admin — QA Verification (Satvik only)

> Everything below is Satvik's pre-ship verification checklist. A regular user never runs any of this. Run after confirming Section 1 passes.

---

## QA-0 — Pre-flight (~5 min)

### QA-0.1 Editable install from source

> For QA runs, install from source worktree (not PyPI) to test the exact code being shipped.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/pip3 install -e \
  ~/Documents/linkright-wt/release-v04/context/cli/linkright/

linkright --version
# Expect: linkright, version 0.4.0
```

### QA-0.2 Config file presence

```bash
ls -la ~/.linkright/
# Expect: .env (mode 600), config.yaml, profile/, runs/, cache/

grep -E "^(LINKRIGHT_CAPTURE_KEY|GROQ_API_KEY|GEMINI_API_KEY)" ~/.linkright/.env | cut -d= -f1
# Expect: GROQ_API_KEY, GEMINI_API_KEY, LINKRIGHT_CAPTURE_KEY (+ rotation keys)
```

---

## QA-1 — Smoke tests (~5 min)

### QA-1.1 Help / version surface

```bash
linkright --help
# Expect: top-level command list including: auth, cl, content, cover-letter, critique,
#   doctor, fill, improve, init, interview, jobs, jobsearch, plan, practice, profile,
#   resume, score, setup, tailor, tldr, watch

linkright tldr
# Expect: one-page cheat sheet of common commands
```

### QA-1.2 watch status

```bash
linkright watch status
# Expect 4 lines (with ✓ or ✗ prefixes):
#   ✓ capture key:   set (len=49)
#   ✓ endpoint:      https://sync-resume-engine.onrender.com/api/captures
#   ✗ chrome CDP:    NOT reachable    [expected if Chrome not started with --remote-debugging-port=9222]
#   ✓ worker health: ... → 200
```

---

## QA-2 — Pillar 1: Resume + Cover Letter (~20-25 min)

> Pre-existing functionality from v0.3.0; verifying nothing regressed.

### QA-2.1 Tailor a resume (full pipeline)

```bash
ls ~/Documents/linkright_production/context/data/assets/resume-applications/ | head -3
# Pick any folder with a jd.md inside, e.g. highlevel_pm-workflows

linkright resume tailor \
  -j ~/Documents/linkright_production/context/data/assets/resume-applications/highlevel_pm-workflows/jd.md \
  --run-id qa_test_$(date +%s)
# Expect: 16-step pipeline, ~2 min wall time
# Final: "Score: XX.X (Grade: X)" + "PDF: ~/.linkright/runs/.../15_final_resume.pdf"
# Open PDF: header not clipped, bullets have metric bolds only, 1-page output
```

### QA-2.2 Score

```bash
linkright score -r ~/.linkright/runs/qa_test_*/15_final_resume.pdf -j .../jd.md
# Expect: 16-dimension scorecard, total ≥ 90
```

### QA-2.3 Critique

```bash
linkright critique --run-id qa_test_*
# Expect: 5 issues + 3 fix options each (one being "manual edit")
```

### QA-2.4 Fill metrics

```bash
linkright fill --run-id qa_test_*
# Expect: prompts for bullets with X% / $YM placeholders
# For each: 3 categories (actual / placeholder / drop)
# Verify: no fabricated numbers
```

### QA-2.5 Cover letter

```bash
linkright cl -j .../jd.md
# Expect: ~250-word cover letter PDF, 90 sec wall time
# Verify: references actual project context, has "why this company" paragraph
```

### QA-2.6 Brand-color resume + cover letter (PR #61)

#### QA-2.6a Interactive

```bash
linkright resume brand --run-id qa_test_*
# Prompts:
#   "  Primary brand hex: "                                       # type #635BFF
#   "  Secondary brand hex (optional, press Enter to skip): "    # type #00D4FF
#   "  Accent brand hex (optional, press Enter to skip): "       # press Enter
# Expect: branded PDF at artifacts/15_final_resume_branded.pdf
# Open PDF: ONLY metric bolds + section dividers colored. All other text black.
```

#### QA-2.6b Power-user flags

```bash
linkright resume brand --run-id qa_test_* --primary "#635BFF" --secondary "#00D4FF" --accent "#FF6B6B" --yes
# Expect: same output, no prompts
```

#### QA-2.6c Cover letter branded

```bash
linkright resume brand --run-id qa_test_* \
    --primary "#635BFF" --yes \
    --cover-letter ~/.linkright/runs/qa_test_*/artifacts/cover_letter.md
# Expect: branded cover letter PDF — metric bolds in primary color, all else black
```

#### QA-2.6d B&W default unchanged

```bash
ls ~/.linkright/runs/qa_test_*/artifacts/15_final_resume.pdf
# Open it — expect pure B&W. Brand command must NOT modify the original.
```

#### QA-2.6e Hex validation

```bash
linkright resume brand --run-id qa_test_* --primary "not-a-hex" --yes
# Expect: "Error: --primary is required when --yes is set (no interactive prompt)"
linkright resume brand --run-id qa_test_* --primary "#GGGGGG" --yes
# Expect: same error — invalid hex chars normalize to None
```

---

## QA-3 — Pillar 2: Job Search (~10-15 min)

### QA-3.1 Auth

```bash
linkright auth login
linkright auth status
# Expect: "Logged in as <email>"
```

### QA-3.2 Jobs find — dual-read (PR #58)

#### QA-3.2a Captures-only (no auth)

```bash
linkright auth logout
linkright jobs find --top 5
# Expect: "⚠ not logged in — showing captures only..." then empty or capture rows
linkright auth login
```

#### QA-3.2b Both sources

```bash
linkright jobs find --top 10
# Expect: table with Rank / Grade / Title / Company / Score / Source
# Bottom: "X scored + Y from captures"
```

#### QA-3.2c Filters

```bash
linkright jobs find --location bangalore --top 5
linkright jobs find --grade A --top 5
linkright jobs find --top 5 --json | jq '.[].job_discoveries.title'
```

### QA-3.3 Show / apply / status

```bash
linkright jobs show <id-prefix>
linkright jobs apply <id-prefix>          # full tailor pipeline runs
linkright jobs status <id-prefix> interviewing
```

---

## QA-4 — Sprint D / `linkright watch` (~15-20 min)

### QA-4.1 Setup

```bash
linkright watch setup
source ~/.zshrc
which chrome
```

### QA-4.2 Chrome CDP

```bash
# Quit Chrome completely (cmd-Q), then:
chrome
curl -sS http://localhost:9222/json/version
# Expect: JSON with webSocketDebuggerUrl
```

### QA-4.3 Status — all green

```bash
linkright watch status
# Expect: 4 ✓ lines
```

### QA-4.4 Foreground listener

```bash
linkright watch -v
# Browse a Naukri job page in Chrome
# Expect log: "✓ <title> — 201 dedup=new"
# ctrl-C → exit 0
```

### QA-4.5 Capture list

```bash
linkright watch list --since "5 minutes" --top 5
linkright watch list --since "5 minutes" --json | jq '.[].job_url'
```

### QA-4.6 Background daemon

```bash
linkright watch install-service
launchctl list | grep linkright     # Expect: "0  -  in.linkright.watch"
tail -f ~/.linkright/watch.log      # ctrl-C to stop
linkright watch uninstall-service
linkright watch install-service
```

### QA-4.7 Multi-portal (PR #57 — 7 portals)

Browse one job page per portal, confirm each appears in `linkright watch list`:

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

### QA-4.8 Privacy regression

```bash
# Browse linkedin.com/messaging/ or naukri.com/notifications in Chrome
linkright watch list --since "1 minute" --json | jq '.[].job_url'
# Expect: NO private-path URLs
```

---

## QA-5 — Pillar 3: Story Bank (~8 min)

### QA-5.1 Practice cards

```bash
linkright practice
# Expect: STAR-format prep cards from career nuggets
```

### QA-5.2–5.9 Story Bank CRUD

```bash
linkright stories list                         # empty state: "No stories yet"
linkright stories add                          # fill 6 prompts → "✓ Story saved"
linkright stories add --from-nugget "AML"      # pre-fills result from nugget
linkright stories list                         # populated table
linkright stories search "AML"                 # matching stories printed
linkright stories edit "My Test"               # change one field → "✓ Updated 1 fields"
linkright stories delete "My Test"             # type n → "Cancelled."
linkright stories delete "My Test" --yes       # "✓ Deleted"
```

### QA-5.10 Interview prep bridge

```bash
linkright interview prep
# Expect: prep cards surface Story Bank entries (PR #62)
```

### QA-5.11 Duplicate-title guard

```bash
linkright stories add --yes --title "Dup Test" --action "x" --result "y"
linkright stories add --yes --title "Dup Test" --action "diff" --result "diff"
# Expect: ClickException — title already exists
linkright stories delete "Dup Test" --yes
```

### QA-5.12 Whitespace rejection

```bash
linkright stories add --yes --title "   " --action "A" --result "R"
# Expect: ClickException — title + action + result required and non-empty
```

---

## QA-6 — Pillar 4: Content (~3 min)

```bash
linkright content plan
linkright content draft
# Expect: commands run without error, output is a reasonable draft
```

---

## QA-7 — Regression (~5 min)

### QA-7.1 jobs find dedup

Apply a job via QA-3.3, then browse the SAME URL in Chrome. `linkright jobs find` must NOT show it twice — Supabase row wins.

### QA-7.2 watch list filters

```bash
linkright watch list --since "1 day"
linkright watch list --source capture_naukri
linkright watch list --since "1 day; DROP TABLE x"
# Last: expect "✗ invalid --since value..." (SQL injection guard)
```

---

## QA-8 — Known limitations (skip-verify)

| Limitation | Reason | Fix |
|---|---|---|
| LinkedIn SPA URLs may miss | pushState pattern not empirically validated | Phase 2 |
| Mobile browsing not captured | No CLI on iOS/Android | v2 |
| Render cold start 30-60s | Free plan idle | Render paid eventually |
| ats_provider=NULL for Indian unicorns | Tier3 iframe pattern mismatch | Phase 2 |
| Story Bank tailor bridge | Deferred to v0.5 per scope lock | Next sprint |
| Mock Interview / Negotiation | v2 deferred | v2 |

---

## QA-9 — Bug-reporting template

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

---

## Ship readiness checklist

- [ ] Section 1 (User Onboarding) — full happy path works
- [ ] QA-2 Pillar 1 — resume + CL + brand all pass
- [ ] QA-3 Pillar 2 — jobs find dual-read + apply + status pass
- [ ] QA-4 Sprint D — watch listener + daemon + 7 portals + privacy pass
- [ ] QA-5 Pillar 3 — Story Bank CRUD + interview bridge pass
- [ ] QA-6 Pillar 4 — content commands run
- [ ] QA-7 Regression — dedup + SQL injection guard pass
- [ ] Admin-Infra checks pass (Section below)

---

## Run-time estimate

| Section | Time |
|---|---|
| 1 — User Onboarding | 10 min |
| QA-0 Pre-flight | 5 min |
| QA-1 Smoke tests | 5 min |
| QA-2 Pillar 1 (incl. brand QA-2.6a-e) | 20-25 min |
| QA-3 Pillar 2 | 10-15 min |
| QA-4 Sprint D | 15-20 min |
| QA-5 Pillar 3 + Story Bank | 8 min |
| QA-6 Pillar 4 | 3 min |
| QA-7 Regression | 5 min |
| **Total user-facing** | **~81-96 min** |
| **Admin-Infra (below)** | **~15 min** |

---
---

# Admin — Infrastructure (Satvik only)

> Oracle Postgres, asyncpg, curl API checks. Run last, separately.

---

## Infra-1 Backend reachability

```bash
curl -sS -m 30 https://sync-resume-engine.onrender.com/health
# Expect: {"status":"ok","service":"linkright-sync-worker", ...}
# (First request may take 30-60s — Render free-plan cold start)

set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
python3 -c "
import asyncio, asyncpg, os
async def main():
    pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
    async with pool.acquire() as conn:
        v = await conn.fetchval('SELECT version()')
        c = await conn.fetchval('SELECT COUNT(*) FROM companies')
        j = await conn.fetchval('SELECT COUNT(*) FROM job_discoveries')
        print(f'PG: {v[:50]}... | companies={c} | job_discoveries={j}')
    await pool.close()
asyncio.run(main())
"
# Expect: PG version | companies=81+ | job_discoveries=N
```

## Infra-2 Captures persist in Oracle PG

```bash
set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
python3 -c "
import asyncio, asyncpg, os
async def main():
    pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
    async with pool.acquire() as conn:
        n = await conn.fetchval('SELECT COUNT(*) FROM job_discoveries')
        n_today = await conn.fetchval(\"SELECT COUNT(*) FROM job_discoveries WHERE captured_at > NOW() - INTERVAL '1 day'\")
        print(f'total: {n} | today: {n_today}')
    await pool.close()
asyncio.run(main())
"
# Expect: numbers match what you browsed in QA-4
```

## Infra-3 Sprint B trigger (PR #59)

Browse a Naukri job at an unknown niche company (NOT Stripe/Anthropic — those are seeded).

```bash
linkright admin companies stats
# Expect: total > 81

set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
python3 -c "
import asyncio, asyncpg, os
async def main():
    pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
    async with pool.acquire() as conn:
        rows = await conn.fetch(\"SELECT name, ats_provider, ingested_at FROM companies WHERE 'passive_capture_naukri' = ANY(source) ORDER BY ingested_at DESC LIMIT 5\")
        for r in rows: print(dict(r))
    await pool.close()
asyncio.run(main())
"
# Expect: new company row; ats_provider filled or NULL (Indian unicorns often NULL — expected)
```

## Infra-4 API edge cases — privacy filter + auth

```bash
# Privacy filter test
curl -sS -X POST https://sync-resume-engine.onrender.com/api/captures \
  -H "Content-Type: application/json" \
  -H "X-LinkRight-Capture-Key: $(grep '^LINKRIGHT_CAPTURE_KEY=' ~/.linkright/.env | cut -d= -f2-)" \
  -d '{"source":"naukri","job_url":"https://www.naukri.com/messages/inbox/123","title":"x","company_name":"x","captured_at":"2026-05-03T12:00:00Z"}' \
  -w "\nHTTP %{http_code}\n"
# Expect: HTTP 403 + "blocked by privacy filter..."

# Wrong auth key
curl -sS -X POST https://sync-resume-engine.onrender.com/api/captures \
  -H "Content-Type: application/json" \
  -H "X-LinkRight-Capture-Key: wrong-key" \
  -d '{"source":"naukri","job_url":"https://www.naukri.com/job-listings-test","title":"x","company_name":"x","captured_at":"2026-05-03T12:00:00Z"}' \
  -w "\nHTTP %{http_code}\n"
# Expect: HTTP 401 + "invalid or missing capture key"
```

## Infra-5 Slug discovery

```bash
linkright admin slug-discovery single Anthropic
# Expect: ATS provider/slug detected
linkright admin slug-discovery stats
# Expect: last-24h stats
linkright admin slug-discovery validate-all --max 3
# Expect: validated/healed/marked-zero counts
```

## Infra-6 Companies stats

```bash
linkright admin companies stats
# Expect: total count, by industry, by ATS provider
```

**Infra PASS = all Infra-1 through Infra-6 produce expected output.**
