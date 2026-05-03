# LinkRight v1 — Manual QA Plan

> **Date**: 2026-05-03
> **Audience**: Satvik (sole tester for v1 pre-public-GitHub release)
> **Scope**: every user-facing CLI command + every cross-cutting flow shipped through PRs #50–#62 (Sprint D watch + Pillar 2 dual-read + brand-color + Story Bank). Deferred items (e.g., tailor pipeline reading stories alongside nuggets) are explicitly called out as v0.5 work, not v1 gaps.
> **Goal**: sit at terminal, run each section in order, verify expected output, log any deviations using the bug template at the end

This is a **runnable checklist**, not a document. Each section is "Do X → Expect Y → Log if not Y". Estimated total run-time: 75-95 min if everything works first try (see breakdown table at end).

---

## 0 — Pre-flight (one-time, ~5 min)

### 0.1 Tooling sanity

```bash
which python3
python3 --version          # expect: 3.9+ (3.12.7 confirmed working)
which pip
which linkright            # expect: path inside your env, NOT /usr/local/bin
linkright --version        # expect: 0.3.0 or 0.4.0 depending on PyPI release status
```

### 0.2 Editable install of the latest local code

```bash
cd ~/Documents/linkright_production/repo
git status
# Confirm: clean working tree, branch=main, up-to-date with origin/main

git log --oneline -5
# Top commits should include:
#   feat(captures): trigger Sprint B slug auto-discovery on new-company captures (#59)
#   feat(jobsearch): dual-read in 'jobs find' — Supabase scored feed + Oracle PG captures merged (#58)
#   feat(captures): widen coverage to 7 portals — ... (#57)
#   feat(watch): linkright watch list — ... (#56)
#   feat(cli): linkright watch — ... (#55)

pip install -e context/cli/linkright/
linkright --version
# Should now load FROM the editable install at ~/Documents/linkright_production/repo/...
```

### 0.3 Config file presence

```bash
ls -la ~/.linkright/
# Expect: .env (mode 600), .env.oracle (mode 600), config.yaml, profile/, runs/, cache/

grep -E "^(LINKRIGHT_CAPTURE_KEY|GROQ_API_KEY|GEMINI_API_KEY)" ~/.linkright/.env | cut -d= -f1
# Expect lines printed for each key — values redacted by cut
# At minimum: LINKRIGHT_CAPTURE_KEY, GROQ_API_KEY (or any LLM provider)

grep "^ORACLE_PG_URL" ~/.linkright/.env.oracle
# Expect: ORACLE_PG_URL=postgres://linkright_app:...@80.225.198.184:5432/linkright_jobs?sslmode=prefer
```

**If anything missing**: stop, fix, then continue.

### 0.4 Backend reachability

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
# Expect: PG version line | companies=81 (or higher if you've browsed) | job_discoveries=N
```

---

## 1 — Smoke tests (5 min)

### 1.1 Help / version surface

```bash
linkright --help
# Expect: top-level command list including: auth, cl, content, cover-letter, critique,
#   doctor, fill, improve, init, interview, jobs, jobsearch, plan, practice, profile,
#   resume, score, setup, tailor, tldr, watch

linkright tldr
# Expect: one-page cheat sheet of common commands
```

### 1.2 Doctor (existing health-check)

```bash
linkright doctor
# Expect: green ticks for config, API keys, deps, embedder, MongoDB
# Note any RED items — they may indicate setup gaps
```

### 1.3 watch status (NEW PR #55 + PR #60)

```bash
linkright watch status
# Expect 4 lines (with ✓ or ✗ prefixes):
#   ✓ capture key:   set (len=49)
#   ✓ endpoint:      https://sync-resume-engine.onrender.com/api/captures
#   ✗ chrome CDP:    NOT reachable    [✗ EXPECTED if Chrome is not started with --remote-debugging-port=9222 yet]
#   ✓ worker health: ... → 200
```

---

## 2 — Pillar 1: Resume + Cover Letter (20-25 min)

> Pre-existing functionality from v0.3.0; verifying nothing regressed.

### 2.1 Profile already exists?

```bash
linkright profile show
# If output: shows your nuggets/career data → skip 2.2
# If error "no profile": run 2.2 first
```

### 2.2 Profile creation (only if 2.1 said "no profile")

```bash
linkright profile create
# Interactive wizard — feed your resume PDF, answer prompts
# Expected: ~30-60s, output "Profile saved with N nuggets"
```

### 2.3 Tailor a resume

```bash
# Use the sample JD that ships with the repo — find one:
ls ~/Documents/linkright_production/context/data/assets/resume-applications/ | head -3
# Pick any folder with a jd.md inside, e.g. highlevel_pm-workflows

linkright resume tailor \
  -j ~/Documents/linkright_production/context/data/assets/resume-applications/highlevel_pm-workflows/jd.md \
  --run-id qa_test_$(date +%s)
# Expect: 16-step pipeline runs, ~2 min wall time
# Final lines should show: "Score: XX.X (Grade: X)" + "PDF: ~/.linkright/runs/.../15_final_resume.pdf"
# Verify the PDF: open it manually, check for:
#   - Header has your name + role title (no clipping)
#   - 4-6 bullets per role, all metrics bold, no placeholder X% / $YM
#   - 1-page output, no overflow
```

### 2.4 Score a tailored PDF

```bash
linkright score -r ~/.linkright/runs/qa_test_*/15_final_resume.pdf -j .../jd.md
# Expect: 16-dimension scorecard, total ≥ 90
```

### 2.5 Critique (Truth Engine layer 3)

```bash
linkright critique --run-id qa_test_*
# Expect: 5 issues + 3 fix options each (one being "manual edit")
# Don't have to apply — just verify the LLM produced sensible output
```

### 2.6 Fill metrics (interactive)

```bash
linkright fill --run-id qa_test_*
# Expect: prompts for any bullet with X% / $YM placeholders
# For each: shows 3 categories (actual / placeholder / drop), you pick one
# Verify: no fabricated numbers in final output
```

### 2.7 Cover letter

```bash
linkright cl -j .../jd.md
# Or: linkright cover-letter -j .../jd.md
# Expect: ~250-word cover letter PDF, 90 sec wall time
# Verify: references your actual project context, has a "why this company" paragraph
```

### 2.8 Brand-color resume + cover letter (PR #61, optional)

Default tailor output is pure B&W. Opt in to company-branded design by piping
1-3 hex codes via the new `linkright resume brand` subcommand.

#### 2.8a Interactive (3 prompts)

```bash
linkright resume brand --run-id qa_test_*
# Expect 3 sequential prompts (Click appends ": " to each label):
#   "  Primary brand hex: "                                       # type #635BFF
#   "  Secondary brand hex (optional, press Enter to skip): "    # type #00D4FF
#   "  Accent brand hex (optional, press Enter to skip): "       # press Enter
# (Note: the first prompt has no "(required)" suffix — it is distinguished
#  from the optional ones by ABSENCE of "(optional, ...)".)
# Expect: "branded resume:        ~/.linkright/runs/qa_test_*/artifacts/15_final_resume_branded.pdf"
# Open the PDF: only metric bolds + section dividers should be colored.
# All other text (headings, body, dates, locations, bullets) MUST be black.
```

#### 2.8b Power-user flags

```bash
linkright resume brand --run-id qa_test_* --primary "#635BFF" --secondary "#00D4FF" --accent "#FF6B6B" --yes
# Expect: same output as 2.8a but no prompts
```

#### 2.8c Cover letter branded too

```bash
linkright resume brand --run-id qa_test_* \
    --primary "#635BFF" --yes \
    --cover-letter ~/.linkright/runs/qa_test_*/artifacts/cover_letter.md
# Expect: "branded cover letter:  ~/.linkright/runs/qa_test_*/artifacts/cover_letter_branded.pdf"
# Open the CL PDF: bolded metrics ($1.2M, 40%, etc.) should be in primary color.
# All other text remains black on white.
```

#### 2.8d B&W default unchanged

```bash
ls ~/.linkright/runs/qa_test_*/artifacts/15_final_resume.pdf
# This is the ORIGINAL (B&W) PDF from `linkright resume tailor`. Open it.
# Expect: pure black text on pure white, no navy/blue tints anywhere.
# Verifies: brand subcommand does NOT modify the original — branded version is a separate file.
```

#### 2.8e Hex validation

```bash
linkright resume brand --run-id qa_test_* --primary "not-a-hex" --yes
# Expect exact error: "Error: --primary is required when --yes is set (no interactive prompt)"
# (invalid hex normalized to None, then --yes guard fires)
linkright resume brand --run-id qa_test_* --primary "#GGGGGG" --yes
# Expect: same exact error — invalid hex chars normalize to None
```

**Pillar 1 PASS = all 8 commands above produce expected output.**

---

## 3 — Pillar 2: Job Search (10-15 min)

### 3.1 Auth login

```bash
linkright auth login
# Expect: opens browser to sync.linkright.in OAuth flow
# After consent: terminal shows "Logged in as ..."

linkright auth status
# Expect: "Logged in as <email>"
```

### 3.2 Jobs find — the new dual-read (PR #58)

#### 3.2a Captures-only mode (no auth scenario)

```bash
linkright auth logout
linkright jobs find --top 5
# Expect: "⚠ not logged in to sync.linkright.in — showing captures only..."
# Then either:
#   - Empty: "Error: No jobs available. Either: ... auth login OR watch setup"
#   - Or: rich table with rows from Oracle PG captures
linkright auth login   # restore session for next steps
```

#### 3.2b Both-sources mode

```bash
linkright jobs find --top 10
# Expect: rich table with columns: Rank, Grade, Title, Company, Location, Score, Source, Action
# Bottom line: "X scored + Y from captures. Use 'linkright jobs show <id>' for full detail."
```

#### 3.2c Filters

```bash
linkright jobs find --location bangalore --top 5
linkright jobs find --grade A --top 5
linkright jobs find --top 5 --json | jq '.[].job_discoveries.title'
# Expect: filters apply correctly; --json produces parseable JSON output
```

### 3.3 Show job detail

```bash
# Take an ID from the find output, e.g. first 8 chars
linkright jobs show <id-prefix>
# Expect: full JD detail view — title, company, location, score breakdown, JD text
```

### 3.4 Apply flow

```bash
linkright jobs apply <id-prefix>
# Expect: tailors resume + cover letter for that JD, marks status='applied'
# (May take 2-3 min — full Pillar 1 pipeline runs)
```

### 3.5 Update status

```bash
linkright jobs status <id-prefix> interviewing
# Expect: "Updated to status=interviewing"
```

### 3.6 CSV import (optional power-user flow)

```bash
# Use any CSV with at least: title, company_name, job_url columns
linkright jobs import path/to/jobs.csv
# Expect: "Imported N rows"
```

**Pillar 2 PASS = jobs find shows captures + scored merge, show/apply/status work end-to-end.**

---

## 4 — Sprint D / `linkright watch` (15-20 min — THE HOTTEST NEW STUFF)

### 4.1 One-time setup (skip if already done)

```bash
linkright watch setup
# Expect: detects Chrome path + writes alias to ~/.zshrc (or .bashrc)
# Output: 4 lines starting with ✓ + Next steps section

source ~/.zshrc       # or restart terminal
which chrome           # expect: chrome alias defined
```

### 4.2 Restart Chrome via the alias

```bash
# Quit Chrome COMPLETELY (cmd-Q on Mac)
chrome
# Expect: Chrome opens, you can see your tabs etc.
# Behind the scenes: started with --remote-debugging-port=9222

# Verify CDP is exposed:
curl -sS http://localhost:9222/json/version
# Expect: JSON with "Browser":"Chrome/...","webSocketDebuggerUrl":"ws://..."
```

### 4.3 watch status — should now show all green

```bash
linkright watch status
# Expect: 4 ✓ lines (chrome CDP now reachable)
```

### 4.4 Foreground listener test

In one terminal:
```bash
linkright watch -v   # -v for verbose log
# Expect: "🔍 linkright watch — listening on localhost:9222 ..."
# Then: silence (waiting for events)
```

In your Chrome, browse a Naukri job page (any job listing).

Back in the terminal, expect a log line like:
```
HH:MM:SS → naukri — https://www.naukri.com/job-listings-...
HH:MM:SS   ✓ Senior Product Manager — 201 dedup=new
```

Press ctrl-C to stop. Should exit cleanly (PR #60: KeyboardInterrupt → exit 0).

### 4.5 Verify capture landed in Oracle PG

```bash
linkright watch list --since "5 minutes" --top 5
# Expect: rich table showing the job(s) you just browsed
# Columns: #, Captured, Source, Company, Title, Location

linkright watch list --since "5 minutes" --json | jq '.[].job_url'
# Expect: list of URLs you browsed
```

### 4.6 Background daemon

```bash
linkright watch install-service
# Expect: ✓ installed ~/Library/LaunchAgents/in.linkright.watch.plist + loaded into launchd
# Output mentions log paths

# Verify it's running
launchctl list | grep linkright
# Expect: "0  -  in.linkright.watch" (the 0 = clean exit; daemon is alive)

tail -f ~/.linkright/watch.log
# Expect: capture log lines as you browse Naukri pages
# Press ctrl-C to stop watching the log

linkright watch uninstall-service
# Then re-install to leave the daemon running for ongoing tests
linkright watch install-service
```

### 4.7 Multi-portal verification (PR #57 — 7 portals)

For EACH of these, browse one job page in Chrome and confirm `linkright watch list` shows it within 10 sec:

| Portal | Test URL pattern | Expected source_type |
|---|---|---|
| Naukri | `naukri.com/job-listings-*` | capture_naukri |
| LinkedIn | `linkedin.com/jobs/view/<id>` | capture_linkedin |
| Indeed | `indeed.com/viewjob?jk=<key>` | capture_indeed |
| Greenhouse | `boards.greenhouse.io/<tenant>/jobs/<id>` (e.g. `anthropic`) | capture_greenhouse |
| Lever | `jobs.lever.co/<tenant>/<uuid>` | capture_lever |
| Ashby | `jobs.ashbyhq.com/<tenant>/<uuid>` | capture_ashby |
| Wellfound | `wellfound.com/jobs/<id>-<slug>` | capture_wellfound |

**Tip**: search "anthropic careers" in Google to find a real Greenhouse board, "openai careers" for Ashby, etc.

```bash
# After browsing all 7, verify each appeared:
linkright watch list --json | jq -r '.[].source_type' | sort -u
# Expect: each capture_* type listed
```

### 4.8 Privacy regression — should BLOCK

In Chrome, visit `https://www.naukri.com/notifications` or `https://www.linkedin.com/messaging/`.

Background daemon should NOT capture these. Verify:

```bash
linkright watch list --since "1 minute" --json | jq '.[].job_url'
# Expect: NO URL containing /notifications/ or /messaging/ or /inbox/
```

If a private path appears: BUG (file via section 9).

### 4.9 Sprint B trigger on NEW company (PR #59)

Browse a Naukri job at a company you've never seen before — pick something niche, NOT Stripe/Anthropic/Razorpay (those are in the 81-seed). E.g. some local Indian startup job.

```bash
# Wait 10-15 sec after browsing for the BackgroundTask to complete
# Then:
linkright admin companies stats
# Expect: total companies count > 81 (you just added a new one)

# Spot-check the new company's ats_provider was filled:
set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
python3 -c "
import asyncio, asyncpg, os
async def main():
    pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
    async with pool.acquire() as conn:
        rows = await conn.fetch(\"SELECT name, ats_provider, ats_slug, ingested_at FROM companies WHERE 'passive_capture_naukri' = ANY(source) ORDER BY ingested_at DESC LIMIT 5\")
        for r in rows: print(dict(r))
    await pool.close()
asyncio.run(main())
"
# Expect: most recent newly-captured company has ats_provider filled (e.g. 'greenhouse', 'lever', 'ashby')
# OR ats_provider=None — meaning Sprint B's 3 tiers couldn't find it (Indian unicorns often miss; expected)
```

### 4.10 Edge cases

```bash
# Bad URL for /api/captures (privacy filter test)
curl -sS -X POST https://sync-resume-engine.onrender.com/api/captures \
  -H "Content-Type: application/json" \
  -H "X-LinkRight-Capture-Key: $(grep '^LINKRIGHT_CAPTURE_KEY=' ~/.linkright/.env | cut -d= -f2-)" \
  -d '{"source":"naukri","job_url":"https://www.naukri.com/messages/inbox/123","title":"x","company_name":"x","captured_at":"2026-05-03T12:00:00Z"}' \
  -w "\nHTTP %{http_code}\n"
# Expect: HTTP 403 + "blocked by privacy filter: path '/messages/inbox/123' matches blocklist..."

# Wrong auth key
curl -sS -X POST https://sync-resume-engine.onrender.com/api/captures \
  -H "Content-Type: application/json" \
  -H "X-LinkRight-Capture-Key: wrong-key" \
  -d '{"source":"naukri","job_url":"https://www.naukri.com/job-listings-test","title":"x","company_name":"x","captured_at":"2026-05-03T12:00:00Z"}' \
  -w "\nHTTP %{http_code}\n"
# Expect: HTTP 401 + "invalid or missing capture key"
```

**Sprint D PASS = setup, listener, list, daemon, multi-portal, privacy filter, Sprint B trigger ALL work end-to-end.**

---

## 5 — Pillar 3: Interview Prep + Story Bank (8 min)

### 5.1 Practice cards (existing flow)

```bash
linkright practice
# OR: linkright interview practice
# Expect: STAR-format prep cards generated from your career nuggets matched to a JD
```

### 5.2 Story Bank — list (empty state)

```bash
linkright stories list
# Expect first time: "No stories yet — run `linkright stories add` to create one."
# Aliases also work: `linkright stories ls`
```

### 5.3 Story Bank — add via interactive prompts

```bash
linkright stories add
# Expect 6 sequential prompts: Title, Situation, Task, Action, Result, Tags
# Type:  My Test Story / Pipeline broke / Restore in 24h / Built oracle / $1.2M saved / python, leadership
# Expect: "✓ Story saved: <ObjectId>" in green
```

### 5.4 Story Bank — add from existing resume nugget (Truth Engine flow)

```bash
linkright stories add --from-nugget "AML"
# Pre-condition: profile must have a nugget containing "AML" (run `linkright profile show` to check)
# Expect: "Pre-filling `result` from nugget: <text>..." then prompts for Title, Situation, Task, Action
# (Result is pre-filled with the nugget text — accept or edit)
# Expect: "✓ Story saved: <ObjectId>"
```

### 5.5 Story Bank — list (populated state)

```bash
linkright stories list
# Expect: rich table — ID (8 hex chars) | Title | Tags | Used (count) | Last (date)
# Most recent stories first
```

### 5.6 Story Bank — search (text + vector)

```bash
linkright stories search "AML"
# Expect: matching stories printed with title + Action excerpt + Result excerpt + Tags
# Aliases: `linkright stories find "AML"`
```

### 5.7 Story Bank — edit

```bash
linkright stories edit "My Test"
# Expect: "Editing: My Test Story\nPress Enter to keep existing value."
# Walk through 6 prompts; change ONE field (e.g., Action), Enter for the rest
# Expect: "✓ Updated 1 fields" in green
```

### 5.8 Story Bank — delete (with confirmation)

```bash
linkright stories delete "My Test"
# Expect: "Delete story 'My Test Story'? This cannot be undone. [y/N]:"
# Type: n
# Expect: "Cancelled."
# Repeat with --yes flag:
linkright stories delete "My Test" --yes
# Expect: "✓ Deleted: My Test Story" in red
```

### 5.9 Story Bank ↔ Interview Prep bridge

```bash
linkright interview prep
# After adding stories above, expect: prep cards now surface YOUR Story Bank entries
# (not just generic STAR scaffolds)
# Verifies: retrieve_stars() reads `career_stories` collection (PR #62)
# Legacy `user_context` debriefs (if any) merge in below career_stories ranking
```

### 5.10 Story Bank — duplicate-title guard

```bash
linkright stories add --yes --title "Dup Test" --action "x" --result "y"
# Expect: ✓ saved
linkright stories add --yes --title "Dup Test" --action "different" --result "different"
# Expect: ClickException — "A story titled 'Dup Test' already exists. Use `linkright stories edit \"<title>\"`..."
# Cleanup:
linkright stories delete "Dup Test" --yes
```

### 5.11 Story Bank — whitespace input rejection

```bash
linkright stories add --yes --title "   " --action "A" --result "R"
# Expect: ClickException — "title + action + result are required and must be non-empty"
linkright stories add --yes --title "T" --action " " --result "R"
# Expect: same error citing action
```

**Pillar 3 v1 PASS = practice cards work + 5.2 through 5.11 all behave as expected.**

---

## 6 — Pillar 4: Content (basic scaffold) (3 min)

### 6.1 Plan + draft

```bash
linkright content plan
linkright content draft
# Expect: basic content plan / draft generation. Limited scope — Pillar 4 is not v1 priority.
```

**Pillar 4 PASS = commands run without error, output is a reasonable starting draft.**

---

## 7 — Admin commands (power-user / builder) (5 min, optional)

### 7.1 Slug discovery

```bash
linkright admin slug-discovery single Anthropic
# Expect: ATS provider/slug detected via tier1_html
linkright admin slug-discovery stats
# Expect: last-24h discovery stats
linkright admin slug-discovery validate-all --max 3
# Expect: re-validates 3 stale companies, shows validated/healed/marked-zero counts
```

### 7.2 Companies stats

```bash
linkright admin companies stats
# Expect: total count, by industry, by ATS provider
```

**Admin PASS = all 4 admin commands produce output without error.**

---

## 8 — Cross-cutting regression checks (5 min)

### 8.1 Captures actually persist

```bash
set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
python3 -c "
import asyncio, asyncpg, os
async def main():
    pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
    async with pool.acquire() as conn:
        n = await conn.fetchval('SELECT COUNT(*) FROM job_discoveries')
        n_today = await conn.fetchval(\"SELECT COUNT(*) FROM job_discoveries WHERE captured_at > NOW() - INTERVAL '1 day'\")
        print(f'job_discoveries total: {n} | today: {n_today}')
    await pool.close()
asyncio.run(main())
"
# Expect: numbers match what you've been browsing
```

### 8.2 jobs find dedup behavior

If you applied to a job via 3.4 (which marks it in Supabase), then browse the SAME URL via Chrome (which captures it to Oracle PG), `linkright jobs find` should NOT show it twice — Supabase row should win the merge dedup.

### 8.3 watch list filters

```bash
linkright watch list --since "1 day"
linkright watch list --source capture_naukri
linkright watch list --since "1 day; DROP TABLE x"
# Last one: expect "✗ invalid --since value..." rejection (SQL injection guard)
```

---

## 9 — Known limitations (skip-verify items)

These are documented gaps. Don't waste time testing — they won't work today.

| Limitation | Reason | Will be fixed |
|---|---|---|
| LinkedIn DOM extraction may fail on `/jobs/collections/` SPA URLs | LinkedIn pushState pattern; selectors not empirically validated | Phase 2 / soak data |
| Mobile browsing not captured | No CLI on iOS/Android | v2 |
| Render free-plan cold start | First POST after 15-min idle takes 30-60s | Render paid plan eventually |
| Some ATS captures show ats_provider=NULL after Sprint B trigger | Tier3 iframe pattern doesn't match all Indian portals | Phase 2 / Naukri tier1.5 |
| Watchlist UX still pre-demotion in code | Code works, docs/onboarding flow not updated yet | Pre-ship cleanup PR |
| Story Bank tailor bridge (resume bullets surface stories) | Locked v1 scope item — deferred to v0.5 pending RCA | Next sprint |
| Mock Interview / Negotiation | v2 deferred per scope decision | v2 |

---

## 10 — Bug-reporting template

For ANY deviation from expected behavior, paste this in chat:

```
[BUG] <one-line summary>

Section: <e.g. 4.5 watch list>
Command: <exact command you ran>
Input/state: <what was the env state, what file etc.>

Expected: <what the QA plan said should happen>
Got: <what actually happened — paste the output>

Reproduction:
  1. <step 1>
  2. <step 2>
  ...

Severity: blocker | major | minor

Additional context: <env vars, screenshots, logs>
```

---

## v1 ship readiness — overall pass criteria

- [ ] All Pillar 1 commands produce expected output (Section 2)
- [ ] All Pillar 2 commands produce expected output (Section 3)
- [ ] All Sprint D commands produce expected output (Section 4) — **highest weight; brand new code**
- [ ] Pillar 3 practice + Story Bank works (Section 5) — bank CRUD + interview prep bridge verified
- [ ] Pillar 4 commands run (Section 6)
- [ ] Admin commands produce output (Section 7)
- [ ] Cross-cutting regression OK (Section 8)
- [ ] No surprise blockers beyond the documented limitations (Section 9)

When all above sections pass + 4 operational-debt items closed (PyPI v0.4.0 upload, watchlist UX demotion docs, Layer 4 cron deployment, manual QA pass itself), **v1 is ready for public GitHub release**.

---

## Run-time estimate by section

| Section | Time |
|---|---|
| 0 — Pre-flight | 5 min |
| 1 — Smoke tests | 5 min |
| 2 — Pillar 1 (incl. brand-color 2.8a-2.8e) | 20-25 min |
| 3 — Pillar 2 | 10-15 min |
| 4 — Sprint D | 15-20 min |
| 5 — Pillar 3 + Story Bank (5.1-5.11) | 8 min |
| 6 — Pillar 4 | 3 min |
| 7 — Admin | 5 min (optional) |
| 8 — Regression | 5 min |
| **Total (sum of row ranges)** | **~76-91 min** |
| **With buffer for re-runs / debugging** | **~75-95 min** |
