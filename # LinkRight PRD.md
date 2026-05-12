# LinkRight Resume Engine PRD — v1.0

> **Period:** 2026-05-11 → 2026-06-22 (6 weeks, 5 sprints — Sprint 5 is extended roadmap)
> **Owner:** Satvik Jain (PM, solo)
> **Drives:** spec-driven coding sprint with TDD, subagent dispatch, graphify-refresh, and end-user manual QA gate
> **Source-of-truth references:** `# FlowCV Tips.md` (Parts 2-7) · `# LinkRight Rules.md` · 2026-05-11 stranger QA walkthrough (22 findings)

---

## 1. Vision & Goals

### 1.1 Three anchor goals (verbatim from Satvik 2026-05-11)

1. **World-class 1-page resume** — every shipped resume passes a stranger-mode QA walkthrough
2. **End-to-end bullet width formatting** — every bullet renders at exactly one rendered line, within the 108-120 char / 96-101 CU band
3. **Optimize tokens and prompts per run** — pre-store more deterministic lookups; reduce per-run LLM round-trips

### 1.2 Out of scope this PRD

- Photo handling in resumes (REJECTED — deferred to a future LinkedIn pillar workstream)
- Pillars 2-4 deep implementation (jobsearch, interview, content)
- Marketing, distribution, GTM
- Backend website pipeline (`repo/website/`)
- Multi-page resume support
- Non-English resume support

---

## 2. Success Metrics (top-line, measurable, end-of-month gate)

| # | Metric | Baseline (2026-05-11) | Target (2026-06-08) | Source |
|---|---|---|---|---|
| 2.1 | Tokens per tailor run | 19,488 | **<13,000 (-33%)** | telemetry `16_telemetry.json` |
| 2.2 | P0-bug count from QA | 4 | **0** | manual QA §11 |
| 2.3 | JD-coverage % surfaced in success box | not shipped | **shipped** | binary check |
| 2.4 | Width hit-rate per resume | 11.11% (1/9) | **>80% (8/10)** | scorecard.py width-band metric |
| 2.5 | Manual QA checklist pass rate | unknown | **≥95%** | §11 next walkthrough |
| 2.6 | Page-fit utilization band | variable | **85-92% on every shipped resume** | scorecard.py:_s_page_fit |
| 2.7 | Bullet ranking Kendall tau (run-to-run consistency) | ~0.6-0.7 (estimated) | **>0.95** | Sprint 5 — S5.1 embedding alignment |
| 2.8 | Cache hit rate (iterative re-runs) | 0% (no cache) | **>25%** | Sprint 5 — S5.2 caching |
| 2.9 | Fabrication guard false-negative rate | unknown (measure Phase 0) | **<2%** | Sprint 5 — S5.7 fine-tuned guard |

**Failure modes:** any metric below target = the corresponding sprint slips into a follow-up PRD. Token-savings (2.1) is the hardest target — depends on Sprints 2 + 3 landing fully.

---

## 3. Section Definitions (canonical — used by profile-creation step to route entries)

These definitions resolve the "Courses vs Certificates" type ambiguity Satvik raised. Each entry parsed during profile creation gets routed to exactly one section per these rules.

| § | Section | Definition | Examples | Counter-example |
|---|---|---|---|---|
| 3.1 | **Professional Experience** | Paid work with formal company affiliation. Full-time, part-time, contract, internship paid roles. | "Senior PM at American Express, Mar 2024–Present" | A 3-month unpaid open-source contribution → goes to Projects |
| 3.2 | **Projects** | Independent or non-traditional work — open-source, freelance, pro-bono, hackathon, side projects, ContentStack-style consulting bursts. Per Satvik 2026-04-22 routing rule. | "Sukha — open-source mindfulness CLI tool" or "ContentStack consulting engagement" | A permanent contract role → Professional Experience |
| 3.3 | **Education** | Formal degree-granting academic credentials only. | "B.Tech CSE, IIT Delhi, 2018-2022" | A 6-month bootcamp → Courses |
| 3.4 | **Courses** | Completed structured learning programs that don't grant a credential on their own. Coursera, edX, Udacity nanodegrees, internal corporate training. | "Coursera Machine Learning Specialization (Andrew Ng), 2023" | A vendor-issued certification with exam → Certificates |
| 3.5 | **Certificates** | Credential issued by an authority, typically exam-tested or skill-attested. Vendor-specific qualifications. | "AWS Certified Solutions Architect", "PMP", "CFA Level II", "Google Cloud Professional Data Engineer" | A YouTube tutorial completion → not a certificate, skip |
| 3.6 | **Awards & Recognitions** | Competitive wins, ranked achievements, talent-program nominations, company-wide MVP-style accolades. Include rank + total contestants when possible (per FlowCV §Awards). | "Talent Program Top 25 of 1,200 across APAC" | A participation token → skip |
| 3.7 | **Organisations** | Affiliations or memberships in professional bodies, NOT employment. | "Member, Product Management Institute (PMI)" | A paid contract role → Professional Experience |
| 3.8 | **Publications** | Papers, articles, books, or substantial published content. Co-authors listed. | "Co-author, 'AML Risk Engine at 100M+ scale', AmEx Tech Blog, 2024" | A LinkedIn post → skip unless career-defining |
| 3.9 | **References** | Endorsers willing to speak for the candidate. Today's default: implicit "available on request" (not rendered). | "Manager at Sprinklr" (only if asked) | Anyone the candidate hasn't briefed → don't list |
| 3.10 | **Interests** | Personal interests reflecting personality. Below experience + education. | "Long-distance running, classical Indian music, chess" | "Meeting friends" → too generic, skip |
| 3.11 | **Languages** | Spoken/written languages + fluency level (test result OR experiential proof). | "English (Native, IELTS 8.5), Hindi (Native), German (B1, lived 1 year in Berlin)" | "Familiar with X" → too vague |

**Profile-creation step impact:** each definition above triggers a different prompt template at `linkright profile create` time. Routing accuracy is one of the scorecard metrics added in §8.5.

---

## 4. Idea Tracker (full audit reconciliation — nothing lost)

**Sprint 1 progress as of 2026-05-11 evening (end of session 1):** 3 of 12 items 🟢 DONE → v0.5.12, v0.5.14, v0.5.15 live on PyPI. 1 critical hotfix shipped (v0.5.16) for regression caught by end-user verification. 9 remaining Sprint 1 items + S1.12 → next session's dispatch queue.

**Status legend:** 🟢 IMPLEMENTED · 🟡 PLANNED-this-PRD · 🔵 DEFERRED · 🔴 REJECTED

### 4.1 From FlowCV Tips Part 4 — 5 enforcement gaps

| Idea | Status | Reason | Revisit |
|---|---|---|---|
| Personal-details photo policy | 🔴 REJECTED for resume | LinkRight resumes are text-only by design | LinkedIn pillar workstream (future) |
| Professional email format check | 🟢 IMPLEMENTED (PR #128 v0.7.0) | Part of personal-details verification at pipeline start | — |
| No FB/IG inclusion | 🟢 IMPLEMENTED | Implicit by parse contract — not extracted at all | — |
| GPA gating ("only if asked or above-average") | 🔵 DEFERRED | Low impact; most users self-curate. Re-eval if QA finds it | Next PRD |
| "Present" date handling | 🔵 DEFERRED | Low impact; pipeline passes "Present" string through correctly today | Next PRD |
| Past/present tense validator | 🔵 DEFERRED | Stylistic only, not disqualifying. All bullets currently past-tense | Next PRD |
| Section-order flexibility CLI flag | 🔵 DEFERRED | Power-user feature, no signal of demand | When user requests |

### 4.2 From FlowCV Tips Part 6 — 10 subliminal-signal recommendations

| # | Recommendation | Status | Expected behavior + success metric |
|---|---|---|---|
| 6.1 | Company-prestige tier weighting in BRS | 🔵 DEFERRED | Heavy data-curation; revisit Q3 |
| 6.2 | Peer-vs-applicant phrase bank (JD-seniority keyed) | 🟢 IMPLEMENTED (PR #136 v0.8.0) | `peer_applicant_bank.yaml` 86 entries, 3 seniority bands; injected into step_10 system prompt |
| 6.3 | Controlled-uncertainty framing for gappy nuggets | 🔵 DEFERRED | Needs phrasing research |
| 6.4 | Career-level vocab profile (exec/mid/entry tone) | 🟢 IMPLEMENTED (PR #135 v0.8.0) | 5 career-levels × 3 verb buckets in `career_level_preferences`; authority/credibility/energy injected into step_10 |
| 6.5 | Metric-magnitude consistency enforcement | 🟢 IMPLEMENTED (PR #132 v0.8.0) | `score_metric_consistency()` in metric_magnitude.py; up to 15% BRS penalty for mixed-tier bullets |
| 6.6 | Email-format + LinkedIn-handle quality check | 🟢 IMPLEMENTED (PR #128 v0.7.0) | `check_email_quality()` + `check_linkedin_quality()` in contact_quality.py; step_01b verify gate |
| 6.7 | Signal-weighting matrix (13×5) | 🟢 IMPLEMENTED (PR #130 v0.7.0) | `signal_weights.yaml` 13-signal × 5-career-level multipliers applied in step_11 BRS scoring |
| 6.8 | Show-vs-tell template library | 🔵 DEFERRED | Needs audience-detection model |
| 6.9 | Industry-domain verb taxonomy | 🟢 IMPLEMENTED (PR #125 v0.6.0) | `domain_verbs.yaml` prefix maps; deterministic verb substitution eliminates LLM retry loops |
| 6.10 | Cluster-aware JD requirement matching | 🟢 IMPLEMENTED (PR #129 v0.7.0) | `jd_cluster.py` cosine-similarity grouping; `covered_clusters` anti-stuffing in step_11 |

### 4.3 From FlowCV Tips Part 7.2 — 10 pre-stored data layer recommendations

| # | Pre-stored Layer | Status | Sprint |
|---|---|---|---|
| 7.2.1 | Acronym expansion bank (~250 × 12 domains) | 🟢 IMPLEMENTED | PR #124 v0.6.0 — 344 entries across 12 domains |
| 7.2.2 | Verb taxonomy (impact × industry) | 🟢 IMPLEMENTED | PR #126 v0.6.0 — 720 entries, 2D impact × industry matrix |
| 7.2.3 | Career-level signal-weighting matrix | 🟢 IMPLEMENTED | PR #130 v0.7.0 — 13 × 5 multipliers in signal_weights.yaml |
| 7.2.4 | Peer-vs-applicant language bank | 🟢 IMPLEMENTED | PR #136 v0.8.0 — 86 entries, 3 seniority bands |
| 7.2.5 | Show-vs-tell template library | 🔵 DEFERRED | — |
| 7.2.6 | Industry-domain verb prefix maps | 🟢 IMPLEMENTED | PR #125 v0.6.0 — deterministic weak-verb replacement |
| 7.2.7 | Width-style profile per career level | 🔵 DEFERRED | — |
| 7.2.8 | JD requirement clustering | 🟢 IMPLEMENTED | PR #129 v0.7.0 — cosine-similarity grouping, anti-stuffing |
| 7.2.9 | Metric magnitude comparables | 🔵 DEFERRED | — |
| 7.2.10 | Bullet signal co-occurrence rules | 🔵 DEFERRED | — |

### 4.4 From LinkRight Rules 🔮 items

| Item | Status | Sprint |
|---|---|---|
| Truth Engine Layer 1 (personal-details verify at start) | 🟢 IMPLEMENTED (PR #128 v0.7.0) | S3.3 |
| Truth Engine Layer 3 (critique step at end) | 🔵 DEFERRED | Next PRD |
| Strategy-review checkpoint at step_07b | 🔵 DEFERRED | Next PRD |

### 4.5 From 2026-05-11 stranger QA — 22 findings

| Finding ID | Severity | Status | Sprint |
|---|---|---|---|
| QA-F1: "0+ years of experience" in summary | ❌ Blocker | 🟢 **DONE** (subsumed by S1.11 PR #110 v0.5.12) | S1.1 (separate scope: full ceiling-rounding rule) |
| QA-F2: Fabrication guard strips real verbs | ❌ Blocker | 🟢 **DONE** (PR #117 v0.5.18) | S1.2 — `_STOPWORDS` verb block; action verbs never flagged |
| QA-F3: Internal step names visible in spinner | ❌ Blocker | 🟢 **DONE** (PR #114 v0.5.17) | S1.3 — human-friendly spinner labels throughout |
| QA-F4: setup --check Groq false-negative | ❌ Blocker | 🟢 **DONE** (PR #119 v0.5.18) | S1.4 — resolves managed .env Groq key correctly |
| QA-F5: Success box path truncation | ⚠️ Friction | 🟢 **DONE** (PR #133 v0.8.0) | S4.5 — two-line filename + path, no mid-word wrap |
| QA-F6: HF Hub warning leak | ⚠️ Friction | 🟢 **DONE** (PR #120 v0.5.19) | S1.7 — HF Hub + tokenizers warning suppressed |
| QA-F7a: Trailing ",." punctuation | ⚠️ Friction | 🟢 **DONE** (PR #115 v0.5.17) | S1.6 — trailing punctuation residues stripped |
| QA-F7b: "at 50" dangling number | ⚠️ Friction | 🔵 DEFERRED | symptom of F2 fix; re-test |
| QA-F7c: Grammar break ("conducting usability along by leveraging") | ⚠️ Friction | 🔵 DEFERRED | LLM-glitch; re-test post-fixes |
| QA-F7d: "Gen-artificial intelligence" expansion | ❌ Blocker | 🟢 **DONE** (PR #118 v0.5.19) | S1.5 — GenAI/LLM/RAG protected from expansion |
| QA-F8: Duplicate bullets for same nugget | ⚠️ Friction | 🔵 DEFERRED | de-dup pass needs work |
| QA-F9: Coverage 25% not surfaced | ⚠️ Friction | 🟢 **DONE** (PR #134 v0.8.0) | S4.4 — success box shows JD coverage % + width hit-rate |
| QA-F10: tldr duplicate of no-args | ⚠️ Friction | 🔵 DEFERRED | low impact |
| QA-Good × 3 (doctor, stories empty state, auth status) | 🟢 IMPLEMENTED | — | |
| QA-Excellent × 4 (update, spinner UX, cache hit msg, doctor flow) | 🟢 IMPLEMENTED | — | |

### 4.6 From 2026-05-11 design-polish request (Satvik mid-PRD additions)

| Idea | Status | Reason | Sprint / Revisit |
|---|---|---|---|
| CLI terminal UI consistency (Claude-Code-style patterns + LinkRight palette) | 🟢 IMPLEMENTED (PR #121 v0.5.21) | High visible-quality lever — first-impression polish unlocks trust. | Sprint 1 — S1.8 |
| LinkRight mascot character (sprite / ASCII art for welcome banner, like Claude Code's blob) | 🔵 DEFERRED | Branding asset — needs design exploration, not blocking. Will live in `linkright/ui/mascot.py` future. | Q3 2026 or post-v1 release |
| Markdown profile ingestion + privacy gate (long-doc career narratives → nuggets) | 🟢 IMPLEMENTED (PR #131 v0.7.0) | Chunked LLM, Jaccard dedup, privacy gate. Surfaces Sukha/ContentStack/Navii from satvik_jain_career_profile.md as Projects. | Sprint 3 — S3.4 |

### 4.7 From 2026-05-11 first end-to-end test run (Satvik's resume + Anthropic Claude Code JD)

Real bugs surfaced by running pipeline against canonical resume. All items are 🟡 PLANNED in Sprint 1 (extended from 8 → 12 items). Root causes investigated, not just symptoms.

| Bug observed | Root cause | Sprint 1 item | Severity |
|---|---|---|---|
| Summary "0+ years of experience" | step_07 total_years calc broken (returned 0.0) + LLM narrowed years to JD-skill specifics | S1.1 (expanded scope: total_years calc + summary-uses-total-years rule) | P0 |
| Locations "New York, USA" for AmEx + Sprinklr (Satvik only worked from Gurugram) | step_01 parse contract does NOT extract `location` field → step_07 LLM free-types plausible-sounding location | S1.9 ✅ **DONE PR #111 v0.5.14** — header-context validator | P0 |
| LinkedIn + Portfolio full URLs in header | HTML render uses raw URL text instead of anchor text "LinkedIn"/"Portfolio" | S1.10 ✅ **DONE PR #112 v0.5.15** — anchor-text hyperlinks, no brand color on body anchors | P1 |
| Music project bullet shows "(Year)" literal placeholder | step_01 parser emits `"year": "Year"` literal for projects when PDF text doesn't have year — should be empty | S1.11 ✅ **DONE PR #110 v0.5.12** — `_sanitize_year` at both parse + render layers (education + projects covered) | P0 |
| ~70% page utilization (whitespace below Education) vs 85-92% target | Strategy (`_BULLET_BUDGETS`) too conservative for mid-level rich career profile; projects budget=0 dropped 2 of 3 source projects; no page-fit EXPAND-mode | S1.12 ✅ **DONE PR #122 v0.5.22** — EXPAND mode added to page-fit loop | P0 |
| Bullets truncated mid-sentence ("at.", "&.", ", 3.") | step_12 condense over-truncating at width limit, leaving orphan words + S1.6 trailing-punctuation symptom | S1.6 ✅ **DONE PR #115 v0.5.17** — trailing punctuation residues stripped | P0 |
| Sukha / ContentStack / Navii missing from resume | Source PDF (Satvik-Jain-Resume.pdf) does NOT list these — they're in `satvik_jain_career_profile.md` only | S3.4 (markdown ingestion) — will surface them as Projects per `project_satvik_resume_classification.md` routing rule | Deferred to S3.4 |
| Music project bullet content tautology ("Co-creating with AI") | Source nugget thin — step_01 captured only "Co-creating with AI" as key_achievement; needs enrichment | S3.4 (markdown ingestion enriches sparse nuggets) | Deferred to S3.4 |

### 4.8 Session 1 outcomes + new discoveries (2026-05-11)

Session 1 ran 6 PR cycles end-to-end (PRD → bd issue → designer-developer ↔ adversarial-reviewer ↔ QA loop → merge → cli-publish → PyPI). Workflow proven. Key outcomes:

| Item | Outcome |
|---|---|
| S1.9 Location truth | ✅ PR #111 → v0.5.14 |
| S1.10 Hyperlinks | ✅ PR #112 → v0.5.15 (initial), brand-spec fix in iter 2 |
| S1.11 Year placeholder | ✅ PR #110 → v0.5.12 |
| **NEW — PR #109 templates fix** | ✅ MERGED v0.5.13 — bundles HTML templates in wheel (was crashing every pipx user) |
| **NEW — PR #113 PKG-1 hotfix** | ✅ MERGED v0.5.16 — restored PR #109's `package-data` after it was reverted by PR #112's rebase. Caught by B1 end-user verification. |
| **NEW — PR #100 (external)** | ✅ MERGED — Tejas (@kekius-maximus45) profile-derived gap-detection sentinels. Closed Issue #91. No version bump (Tejas correctly put entry under `[Unreleased]`; ships at next bump). |
| **NEW — repo-strict-division clarified** | linkright_production = canonical CLI repo (has cli-publish workflow on `context/cli/linkright/`). sync-resume-engine = website + worker + truss + extension. Never delete sync-resume-engine; never put CLI PRs there. See memory `feedback_repo_strict_division.md`. |

**Process learnings (added to memories):**

1. **Verify before celebrate** — end-user `linkright resume tailor` verification caught a CRITICAL regression (templates dropped during rebase) that 4 reviewer rounds missed. Never claim "users unblocked" without running the published artifact against a real input. Memory: `feedback_verify_before_celebrate.md`.
2. **Edit-tool race** — Edit tool reported success but file unchanged twice this session. Workaround: use `sed` for non-trivial Python file mutations OR verify with `cat` + `git diff --staged` before commit. Memory: `feedback_edit_verify_before_commit.md`.
3. **Pipx vs pyenv editable** — when CLI ships via pipx AND has a `pip install -e` editable in any pyenv-managed Python, PATH ordering causes pyenv to win silently. End-user import errors result. Always uninstall editable dev-installs before relying on pipx version. Memory: `feedback_pipx_pyenv_conflict.md`.
4. **Socratic review style** — Satvik's PR #100 review (3 open-ended questions + pattern-prompts + "subtlest one" tagging) drove Tejas to apply principles, not patches. Worth replicating for future external-contributor reviews. Memory: `feedback_socratic_review_style.md`.
5. **Reviewer-block cadence** — design-litigation reviews 15-30 min; rebase-integrity reviews 1-3 min. Lean focused-scope when scope is mechanical.

**Sprint 1 all done — remaining items shipped in session 2 (2026-05-11):**

| Item | Outcome |
|---|---|
| S1.1 Experience rounding | ✅ PR #116 → v0.5.18 |
| S1.2 Fabrication guard verbs | ✅ PR #117 → v0.5.18 |
| S1.3 Spinner labels | ✅ PR #114 → v0.5.17 |
| S1.4 Groq false-negative | ✅ PR #119 → v0.5.18 |
| S1.5 Gen-AI acronym | ✅ PR #118 → v0.5.19 |
| S1.6 Trailing punctuation | ✅ PR #115 → v0.5.17 |
| S1.7 HF Hub warning | ✅ PR #120 → v0.5.19 |
| S1.8 CLI terminal UI | ✅ PR #121 → v0.5.21 |
| S1.12 Page-fit expand | ✅ PR #122 → v0.5.22 |
| Worker S1.2 sync (lr-w75) | ✅ sync-resume-engine PR #34 — jd_keyphrase.py verb block |

**Sprint 2 outcomes (session 2, v0.6.0):**

| Item | Outcome |
|---|---|
| S2.1 Acronym expansion bank (344 entries, 12 domains) | ✅ PR #124 → v0.6.0 |
| S2.2 Industry-domain verb prefix maps | ✅ PR #125 → v0.6.0 |
| S2.3 Verb taxonomy (720 entries, impact × industry 2D) | ✅ PR #126 → v0.6.0 |
| Fragment-based CHANGELOG infra | ✅ PR #123 → no version bump (infra only) |

**Sprint 3 outcomes (session 2, v0.7.0):**

| Item | Outcome |
|---|---|
| S3.3 Truth Engine Layer 1 — personal-details verify | ✅ PR #128 → v0.7.0 |
| S3.2 JD requirement clustering | ✅ PR #129 → v0.7.0 |
| S3.1 Signal-weighting matrix (13 × 5) | ✅ PR #130 → v0.7.0 |
| S3.4 Markdown profile ingestion + privacy gate | ✅ PR #131 → v0.7.0 |

**Sprint 4 outcomes (session 2, v0.8.0):**

| Item | Outcome |
|---|---|
| S4.3 Metric-magnitude consistency enforcement | ✅ PR #132 → v0.8.0 |
| S4.5 Success box path wrap fix | ✅ PR #133 → v0.8.0 |
| S4.4 JD coverage % + width hit-rate in success box | ✅ PR #134 → v0.8.0 |
| S4.2 Career-level vocab profile | ✅ PR #135 → v0.8.0 |
| S4.1 Peer-vs-applicant language bank | ✅ PR #136 → v0.8.0 |

**No idea silently dropped.** Every audit row above has explicit status + revisit-date.

### 4.9 From 2026-05-11 local-model + quality prioritisation analysis (12 hypotheses)

Weighted prioritisation matrix run 2026-05-11 across 12 hypotheses. Scoring: Quality (0-40) × Speed (0-25, runtime-blocking vs. background-adjusted) × Cost (0-15) × Effort-inverse (0-20) = 100 pts max. Priority order: quality >> speed > cost. Speed score capped at 15 for background-eligible tasks (user doesn't feel the latency).

| Hypothesis | Score | Status | Sprint | Reason |
|---|---|---|---|---|
| H1 — Embedding-based JD-bullet alignment (step_11, nomic-embed-text) | 78/100 | 🟡 PLANNED | S5.1 | Zero fine-tune; Oracle embed already exists; solves run-variance + semantic mismatch |
| H2 — RAG for step_10 (few-shot from history) | 66/100 | 🔵 DEFERRED | Post 500 runs | Cold-start kills early value. Revisit when >500 tailor-run history available. |
| H3 — Fine-tuned fabrication guard (gemma3:1b, asymmetric loss) | 83/100 | 🟡 PLANNED | S5.7 | Highest quality score; addresses catastrophic risk (P1). Data collection must start NOW (parallel with Sprints 1-4). |
| H4 — Adaptive bullet reranking (generate 3, pick best, async) | 61/100 | 🔵 DEFERRED | After H3 ships | Cost-negative. H3 already gives weak bullets a second attempt via fabrication-guard retry. Overlap. Revisit post-S5.7. |
| H5 — Fine-tuned resume extraction India-specific (step_02) | 49/100 | 🔴 REJECTED | — | Data collection dependency too long (need 200+ Indian resumes; have 5). Prompt improvement achieves 80% of gain with zero training effort. Re-evaluate if extraction accuracy measured below 90%. |
| H6 — JD keyword contamination prompt fix | 60/100 | 🟡 PLANNED | S5.3 | Bug-fix scope only (0.5 day prompt change). Fine-tune rejected; prompt fix handles 100% of contamination structurally. |
| H7 — Progressive validation gate (early regen on BRS-weak bullets) | 68/100 | 🟡 PLANNED | S5.5 | 1-2 day orchestration change; prevents distortion of weak bullets; quality + speed both improve |
| H8 — Career level classification → pure deterministic | 59/100 | 🟡 PLANNED | S5.4 | 0.5 day cleanup; removes LLM call from deterministic-by-rules task; eliminates run variance |
| H9 — Background JD pre-processing pipeline | 48/100 | 🔴 REJECTED | — | Zero quality benefit. Speed gain real but S5.2 caching solves the same runtime problem without async infra overhead. Reject. |
| H10 — Cross-bullet verb coherence enforcer (Oracle local) | 68/100 | 🟡 PLANNED | S5.6 | Local Oracle gemma3:1b (no API); 2-3 days; recruiter-visible quality signal; no fine-tuning needed |
| H11 — Prompt compression / context pruning for step_10 | 62/100 | 🔵 DEFERRED | When billing matters | Quality risk if context stripped incorrectly. Revisit when token cost is real constraint (user-base growth, API billing pressure). |
| H12 — Request-level output caching | 72/100 | 🟡 PLANNED | S5.2 | 3-4 days; most underrated win; 0 quality tradeoff; 100% token savings for iterative runs; cache hit rate must be verified ≥25% (Phase 0 instrumentation first) |

**⚠️ Critical parallel action:** H3 (S5.7) requires 3 weeks total including data collection. Step_10b instrumentation to collect `(bullet, source_excerpt, guard_decision)` triplets must start in Sprint 1 — running passively in background while Sprints 1-4 execute. Without this, S5.7 cannot start until weeks after Sprint 5 begins.

---

## 5. Experience Years Rule (NEW — supersedes "0+ years" bug fix)

### 5.1 Logic

```
import math

def years_to_display(total_years: float, career_level: str) -> str | None:
    """
    Returns the string to substitute into the summary template,
    or None to drop the 'X years of experience' phrase entirely.
    """
    if career_level == "fresher" or total_years < 1.0:
        return None  # drop the phrase
    
    rounded = max(1, math.ceil(total_years))
    return f"{rounded}+ years"
```

### 5.2 Edge cases

| Input total_years | career_level | Output | Reason |
|---|---|---|---|
| 3.5 | mid | "4+ years" | ceiling 3.5 → 4 |
| 4.7 | mid | "5+ years" | ceiling 4.7 → 5 (adjacent-band capture for "5-7 years" postings) |
| 0.7 | entry | "1+ years" | non-fresher floor at 1 |
| 0.2 | entry | None | fresher path: drop phrase |
| 0.0 (current bug) | fresher | None | fresher path: drop phrase |
| 8.3 | senior | "9+ years" | ceiling |
| 12.0 | executive | "12+ years" | already integer, ceiling = same |

### 5.3 Rationale

Don't miss adjacent year-band opportunities. A "5-7 years" job posting will filter out a literal "4 years" claim. Rounding up to 5 (when actual is 4.7) keeps the candidate in the consideration set without claiming false experience.

For freshers, the "0+ years" phrasing is harmful — better to omit the years claim entirely and let other parts of the resume signal value.

### 5.4 Files touched

- `resume/orchestrator.py` step_07 (`career_summary` template rendering)
- `resume/orchestrator.py` step_09 (`step_09_summary` text generation)
- `resume/lib/prompts.py:150, 175-181` (career_level bucket comment update)
- New helper module: `resume/lib/experience.py` (`years_to_display()` function)
- Tests: `tests/test_experience_years.py` (7 test cases per §5.2 table)

---

## 6. 5-Sprint Roadmap (6 weeks, 31 items)

### Sprint 1 — Bug-fix sprint + UI foundation ✅ COMPLETE (v0.5.12–v0.5.24)

| ID | Title | Priority | Effort | Outcome |
|---|---|---|---|---|
| ✅ S1.1 | Experience rounding rule + fresher-drop + total_years calc fix | P0 | M | PR #116 v0.5.18 |
| ✅ S1.2 | Fix step_10b fabrication guard stripping real verbs | P0 | M | PR #117 v0.5.18 |
| ✅ S1.3 | Hide internal step names in spinner labels | P0 | S | PR #114 v0.5.17 |
| ✅ S1.4 | Fix `setup --check` Groq false-negative | P0 | S | PR #119 v0.5.18 |
| ✅ S1.5 | Fix Gen-AI acronym expansion error | P0 | S | PR #118 v0.5.19 |
| ✅ S1.6 | Strip trailing ",." double-punctuation + orphan-word truncation | P0 | M | PR #115 v0.5.17 |
| ✅ S1.7 | Suppress HF Hub warning leak in setup --check | P1 | S | PR #120 v0.5.19 |
| ✅ S1.8 | CLI Terminal UI consistency (Claude-Code-style patterns + LinkRight palette) | P0 | M | PR #121 v0.5.21 |
| ✅ S1.9 | Location-fact truth-engine guard | P0 | M | PR #111 v0.5.14 |
| ✅ S1.10 | LinkedIn/Portfolio as hyperlinks | P1 | S | PR #112 v0.5.15 |
| ✅ S1.11 | Year placeholder bug | P0 | S | PR #110 v0.5.12 |
| ✅ S1.12 | Strategy whitespace under-utilization — page-fit expand-mode | P0 | L | PR #122 v0.5.22 |

### Sprint 2 — Token-cost foundations ✅ COMPLETE (v0.6.0)

| ID | Title | Priority | Effort | Outcome |
|---|---|---|---|---|
| ✅ S2.1 | Acronym expansion bank (344 entries × 12 domains) | P1 | M | PR #124 v0.6.0 |
| ✅ S2.2 | Industry-domain verb prefix maps | P1 | M | PR #125 v0.6.0 |
| ✅ S2.3 | Verb taxonomy (720 entries, impact-cat × industry) | P1 | L | PR #126 v0.6.0 |

### Sprint 3 — Subliminal + truth + long-doc ingest ✅ COMPLETE (v0.7.0)

| ID | Title | Priority | Effort | Outcome |
|---|---|---|---|---|
| ✅ S3.1 | Signal-weighting matrix (13 × 5) | P1 | M | PR #130 v0.7.0 |
| ✅ S3.2 | JD requirement clustering (8-15 clusters per JD) | P1 | M | PR #129 v0.7.0 |
| ✅ S3.3 | Truth Engine Layer 1 — personal-details verify at start | P1 | M | PR #128 v0.7.0 |
| ✅ S3.4 | Markdown profile ingestion + privacy gate | P1 | M | PR #131 v0.7.0 |

### Sprint 4 — Subliminal polish + UX ✅ COMPLETE (v0.8.0)

| ID | Title | Priority | Effort | Outcome |
|---|---|---|---|---|
| ✅ S4.1 | Peer-vs-applicant language bank | P2 | M | PR #136 v0.8.0 |
| ✅ S4.2 | Career-level vocab profile | P2 | M | PR #135 v0.8.0 |
| ✅ S4.3 | Metric-magnitude consistency enforcement | P2 | S | PR #132 v0.8.0 |
| ✅ S4.4 | Surface JD coverage % + width-hit-rate in success box | P2 | S | PR #134 v0.8.0 |
| ✅ S4.5 | Fix success box path wrap | P2 | S | PR #133 v0.8.0 |

### Sprint 5 — Local-model quality + pipeline optimization (Week of 2026-06-08, 8 items)

> **Extended roadmap.** Sprint 5 items are lower-urgency than Sprints 1-4 but deliver compounding quality + efficiency gains. S5.7 has the highest quality score (83/100) but longest lead time — data collection must begin in Sprint 1.

| ID | Title | Priority | Score | Effort | Source | Subagent |
|---|---|---|---|---|---|---|
| ✅ S5.0 | CLI pre-flight dependency guards (profile + LLM key + tailor-run + PDF readability) | P0 | —/100 | S | PRs #146 + #147 v0.9.x | caveman:cavecrew-builder |
| S5.1 | Embedding-based JD-bullet alignment (step_11, nomic-embed-text) | P1 | 78/100 | S | H1 — local-model analysis 2026-05-11 | caveman:cavecrew-builder |
| S5.2 | Request-level output caching | P1 | 72/100 | M | H12 — local-model analysis 2026-05-11 | product-owner-qa |
| S5.3 | JD keyword contamination prompt fix | P1 | 60/100 | S | H6 — `feedback_step07_jd_keyword_contamination.md` | caveman:cavecrew-builder |
| S5.4 | Career level classification → pure deterministic | P2 | 59/100 | S | H8 — local-model analysis 2026-05-11 | caveman:cavecrew-builder |
| S5.5 | Progressive validation gate (early regen on BRS-weak bullets) | P1 | 68/100 | S | H7 — local-model analysis 2026-05-11 | designer-developer |
| S5.6 | Cross-bullet verb coherence enforcer (Oracle local gemma3:1b) | P1 | 68/100 | M | H10 — local-model analysis 2026-05-11 | designer-developer |
| S5.7 | Fine-tuned fabrication guard (asymmetric loss, gemma3:1b) | P0 | 83/100 | L+ | H3 — local-model analysis 2026-05-11 | product-owner-qa |

---

## 7. Features + User Stories + AC + Test Cases

Each S-item below uses the same template. Files-touched lists are best-guess; the implementing agent verifies before writing.

### 7.S1.1 — Experience rounding rule + fresher-drop

**Feature description:** Replace the buggy `total_years: 0.0 → "0+ years"` output with a deterministic ceiling-rounding rule. For non-fresher candidates, round actual fractional years up to the next integer (3.5 → 4, 4.7 → 5). For fresher / sub-1-year candidates, drop the entire "X years of experience" phrase from the summary. This avoids both the embarrassing "0+ years" bug and the missed-opportunity problem of being a year shy of a posting's band.

**Acceptance criteria:**
- AC1: No shipped resume contains the string "0+ years" or "0 years"
- AC2: Candidate with `total_years == 3.5` produces summary with "4+ years" (or stronger)
- AC3: Candidate with `total_years == 0.0` produces summary that does NOT contain the years-of-experience phrase
- AC4: Unit test suite covers all 7 edge cases in §5.2

**User story:**
> As a job seeker with 4.7 years of experience applying to a "5-7 years" posting, I want my resume to claim "5+ years" so that the recruiter ATS-filter doesn't auto-reject me.

> As a fresher with no professional experience, I want my resume's summary to NOT claim "0+ years" because that phrasing makes me look unintentionally amateur.

**Test cases:** see §5.2 table — 7 input/output rows.

**Files touched:**
- `resume/lib/experience.py` (new file, `years_to_display()` function)
- `resume/orchestrator.py` step_07 + step_09 (use helper)
- `resume/lib/prompts.py:150, 175-181` (template + comment update)
- `tests/test_experience_years.py` (new)

**Dependencies:** none. Standalone bugfix.

---

### 7.S1.2 — Fix step_10b fabrication guard stripping real verbs

**Feature description:** The current fabrication guard (`resume/lib/metric_extract.py:84-114`) is over-aggressive — it strips real action verbs like "Delivered" out of valid bullets (producing "Complete dashboards in 10 seconds..." instead of "Delivered complete dashboards..."). Tighten the guard so it only strips JD-keywords that are absent from source nuggets, not generic action verbs.

**Acceptance criteria:**
- AC1: Bullet starting with "Delivered" survives the guard when source nugget contains a delivery-related signal
- AC2: Bullet with fabricated JD-keyword "Kubernetes" (not in source) still gets rejected
- AC3: Test corpus regression: pre-fix run produces N broken bullets; post-fix produces 0
- AC4: Real-corpus check on Satvik's Sprinklr + AmEx data shows no verb-stripped bullets

**User story:**
> As a job seeker, I want every bullet on my resume to have an action verb at the start so it reads as professional output, not a half-edited draft.

**Test cases:**
- Input: nugget "Built dashboards delivering 30-day analytics in 10 seconds." + bullet "Delivered complete dashboards in 10 seconds with 30-day analytics."
  → Expected: bullet kept verbatim (verb "Delivered" is action verb, not fabricated JD keyword)
- Input: nugget "Built dashboards." + bullet "Built dashboards using Kubernetes."
  → Expected: bullet rejected ("Kubernetes" not in source)

**Files touched:**
- `resume/lib/metric_extract.py:84-114` (loosen verb-stripping logic)
- `resume/lib/jd_keyphrase.py` (review JD-keyword detection)
- `tests/test_fabrication_guard.py`

**Dependencies:** none. Standalone bug fix.

---

### 7.S1.3 — Hide internal step names in spinner labels

**Feature description:** During `linkright tailor`, the terminal currently flashes internal step names like `step_07_phase_1_2`, `step_09_summary`, `step_14_signal_classify` while spinners are running. Replace these with human-friendly labels.

**Acceptance criteria:**
- AC1: No `step_NN_*` strings visible to end-user in any terminal output
- AC2: Each spinner shows a human-friendly label like "Analyzing job description" or "Writing professional summary"
- AC3: Internal debug logs preserve step names (for developer debugging) — only user-visible output is cleaned

**User story:**
> As a first-time user, I want spinner messages to read like a polite assistant, not like compiler output, so I trust the tool.

**Test cases:**
- Run `linkright resume tailor -r resume.pdf -j jd.md --no-pause`
- grep terminal output for `step_[0-9][0-9]_` → expected 0 matches in user-visible lines
- Internal log file `vision.md` MAY contain step names (developer audit trail)

**Files touched:**
- `resume/orchestrator.py` (search `tokens] step_`, replace label strings)
- `resume/cli.py` (spinner-label registry)

**Dependencies:** none.

---

### 7.S1.4 — Fix `setup --check` Groq false-negative

**Feature description:** `linkright setup --check` currently shows "Groq key: ✗ not set" even when `doctor` shows "22 keys across 7 providers". Root cause: `setup --check` checks for `GROQ_API_KEY` (singular), but keys are stored as `GROQ_API_KEY_1`, `GROQ_API_KEY_2`. Update the check to match the actual env-var pattern.

**Acceptance criteria:**
- AC1: `setup --check` correctly reports Groq key as present when any `GROQ_API_KEY*` env var is set
- AC2: `setup --check` and `doctor` produce consistent verdicts on the same machine
- AC3: All 7 providers (Groq, Cerebras, Cloudflare, Gemini, SambaNova, Z.ai, OpenRouter) use the same numbered-key-pattern check

**User story:**
> As a new user verifying my setup, I want `setup --check` to not contradict `doctor` so I trust the tool's diagnostic output.

**Test cases:**
- Set `GROQ_API_KEY_1=gsk-test` → `setup --check` shows ✓ Groq
- Unset all Groq keys → `setup --check` shows ✗ Groq with "run linkright setup to configure"
- Same input scenarios across all 7 providers

**Files touched:**
- `linkright/setup_wizard.py` (key-presence check)
- `linkright/cli.py: setup` (--check handler)

**Dependencies:** none. Caveman scope.

---

### 7.S1.5 — Fix Gen-AI acronym expansion error

**Feature description:** Acronym-expansion currently produces "Gen-artificial intelligence Assistant" instead of preserving "Gen-AI" verbatim. The bug: the expansion logic treats "Gen" and "AI" as two separate acronyms instead of one proper noun. Pre-store "Gen-AI" (and similar hyphenated proper-noun acronyms) as no-expand entries.

**Acceptance criteria:**
- AC1: Bullet containing "Gen-AI" stays "Gen-AI" through every pipeline step
- AC2: No-expand list also covers other hyphenated proper-noun cases: "AI/ML", "C++", "Node.js", "GenAI" (without hyphen)
- AC3: Pre-existing acronym expansions (AML, KYC, RBAC) still work normally

**User story:**
> As a job seeker in AI/ML, I want product names like "Gen-AI" preserved verbatim because the wrong expansion makes the resume look broken.

**Test cases:**
- Bullet "Improved support by 85% at Sprinklr using Gen-AI Assistant" → preserved verbatim
- Bullet "Architected AML risk engine" → expanded to "Anti-Money Laundering" on first mention, then "AML" thereafter (existing behavior)
- Bullet mentioning "C++" → preserved verbatim

**Files touched:**
- `resume/data/learned_corpus.py` (add no-expand list, OR YAML config)
- `resume/scorecard.py:329` (`_COMMON_KNOWN_ACRONYMS` set — possibly add hyphenated entries)
- `resume/orchestrator.py` (acronym-expansion call site)

**Dependencies:** none.

---

### 7.S1.6 — Strip trailing ",." double-punctuation

**Feature description:** Bullets occasionally render with trailing `,.` (e.g. "Improved usability by 50% via 20+ UX research sessions with compliance analysts/managers at American Express,.") — a punctuation residue from the condense step. Add a final cleanup pass that collapses `,.` → `.` and other obvious punctuation residues.

**Acceptance criteria:**
- AC1: No shipped bullet contains the literal `,.` substring
- AC2: Cleanup also covers `..`, `;;`, ` ,`, ` .`, `,,` patterns
- AC3: Single-period bullet endings preserved unchanged

**User story:**
> As a job seeker, I want every bullet to end with proper punctuation because typos signal low attention to detail.

**Test cases:**
- "Foo bar,." → "Foo bar."
- "Foo bar.." → "Foo bar."
- "Foo bar ." → "Foo bar."
- "Foo bar." → "Foo bar." (no change)

**Files touched:**
- `resume/orchestrator.py` step_14 (final assembly) OR step_15 (PDF render) — pick the latest in pipeline
- `tests/test_punctuation_cleanup.py`

**Dependencies:** none. Caveman scope.

---

### 7.S1.7 — Suppress HF Hub warning leak in `setup --check`

**Feature description:** `setup --check` and embedder-load steps leak a Hugging Face Hub warning ("You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN…") to stdout. Suppress this warning since LinkRight users don't need an HF_TOKEN.

**Acceptance criteria:**
- AC1: No "HF_TOKEN" or "unauthenticated requests" text appears in user-visible output
- AC2: HF Hub still functions (rate-limited at the unauthenticated tier is fine for our usage)
- AC3: Warning suppression is scoped to LinkRight — doesn't affect global Python warnings

**User story:**
> As a new user, I want `setup --check` to look clean so I don't think I need to configure another API key.

**Test cases:**
- Run `linkright setup --check` → grep output for "HF_TOKEN" → expected 0 matches
- Run `linkright profile create` (which loads embedder) → same expectation

**Files touched:**
- `resume/lib/embedder.py` (warnings.filterwarnings before fastembed import)
- OR contextmanager wrapper at embedder-load call sites

**Dependencies:** none. Caveman scope.

---

### 7.S1.8 — CLI Terminal UI consistency (Claude-Code-style patterns + LinkRight palette)

**Feature description:** Establish a canonical CLI terminal UI pattern library for LinkRight, mirroring the polish of Claude Code's CLI (numbered AskUserQuestion-style pickers, tree-indented status output, ● bullet markers, color-coded operation labels, ★ Insight blocks with horizontal rules, italic-grey metadata, "+N lines (ctrl+o to expand)" affordances, time-elapsed progress indicators, etc.) BUT using LinkRight's design-system colors instead of Anthropic's. All future CLI surfaces (`tailor`, `profile`, `setup`, `doctor`, `jobs`, `cl`, `critique`, `practice`, etc.) follow these patterns. Establishes the visual identity before adding more features.

**Acceptance criteria:**
- AC1: New module `resume/lib/cli_theme.py` (or `linkright/ui/theme.py`) exports a single `LR_THEME` Rich theme object + named style aliases for: `brand_primary` (`#4285F4`), `brand_secondary` (`#EA4335`), `metric_positive` (`#34A853`), `metric_negative` (`#EA4335`), `text_primary` (`bright_white`), `text_secondary` (`#5F6368` or `grey50`), `divider` (`#DADCE0` or `grey70`), `warning` (yellow), `success` (`#34A853`), `error` (`#EA4335`), `info` (`#4285F4`)
- AC2: All `Console()` instances across `resume/`, `profile/`, `jobs/`, `setup_wizard.py`, `cli.py` use `Console(theme=LR_THEME)` — no hardcoded ANSI escapes, no inline `style="cyan"` strings
- AC3: New helper module `linkright/ui/patterns.py` exposes 6 reusable rendering primitives:
  - `picker(question, options, header)` → AskUserQuestion-style numbered picker (Image 1 pattern)
  - `status_event(emoji, label, body, allowed_by=None)` → bullet-tree status update (Image 2 pattern)
  - `insight_block(text)` → "★ Insight" with horizontal divider top + bottom (Image 5 pattern)
  - `code_block(content, lang=None)` → green-left-border code panel (Image 2/5 pattern)
  - `progress_indicator(label, elapsed, tokens=None)` → "Waddling… (2m 3s · ↓ 8.6k tokens)" style line (Image 2 pattern)
  - `tree_branch(items)` → `└─` / `├─` style nested indent renderer
- AC4: Welcome banner (Image 4) updated to use LR_THEME — brand-primary for "LINKRIGHT" gradient anchor, brand-secondary for accent rule, divider for separator line, text-secondary for "Your local-first career OS · $0 to run" subline
- AC5: `linkright doctor`, `linkright setup --check`, `linkright tailor` success box, `linkright stories list`, `linkright auth status` — all re-rendered to use `status_event()` + tree-branch + ★ insight patterns where applicable
- AC6: Snapshot tests (`tests/test_cli_ui_snapshot.py`) lock the rendered output for each surface — future PRs that touch UI must update snapshots intentionally

**User stories:**

> US-S1.8.a — As a first-time user, I want LinkRight CLI to feel as polished as Claude Code (tight tree-indented output, clear color hierarchy, sensible whitespace) because that polish signals trustworthy software at first impression.

> US-S1.8.b — As a power user running multiple LinkRight commands, I want a consistent visual language across `tailor`, `profile`, `jobs`, `cl`, `critique` so I can scan output quickly without re-learning each command's idiosyncratic style.

> US-S1.8.c — As a contributor (or future Claude session), I want a single `cli_theme.py` + `patterns.py` module to import from so adding a new CLI surface doesn't require re-deriving the visual language from scratch.

**Test cases:**

| Input scenario | Expected rendering |
|---|---|
| `linkright doctor` (all green) | Each check renders as `● <emoji> <label>: <result>` in `success` style; failing checks switch to `error` style |
| `linkright tailor` mid-run | Spinner line uses `progress_indicator()` showing human-friendly label + elapsed + token-count (NO `step_NN_*` strings — covers S1.3) |
| `linkright tailor` success | Final success box uses `insight_block()` for headline + `tree_branch()` for paths + `status_event()` for next-steps |
| `linkright setup --check` warning case | Issues render as `status_event(emoji="⚠️", label="Groq key", body="...", allowed_by=None)` in `warning` style |
| Output capture via `Console(record=True)` | Snapshot matches stored golden output in `tests/snapshots/` |

**Files touched:**
- `context/cli/linkright/src/linkright/ui/__init__.py` (new package)
- `context/cli/linkright/src/linkright/ui/theme.py` (new — LR_THEME definition)
- `context/cli/linkright/src/linkright/ui/patterns.py` (new — 6 rendering primitives)
- `context/cli/linkright/src/linkright/ui/banner.py` (new — Image 4 banner moved here, themed)
- All existing files that instantiate `Console()` — switch to themed Console:
  - `resume/cli.py`, `resume/orchestrator.py` (success box, checkpoints, spinners)
  - `profile/render.py`, `profile/cli.py`, `profile/pipeline.py`, `profile/enrich.py`
  - `setup_wizard.py`, `cli.py` (root)
  - `jobs/cli.py`, `cover_letter/cli.py`, `critique/cli.py`, `practice/cli.py` (if these exist; verify)
- `tests/test_cli_ui_snapshot.py` (new — snapshot regressions)
- `tests/snapshots/` (new directory with golden output captures)

**Dependencies:** S1.3 (clean spinner labels) — S1.8 patterns absorb the labels rule. Recommended order: S1.3 lands first OR they ship together in one PR since S1.3 is a sub-concern of S1.8.

**LinkRight design-system color reference (from `tools/assemble_html.py:ThemeColors`):**

| Token | Hex | Terminal use |
|---|---|---|
| brand_primary | `#4285F4` | LINKRIGHT banner anchor, info-state, command names, key emphasis |
| brand_secondary | `#EA4335` | error-state, blocker tags, destructive-action warnings |
| metric_positive | `#34A853` | success-state, ✓ marks, value-delivered indicators |
| metric_negative | `#EA4335` | regression markers, value-lost indicators |
| text_primary | bright_white | body output |
| text_secondary | `grey50` / `#5F6368` | italic recap, metadata, "Allowed by auto mode classifier"-style annotations, file paths |
| divider | `grey70` / `#DADCE0` | section dividers, horizontal rules, table-borders |

**Out of scope for this feature (deferred):**
- LinkRight mascot character (sprite/ASCII art) — see §4 deferred items. Will live in `linkright/ui/mascot.py` future.
- Per-pillar color variants — single palette for v1.

---

### 7.S2.1 — Acronym expansion bank (~250 × 12 domains)

**Feature description:** Pre-store a comprehensive acronym expansion bank covering 12 industry domains (tech, cloud, devops, data, AI, security, business, product, healthcare, marketing, HR, finance). Currently expansions are learned per-run from each candidate's resume — wasteful. With the bank pre-loaded, step_14 LLM lookups for known acronyms are eliminated.

**Acceptance criteria:**
- AC1: New file `resume/data/acronyms.yaml` contains ≥250 entries across 12 domain keys
- AC2: Each entry has form `acronym: { expansion: "...", domain: "..." }`
- AC3: First-mention expansion uses the bank lookup; subsequent mentions use bare acronym (existing behavior)
- AC4: Token telemetry shows step_14 LLM calls drop by ≥50% on test corpus
- AC5: Fall-back to `learned_corpus.py` when acronym not in bank (no regression)

**User story:**
> As a system maintainer, I want common-domain acronyms pre-stored so the LLM doesn't waste tokens looking them up every run.

**Test cases:**
- Resume mentions "AML" + "KYC" + "RBAC" — all expand from bank (no LLM call)
- Resume mentions "XQUARK7" (made-up acronym, not in bank) — falls back to learned_corpus.py + LLM lookup
- After 1 LLM-learned expansion, `learned_corpus.py` persists the new entry for next run

**Files touched:**
- `resume/data/acronyms.yaml` (new file, 250+ entries)
- `resume/lib/acronyms.py` (new loader module)
- `resume/orchestrator.py` step_14 (call sites)
- `tests/test_acronyms.py`

**Dependencies:** none. Foundation for S2.2 and S2.3.

---

### 7.S2.2 — Industry-domain verb prefix maps

**Feature description:** Pre-store deterministic verb prefixes per industry domain — Tech → "Architected", PM → "Launched", Sales → "Closed", Finance → "Reconciled", Legal → "Drafted", Marketing → "Drove", etc. Used at step_10 when the LLM produces a bullet with a weak verb — the prefix map provides a deterministic substitution, avoiding the verb-rephrase retry loop that burns tokens today.

**Acceptance criteria:**
- AC1: New file `resume/data/domain_verbs.yaml` with 8 industries × ~12 prefixes each
- AC2: Step_10 verb-retry-loop count drops to <1 per run on test corpus
- AC3: Verb substitution preserves verb tense (always past tense for past roles)
- AC4: Substitution respects the cross-company verb-tracking rule (no reuse)

**User story:**
> As a system maintainer, I want weak verbs (worked, helped) deterministically replaced with domain-appropriate strong verbs so the LLM doesn't have to retry repeatedly.

**Test cases:**
- Bullet "Worked on payment integration at Stripe" (Tech industry) → "Architected payment integration at Stripe"
- Bullet "Worked with marketing on campaigns" (Marketing) → "Drove marketing campaigns" 
- Already-used verb in same resume → pick next-tier alternative, not duplicate

**Files touched:**
- `resume/data/domain_verbs.yaml` (new)
- `resume/lib/domain_verbs.py` (new loader)
- `resume/orchestrator.py` step_10 (verb-substitution call site)
- `tests/test_domain_verbs.py`

**Dependencies:** S2.1 (acronym pattern proven first)

---

### 7.S2.3 — Verb taxonomy (impact-cat × industry, ~640 entries)

**Feature description:** Larger and more nuanced than S2.2 — a 2D matrix of impact-category × industry, where each cell holds ~10 verbs. Impact categories from FlowCV (Achievement, Communication, Initiative, Research, Org/planning, Interpersonal, Leadership, Managing, Problem-solving). Industries from S2.2. Used at step_10 for richer verb diversity across companies.

**Acceptance criteria:**
- AC1: New file `resume/data/verb_taxonomy.yaml` with 8 impact-categories × 8 industries × ~10 verbs ≈ 640 entries
- AC2: Step_10 batched-generation token usage drops 20-30% on test corpus
- AC3: Cross-company verb diversity (unique verbs / total bullets) rises to ≥0.95

**User story:**
> As a system, I want a rich verb library so generated bullets across multiple roles never reuse a verb and always pick an industry-appropriate one.

**Test cases:**
- Tech industry, Achievement category → verbs include "shipped", "architected", "delivered", "deployed"
- Marketing industry, Communication category → verbs include "presented", "pitched", "evangelized"
- Sales industry, Achievement category → "closed", "secured", "won"

**Files touched:**
- `resume/data/verb_taxonomy.yaml` (new, large)
- `resume/lib/verb_taxonomy.py` (new loader + selection logic)
- `resume/orchestrator.py` step_10 + scorecard verb-diversity scoring
- `tests/test_verb_taxonomy.py`

**Dependencies:** S2.2 (domain map established)

---

### 7.S3.1 — Signal-weighting matrix (13 × 5)

**Feature description:** A 13-signal × 5-career-level multiplier matrix. Signals from `_VALID_SIGNALS` (leadership, regulatory-tech, revenue-impact, data-driven, cost-reduction, growth, scale, executive-influence, build-execution, user-empathy, ambiguity-resolution, automation, execution). Career levels from `_CAREER_LEVEL_MIN_YEARS`. Each cell is a multiplier (e.g. exec-level resumes weight `executive-influence` 2x; entry-level weight `build-execution` 2x). Applied at step_11 ranking.

**Acceptance criteria:**
- AC1: New file `resume/data/signal_weights.yaml` with 13 × 5 matrix
- AC2: All multipliers in [0.5, 2.5] range — no signal completely zeroed out
- AC3: Step_11 bullet-rank order shifts demonstrably between career levels (test: same nuggets, different career_level → different top-1/3 bullets)
- AC4: Signal-fit score per career-level rises ≥15% on test corpus

**User story:**
> As an executive job-seeker, I want my resume's executive-influence bullets ranked higher than my early-career build-execution bullets so the top 1/3 reflects my current level.

**Test cases:**
- career_level=executive + 3 bullets (leadership, build-execution, growth) → leadership ranks #1
- career_level=fresher + same 3 bullets → build-execution ranks #1
- career_level=mid + same 3 bullets → growth ranks #1 (mid-tier credibility signal)

**Files touched:**
- `resume/data/signal_weights.yaml` (new)
- `resume/lib/signal_weights.py` (new loader)
- `resume/orchestrator.py: step_11_rank` (apply multiplier)
- `tests/test_signal_weighting.py`

**Dependencies:** none structural.

---

### 7.S3.2 — JD requirement clustering (8-15 clusters/JD)

**Feature description:** Currently every JD requirement (8-15 items per JD) is matched 1:1 to bullets, causing redundancy ("communicate" + "collaboration" + "stakeholder alignment" each get their own bullet). Pre-cluster the JD requirements using embedding cosine similarity (already have embedders), producing 4-7 canonical clusters per JD. Bullet-ranker matches to clusters, not individual items.

**Acceptance criteria:**
- AC1: Step_05/06 produces a `jd_requirement_clusters` array on parsed_p12
- AC2: Each cluster has `cluster_id`, `member_requirement_ids`, `canonical_label`
- AC3: Step_11 ranking algorithm uses cluster_id, not requirement_id, for JD-overlap scoring
- AC4: Step_11 LLM calls drop by ~50% on test corpus (cluster-aware skipping)

**User story:**
> As a job seeker, I don't want my resume to read like keyword stuffing with three bullets all answering "you must communicate well". One strong bullet covering the cluster is better.

**Test cases:**
- JD with "communicate", "collaborate", "stakeholder alignment" → clustered into 1 (canonical_label="stakeholder_communication")
- JD with "Python", "Pandas", "ML pipelines" → clustered into 1 (canonical_label="data_engineering_stack")
- JD with truly distinct requirements ("Python", "Spanish fluency", "AWS") → stays as 3 clusters

**Files touched:**
- `resume/orchestrator.py` step_05/06 (clustering pass)
- `resume/lib/cosine.py` (existing utility, may reuse)
- `resume/orchestrator.py: step_11_rank` (cluster-aware match)
- `tests/test_jd_clustering.py`

**Dependencies:** none. Pure deterministic addition.

---

### 7.S3.3 — Truth Engine Layer 1 — personal-details verify at start

**Feature description:** At pipeline start (after step_01 PDF parse, before step_07 JD pickup), surface the parsed phone / email / LinkedIn / portfolio to the user for confirmation. Includes inline quality checks: professional-email format (firstname.lastname pattern), LinkedIn-handle quality (custom slug preferred over numeric). User can Edit / Skip / Lock each field via questionary.

**Acceptance criteria:**
- AC1: `linkright resume tailor` shows a "Verify your details:" prompt before JD analysis
- AC2: Email check warns on non-professional format (e.g. "abbygirl129@gmail.com") with suggested alternative
- AC3: LinkedIn check warns on default-numeric slug (e.g. "linkedin.com/in/user-1234567")
- AC4: User can Edit each field inline; choice persisted to profile cache
- AC5: Skip-all flag (`--no-pause` / `LR_NO_PAUSE=1`) bypasses the prompt

**User story:**
> As a job seeker, I want to verify and correct my contact details before the rest of the pipeline runs because typos at the top of my resume are the worst typos.

**Test cases:**
- Email "abbygirl129@gmail.com" → warning shown with "firstname.lastname@gmail.com" suggested
- LinkedIn "linkedin.com/in/satvik-jain" → no warning
- LinkedIn "linkedin.com/in/user-1837492" → warning shown
- `--no-pause` set → no prompt, pipeline proceeds with parsed values

**Files touched:**
- `resume/orchestrator.py` (new step_01b)
- `resume/cli.py` (interactive prompt + questionary integration)
- `resume/lib/contact_quality.py` (new module — email + LinkedIn regex checks)
- `tests/test_contact_quality.py`

**Dependencies:** S1.3 (clean spinner labels)

---

### 7.S3.4 — Markdown profile ingestion + privacy gate

**Feature description:** Add a new pathway for ingesting long-form markdown career profiles (like Satvik's `satvik_jain_career_profile.md` — 95KB, 435 lines, diary-style narrative) into LinkRight's nugget store. Today `linkright profile create` strictly takes PDF input. The new `--from-markdown` flag (or `linkright profile enrich --from-document`) parses the markdown by section, gates personal/family-tragedy content behind an opt-in flag, chunks career-relevant paragraphs, runs LLM nugget extraction per chunk (reusing existing `extract_from_answer` prompt), dedups against the existing profile, and persists. Unlocks the rich personal-context data Satvik has already written but cannot use today.

**Acceptance criteria:**
- AC1: New command `linkright profile create --from-markdown <file.md>` accepts a markdown file path; alternate flag `linkright profile enrich --from-document <file.md>` appends to existing profile.
- AC2: Section parsing splits by `## N. <title>` headers. Each section is classified into one of: `career-relevant` / `personal-life` / `mixed` via a deterministic keyword stoplist on title words (e.g. titles containing "family", "tragedy", "early life", "school", "personal" → `personal-life`; titles with "work", "role", "company", "internship", "project" → `career-relevant`).
- AC3: Default behavior skips `personal-life` sections. `--include-personal` flag opts in (for cases where personal context legitimately enriches career narrative, e.g. resilience signals seeded by family tragedy).
- AC4: Within career-relevant sections, paragraph chunking targets 200-400 tokens per chunk (single paragraph or small group). LLM call per chunk extracts 1-N atomic career nuggets in the same JSON shape as `extract_from_answer` output.
- AC5: Dedup pass: new nuggets compared against existing profile via `nugget_key()` (already at `profile/pipeline.py:73`). Duplicates merged, not appended.
- AC6: Embedding step uses same embedder tier as existing profile (per `metadata.yaml`). Tier mismatch refuses run, asks user to rebuild profile.
- AC7: Token budget compliance — per memory `feedback_rate_limit_50pct_ceiling.md`, full run on 95KB markdown stays under 50% of any provider's rate limit (estimated 10-15 LLM calls, 20-30K total tokens, well within Groq free tier).
- AC8: Privacy audit log — after run, print a summary showing which sections were skipped (privacy-gated) vs included. User sees exactly what entered nugget store.
- AC9: Snapshot tests on Satvik's profile.md as golden — known nugget count after first run becomes regression baseline.

**User stories:**

> US-S3.4.a — As a candidate who has already written a long personal career-narrative document (or maintains one in Obsidian), I want LinkRight to ingest that document so my nugget store reflects the depth I've written, not just what fits on my 1-page resume.

> US-S3.4.b — As a candidate whose career-narrative document includes sensitive personal content (family tragedy, mental-health context), I want privacy-by-default — personal sections SKIPPED unless I explicitly opt them in. I should never see those nuggets accidentally land in a resume bullet.

> US-S3.4.c — As a contributor adding a new ingestion source (Notion / Google Doc / Obsidian later), I want the markdown pathway to be the reference implementation — section parsing + privacy gate + chunked LLM extraction as reusable building blocks.

**Test cases:**

| Input | Expected outcome |
|---|---|
| `linkright profile create --from-markdown ~/profile.md` (career-only sections) | Profile created; nugget count matches section-paragraph count × ~1.2 |
| Same file containing `## 1. Early Life, Family, and Tragedy` section | Section SKIPPED by default; audit log notes skip; nuggets only from career sections |
| `--include-personal` flag set | Personal sections also ingested; audit log notes opt-in; user sees confirmation prompt before persistence |
| Existing profile + `linkright profile enrich --from-document <new.md>` | Dedup pass merges; final count = existing + new − duplicates |
| Profile created with embedder=fastembed; ingest md with --embedder=sentence_transformers | Refuses with clear error: "embedder tier mismatch — run `linkright profile rebuild` first" |
| Markdown file >200KB | Auto-chunking splits into 50+ chunks; rate-limit throttle paces calls to ≤50% provider RPM |
| Markdown file with no `## N.` headers | Falls back to single-section ingestion; entire file treated as one career-relevant block |

**Files touched:**
- `context/cli/linkright/src/linkright/profile/markdown_ingest.py` (NEW — section parser + privacy gate + paragraph chunker)
- `context/cli/linkright/src/linkright/profile/pipeline.py` (extend with `ingest_markdown(markdown_path: Path, include_personal: bool=False) -> dict` function)
- `context/cli/linkright/src/linkright/profile/cli.py` (add `--from-markdown` flag to `create` + new `--from-document` flag to `enrich`)
- `context/cli/linkright/src/linkright/profile/enrich.py` (reuse `extract_from_answer` for per-chunk LLM call)
- `context/cli/linkright/src/linkright/resume/lib/prompts.py` (new prompt template for markdown-chunk → nuggets, or reuse EXTRACT_SYSTEM)
- `tests/test_markdown_ingest.py` (NEW — golden tests on Satvik's profile.md)
- `tests/fixtures/sample_career_profile.md` (NEW — small fixture for unit tests)

**Dependencies:** S3.3 (Truth Engine Layer 1) — if personal-details verify is happening at pipeline start, markdown ingest should respect the same verified contact details. Recommended order: S3.3 first, then S3.4.

**Privacy gate — section classification heuristic (default blocklist):**

| Section title contains (case-insensitive) | Classification | Default action |
|---|---|---|
| `family`, `tragedy`, `early life`, `childhood`, `school`, `parents`, `personal`, `mental health`, `relationships`, `dating`, `marriage`, `health` | `personal-life` | SKIP |
| `work`, `role`, `internship`, `job`, `company`, `project`, `engineering`, `product`, `experience`, `achievement`, `award`, `skill`, `tool`, `education`, `degree`, `iit`, `iim`, `university`, `college` | `career-relevant` | INCLUDE |
| Other / ambiguous | `mixed` | ASK USER (interactive prompt) |

**Out of scope for this feature:**
- Ingestion from non-markdown sources (Notion / Google Docs / .docx) — future workstream.
- Two-way sync (push nugget changes back to source markdown) — one-way ingest only.
- Real-time watching / auto-reingest on file change — manual re-run only.

---

### 7.S4.1 — Peer-vs-applicant language bank

**Feature description:** Pre-store a phrase-substitution bank keyed by JD seniority — peer-language (co-led, partnered, aligned with, evangelized) for senior roles, applicant-language (drove, owned, shipped, delivered) for junior roles. Applied at step_10 to adjust bullet tone.

**Acceptance criteria:**
- AC1: New file `resume/data/peer_applicant_bank.yaml` with ≥80 phrase pairs across 3 seniority bands (junior / mid / senior)
- AC2: JD-seniority detected from JD parse (existing `career_level` field)
- AC3: Cross-company verb-similarity score drops by ≥30% on test corpus when peer-language pulled in
- AC4: Substitution respects no-fabrication rule (only changes verb-style, not facts)

**User story:**
> As a senior job-seeker, I want my resume to read as a peer to the hiring panel ("partnered with…", "co-led…") rather than as an applicant pleading for the role ("drove…", "shipped…").

**Test cases:**
- senior JD + nugget "Built dashboards" → "Architected dashboards alongside data-eng partners"
- junior JD + same nugget → "Built dashboards delivering 30-day analytics"
- Substitution preserves all numeric metrics verbatim

**Files touched:**
- `resume/data/peer_applicant_bank.yaml`
- `resume/lib/peer_applicant.py` (new)
- `resume/orchestrator.py` step_10
- `tests/test_peer_applicant.py`

**Dependencies:** S2.3 (verb taxonomy in place)

---

### 7.S4.2 — Career-level vocab profile

**Feature description:** Apply a career-level-specific vocabulary preference at step_10 bullet generation. Executive resumes prefer authority verbs (oversaw, governed, established). Mid-level prefer credibility verbs (drove, optimized, scaled). Entry-level prefer energy verbs (built, shipped, launched).

**Acceptance criteria:**
- AC1: Career-level detected from existing pipeline state
- AC2: Step_10 prompt template injects level-specific verb-preference list
- AC3: Generated bullets show measurable shift in verb-distribution across levels
- AC4: Exec-level resumes have ≥80% authority verbs on scorer

**User story:**
> As an executive, I want my resume to sound executive — not like I'm a builder reporting to my manager.

**Test cases:**
- career_level=executive + nugget "Ran product team" → "Established product-team governance for 80+ engineers"
- career_level=fresher + same nugget → "Built product-team coordination process"

**Files touched:**
- `resume/data/verb_taxonomy.yaml` (extend with career-level filters from S2.3)
- `resume/lib/verb_taxonomy.py` (career-level filter)
- `resume/orchestrator.py` step_10 prompt
- `tests/test_career_level_vocab.py`

**Dependencies:** S2.3, S3.1

---

### 7.S4.3 — Metric-magnitude consistency enforcement

**Feature description:** Within each bullet (and ideally across adjacent bullets), ensure metric magnitudes are consistent. Never put 5% next to $50B in the same bullet — reader anchors on the smaller number, deflating perceived impact. Sort metrics within a bullet by magnitude tier so the largest comes first.

**Acceptance criteria:**
- AC1: New scorer check `_s_metric_consistency` in scorecard.py
- AC2: Bullets with mixed-tier metrics get a penalty in the consistency score
- AC3: Step_11 ranking penalizes inconsistent bullets
- AC4: Zero %-next-to-$B in same bullet on test corpus

**User story:**
> As a job seeker, I want my big numbers to lead because mixing scales hurts impact.

**Test cases:**
- Bullet "Cut churn by 5% saving $50M ARR" → reordered to "Saved $50M ARR by cutting churn 5%"
- Bullet "$1.2M revenue + 40 hrs/wk saved" → kept (different units)
- Bullet "70% improvement at 100M+ accounts" → kept (same direction)

**Files touched:**
- `resume/scorecard.py` (new scorer)
- `resume/orchestrator.py` step_11 (penalty integration)
- `tests/test_metric_consistency.py`

**Dependencies:** none.

---

### 7.S4.4 — Surface JD coverage % + width-hit-rate in success box

**Feature description:** At end of tailor run, the success box shows the PDF path but hides critical quality signals — JD requirement coverage % (e.g. "2/8 reqs, 25%") and width hit-rate (e.g. "1/9 bullets in 108-120 band, 11.11%"). Add these to the success box header before the path.

**Acceptance criteria:**
- AC1: Success box shows "JD coverage: X/Y reqs (Z%)" line
- AC2: Success box shows "Width hits: X/Y bullets (Z%)" line
- AC3: When metrics are below target (coverage <80%, width-hits <80%), the box uses warning color
- AC4: Metrics come from vision.md + scorecard.py existing fields (no new computation)

**User story:**
> As a job seeker, I want to know immediately whether my resume covers the JD requirements before I send it out.

**Test cases:**
- Coverage 2/8 (25%) → red/yellow warning + advice
- Coverage 7/8 (87.5%) → green ✓
- Width-hits 1/9 → red warning

**Files touched:**
- `resume/cli.py` (success-box rendering)
- `resume/orchestrator.py` step_16 (metrics aggregation)
- `tests/test_success_box.py`

**Dependencies:** none.

---

### 7.S4.5 — Fix success box path wrap

**Feature description:** Current success box wraps file paths mid-word — "/Users/satvikjain/.linkright/runs/.../15_final_res|ume.pdf" — breaking the path mid-filename. Fix by showing filename on its own line + full path on a smaller second line.

**Acceptance criteria:**
- AC1: No `<filename>` string ever breaks across lines
- AC2: Box renders cleanly at common terminal widths (80, 100, 120 cols)
- AC3: `open` command shown on its own line, label "Open PDF" on a separate line aligned to the right

**User story:**
> As a user, I want to copy-paste the resume path without dealing with mid-word wraps.

**Test cases:**
- Path with 100+ chars → wraps cleanly between path components, not mid-filename
- Short path → renders on one line
- Path with spaces → quoted properly

**Files touched:**
- `resume/cli.py` (Rich-box rendering)
- `tests/test_success_box_render.py`

**Dependencies:** none. Caveman scope.

---

### 7.S5.1 — Embedding-based JD-bullet alignment

**Feature description:** Replace the current LLM-scored JD-bullet alignment call in step_11 with deterministic cosine-similarity scoring using Oracle's existing `nomic-embed-text` model (already installed and verified per `reference_oracle_ollama.md`). The LLM currently scores "how well does this bullet match this JD requirement" — producing ordinal scores (7/10) that drift across runs and miss semantic equivalence ("drove ARR growth" ↔ "P&L ownership" — identical signal, zero keyword overlap). Cosine similarity between embedded bullet text and embedded JD requirement text is: calibrated (0-1 range), deterministic (same inputs = same output every time), semantically richer, and orders of magnitude faster (2ms local vs. 3-5 sec API call per bullet). This solves Pain #2 (run-to-run ranking variance erodes user trust) and Pain #4 (semantic mismatches in alignment scoring).

**Baseline metrics (measure before implementing — Phase 0):**
- Kendall tau correlation of bullet ranking across 5 independent runs of same resume + JD (estimated ~0.6-0.7)
- Human relevance rating of bullet order (blind eval, 1-5 scale, 10 samples)
- step_11 API call count + latency per resume

**Success metrics:**
- Kendall tau post-implementation: >0.95 (near-deterministic ranking)
- Human preference: >65% prefer embedding-ranked order over prior LLM-ranked (blind A/B, 20 samples)
- step_11 runtime: <50ms total (vs. 3-5 sec per resume)
- API calls for alignment scoring: 0

**Experiment phases:**
```
Phase 0 (1 day): Run 5 test resumes × 3 runs each. Record bullet orders.
                 Compute Kendall tau. Human-rate 10 samples. Record baseline.
Phase 1 (2 days): Wire nomic-embed-text into step_11. Replace LLM alignment call.
Phase 2 (1 day): Re-run Phase 0 tests. Compare Kendall tau + human ratings.
                 Revert if Kendall tau < 0.90 OR human preference < 55%.
```

**Acceptance criteria:**
- AC1: step_11 alignment score = `cosine_similarity(embed(bullet), embed(jd_requirement))` — no LLM call in alignment path
- AC2: For multi-requirement JDs: `score = max(cosine(embed(bullet), embed(req)) for req in jd_requirements)` — best match wins
- AC3: Same resume + same JD → identical bullet ranking across 3 independent runs (Kendall tau >0.95)
- AC4: Oracle embed endpoint verified at step_11 entry — raises `OracleEmbedUnavailable` if not reachable
- AC5: Graceful fallback to LLM scoring if Oracle unreachable — pipeline continues, warning logged; never silent failure

**User story:**
> As a job seeker tailoring the same resume to multiple JDs, I want bullet ordering to be identical every run so I can trust the tool's judgment — not wonder if different runs are producing different results.

**Test cases:**

| Input scenario | Expected outcome |
|---|---|
| "Drove ARR growth 40% YoY" vs JD req "P&L ownership" | High cosine (semantic match, no keyword overlap) |
| "Used Excel for reporting" vs JD req "Python, ML pipelines" | Low cosine (genuine mismatch) |
| Same resume + same JD, 3 runs | Identical bullet order every run (Kendall tau = 1.0) |
| Oracle embed endpoint down | Fallback to LLM scoring; warning in telemetry; pipeline completes |

**Files touched:**
- `resume/orchestrator.py: step_11_rank` (replace LLM alignment call with cosine similarity)
- `resume/lib/embedder.py` (add Oracle nomic-embed-text client, reuse existing embed infra)
- `resume/lib/cosine.py` (cosine similarity utility — create if not exists)
- `tests/test_jd_alignment_embedding.py` (regression + semantic match tests)

**Dependencies:** Oracle nomic-embed-text running (`ollama pull nomic-embed-text` verified). S3.2 JD clustering benefits from this (clusters use same embedding space).

---

### 7.S5.2 — Request-level output caching

**Feature description:** When a user re-runs `linkright resume tailor` on the same resume PDF + same JD text, every LLM call re-executes — burning 13,000-19,000 tokens for identical output. The most common usage pattern is iterative refinement: edit 2 lines in the resume, re-run. A content-addressed cache keyed on `sha256(resume_pdf_bytes + jd_text_bytes + pipeline_version)` returns the previous complete output instantly, eliminating all LLM calls for identical inputs. Cache invalidation is trivial: any byte change in resume OR JD = different hash = automatic cache miss. Pipeline version in the key means a `linkright update` auto-invalidates all stale cache entries (users always get fresh output post-update). Addresses Pain #3 (long runtime) for the most common user pattern.

**Baseline metrics (instrument before implementing — Phase 0):**
- Log `sha256(resume_pdf_bytes + jd_text_bytes)` to step_16 telemetry for 1 week
- Measure: % of runs that share a hash with a prior run (= would-be cache hit rate)
- Current per-run time: 90-120 sec, 13,000-19,000 tokens

**Success metrics:**
- Cache hit rate after 1 week: >25% (proves iterative usage pattern is real — if <10%, deprioritize)
- Cache hit response time: <500ms
- Token savings for cached runs: 100%
- `linkright cache clear` reduces `~/.linkright/cache/` to 0 bytes

**Experiment phases:**
```
Phase 0 (1 day): Add hash logging to step_16 telemetry. Run for 1 week passive.
                 If cache hit rate <10% → deprioritize S5.2. If >25% → proceed.
Phase 1 (3 days): Implement cache. Hash → store complete output dir in
                  ~/.linkright/cache/<hash>/. TTL: 7 days. --no-cache flag.
Phase 2 (1 day): Test invalidation (1 char edit → cache miss → full run).
                 Test cache hit serving correct output.
```

**Acceptance criteria:**
- AC1: Cache key = `sha256(resume_pdf_bytes + jd_text_bytes + __pipeline_version__)` — version-invalidates on any `linkright update`
- AC2: Cache stored at `~/.linkright/cache/<key>/` — contains full output directory (HTML, PDF, vision.md, telemetry JSON)
- AC3: Cache hit shows "Cache hit — returning previous output (saved ~90 sec)" with original-run timestamp
- AC4: `--no-cache` flag bypasses cache for forced re-run
- AC5: `linkright cache clear` command clears all cached runs — shows disk usage before clearing, asks for confirmation
- AC6: Cache entries auto-expire after 7 days (stat-mtime check at hit-time)
- AC7: Phase 0 gate: if measured cache hit rate <10% after 1 week → do NOT implement; file issue to re-evaluate after 3 months

**User story:**
> As a job seeker who iterates on my resume across multiple sessions, I want re-runs on the same inputs to return instantly so I don't burn 90 seconds waiting every time I make a small change.

**Test cases:**

| Input scenario | Expected outcome |
|---|---|
| Run tailor; run again with identical PDF + JD | Cache hit; <500ms; "saved ~90 sec" shown |
| Edit 1 word in resume, re-run | Cache miss (different hash); full pipeline |
| `linkright update` to new version, re-run | Cache miss (pipeline_version changed); full pipeline |
| `--no-cache` flag | Cache bypassed; full pipeline even if cache available |
| Cache entry >7 days old | Cache miss (expired); full run; new cache written |

**Files touched:**
- `resume/lib/cache.py` (new — hash generation, read/write, TTL check, disk usage calc)
- `resume/orchestrator.py` (check cache before step_00; write cache after step_16)
- `resume/cli.py` (add `--no-cache` flag; cache hit message via `insight_block()`)
- `linkright/cli.py` (add `linkright cache clear` subcommand)
- `tests/test_output_cache.py`

**Dependencies:** S1.8 (UI patterns — cache-hit message uses `insight_block()` from `patterns.py`). Phase 0 baseline measurement must confirm >10% hit rate before implementation begins.

---

### 7.S5.3 — JD keyword contamination prompt fix

**Feature description:** step_07's LLM call for JD keyword extraction leaks resume-specific terms (e.g. "AML", "NICE Actimize") into the `jd_keywords` list when those terms appear in the context window alongside the JD text. Contaminated keywords incorrectly inflate JD-alignment scores for bullets that mention these terms — not because the JD requires them, but because the resume already has them. This is a silent ATS-quality bug (Pain #4): the resume appears to match requirements it doesn't actually satisfy. A downstream filter was partially implemented (per `feedback_step07_jd_keyword_contamination.md` — catching 9/58 contaminating terms in testing). This item completes the fix: update the step_07 extraction prompt with explicit negative instruction + add a strict post-extraction filter that structurally eliminates contamination. Fine-tuning rejected (H5 rationale) — prompt fix handles 100% of contamination at 40× lower effort.

**Baseline metrics (measure before fix):**
- Run step_07 on 5 test resume+JD pairs. Manually audit `jd_keywords` — how many are resume-sourced vs. JD-sourced?
- Current contamination rate: ~15% (9/58 in one test run)

**Success metrics:**
- Post-fix contamination rate: 0% (no keyword in `jd_keywords` absent from raw JD text)
- No regression: legitimate JD keywords correctly retained at same rate as before fix

**Acceptance criteria:**
- AC1: step_07 prompt updated with: "Extract ONLY terms from the JD text below. Never include terms that appear only in the candidate's profile or resume."
- AC2: Post-extraction filter: `validated_keywords = {kw for kw in jd_keywords if kw.lower() in jd_raw_text.lower()}` — any keyword not in raw JD text removed
- AC3: Test: resume contains "NICE Actimize"; JD does NOT → "NICE Actimize" NOT in `jd_keywords`
- AC4: Test: JD explicitly requires "NICE Actimize" → correctly retained in `jd_keywords`

**User story:**
> As a job seeker, I want the keywords driving my bullet alignment to come from what the employer actually needs — not from what's already on my resume — because the whole point of tailoring is to fill the gap, not reinforce what I have.

**Test cases:**
- Resume: "AML risk engine, NICE Actimize, KYC"; JD: "Python, SQL, risk analysis" → `jd_keywords` contains zero of {AML, NICE Actimize, KYC}
- Resume mentions "Python"; JD requires "Python" → "Python" correctly IN `jd_keywords`
- JD explicitly mentions "NICE Actimize" (employer uses it) → correctly retained

**Files touched:**
- `resume/orchestrator.py` step_07 (prompt update + post-extraction filter integration)
- `resume/lib/jd_keyphrase.py` (strengthen existing partial filter — full structural fix)
- `tests/test_jd_contamination.py`

**Dependencies:** none. Bug-fix only. Ship as first item in Sprint 5.

---

### 7.S5.4 — Career level classification → pure deterministic

**Feature description:** Career level classification currently invokes an LLM call despite `_CAREER_LEVEL_MIN_YEARS` existing in `resume/orchestrator.py:206` with deterministic year-band thresholds. The LLM override introduces run-to-run variance (sometimes classifying 4.9 years as "mid", sometimes "senior") and burns one API call. This is a cleanup item: remove the LLM call from the career-level path entirely. Trust `_CAREER_LEVEL_MIN_YEARS` exclusively. Makes `years_to_display()` from §5 more reliable (no career_level variance propagating into summary). Pairs with S5.1 — both eliminate unnecessary LLM calls from non-generative tasks.

**Baseline metrics:**
- Run same 5 resumes 3× each; record `career_level` per run — is it always the same? (measure variance)
- API calls for career-level step per resume: 1

**Success metrics:**
- Career level identical across 3 runs of same resume: 100% (0 variance)
- API calls for career-level step: 0
- 5 test resumes → same career_level as human-assigned ground truth

**Acceptance criteria:**
- AC1: `_classify_career_level()` uses ONLY `_CAREER_LEVEL_MIN_YEARS` dict — zero LLM calls in this path
- AC2: Boundary case: `total_years == 5.0` exactly → rounds to lower band (conservative, per §5 rationale)
- AC3: `total_years < 1.0 OR career_level == "fresher"` → always `"fresher"` (per §5)
- AC4: 5 test resumes × 3 runs each → identical classification every run

**User story:**
> As a job seeker, I want the pipeline to classify my experience level identically every run so I'm not getting different resume strategies depending on an LLM's mood.

**Test cases:**
- `total_years = 2.3` → `"entry"` (band 1-3)
- `total_years = 5.0` (boundary) → `"mid"` (lower band, conservative)
- `total_years = 0.8` → `"fresher"`
- `total_years = 10.5` → `"executive"`
- Same inputs × 3 runs → identical output every time

**Files touched:**
- `resume/orchestrator.py:206` (remove LLM call; pure dict lookup via `_CAREER_LEVEL_MIN_YEARS`)
- `tests/test_career_level.py` (determinism test × 3 runs)

**Dependencies:** §5 `years_to_display()`. Ship after S1.1.

---

### 7.S5.5 — Progressive validation gate

**Feature description:** When step_10b (fabrication guard) passes a bullet, the pipeline immediately runs step_12 (width expansion/contraction) regardless of that bullet's underlying quality. Width expansion on a low-BRS bullet distorts the phrasing — the result is a bullet that is simultaneously low-quality AND awkwardly worded. Add a BRS pre-check gate between step_10b exit and step_12 entry: if a bullet's BRS score falls below a configurable threshold (default: 6.0/10), skip step_12, immediately trigger step_10 regeneration (1 additional attempt only). If the regenerated bullet also fails → accept the original but flag in the success box ("2 bullets below quality threshold — consider manual review"). Prevents the pipeline from spending deterministic-step resources polishing bullets that don't deserve it.

**Baseline metrics (Phase 0):**
- % of bullets with BRS < 6.0 after step_10 across 10 test resumes
- Human quality rating (1-5) of BRS<6 bullets in final output (post-width-expansion)
- Mean BRS of all final-output bullets

**Success metrics:**
- Human quality rating for previously-weak bullets: +1.0 on 1-5 scale
- % of final-output bullets with BRS < 6.0: reduced >40%
- Runtime: neutral or faster (early detection avoids downstream steps on weak bullets)

**Experiment phases:**
```
Phase 0 (0.5 day): Run 10 test resumes. Tag all BRS<6 bullets. Human-rate.
Phase 1 (1.5 days): Implement gate. Threshold=6.0 (configurable via LR_BRS_THRESHOLD).
Phase 2 (0.5 day): Re-run same 10 resumes. Compare BRS distribution + human ratings.
                   If no improvement → raise threshold to 7.0, re-test.
                   Revert if mean BRS degrades (gate generating too many false positives).
```

**Acceptance criteria:**
- AC1: New gate function `_should_regenerate(brs: float, threshold: float = 6.0) -> bool` in orchestrator
- AC2: If gate fires → step_10 called again (1 additional attempt max — no infinite loop)
- AC3: If 2nd attempt also fails threshold → original accepted + flagged in success box: "N bullets below quality threshold — consider manual review"
- AC4: `LR_BRS_THRESHOLD` env var overrides 6.0 default (tuning without code change)
- AC5: Gate applies ONLY between step_10b and step_12 — does NOT affect fabrication-guard retry logic

**User story:**
> As a job seeker, I want weak bullets to get a second generation attempt instead of being width-expanded into a worse shape. Polished mediocrity is still mediocrity.

**Test cases:**
- Bullet BRS = 7.5 → gate passes; width expansion runs normally
- Bullet BRS = 5.2 → gate fires; step_10 regenerates; new BRS = 7.1 → proceeds normally
- Bullet BRS = 5.2 → regenerated BRS = 4.9 → both below threshold → accept original + flag
- `LR_BRS_THRESHOLD=8.0` set → gate fires on bullets BRS < 8.0

**Files touched:**
- `resume/orchestrator.py` (new `_should_regenerate()` + gate between step_10b and step_12)
- `resume/cli.py` (success-box warning for flagged bullets)
- `tests/test_progressive_gate.py`

**Dependencies:** S1.2 (fabrication guard verb-stripping bug fixed first — otherwise gate may fire on fabrication-failed bullets, conflating two failure modes).

---

### 7.S5.6 — Cross-bullet verb coherence enforcer

**Feature description:** Within a single resume section (e.g. one job role), step_10 generates bullets somewhat independently. The verb diversity scorer in scorecard.py penalizes reuse post-hoc, but bullets are already assembled. The result: "Led cross-functional... Led compliance... Led growth..." — 3 of 6 bullets in the same section starting with "Led". Recruiters notice verb repetition; it signals low-effort drafting. Add a post-generation pass using Oracle's local `gemma3:1b` (already on Oracle per `reference_oracle_ollama.md`, already used in production — no new model download, no API call, no fine-tuning needed). The task is constrained: "rephrase this bullet without using the verb X." Constrained generation is exactly where a 1B model performs well. BRS check on the rephrased bullet before accepting — if rephrased version degrades BRS by >10%, revert to original (quality-first).

**Baseline metrics (Phase 0):**
- % of resumes with leading-verb repetition in same section across 10 test resumes
- Mean leading-verb diversity per section (unique verbs / total bullets per section)

**Success metrics:**
- % of resumes with 0 leading-verb repetition in same section: >90%
- Mean leading-verb diversity: >0.90 per section
- BRS of rephrased bullets: no mean degradation vs. originals (< 5% average drop)
- API calls: 0 (Oracle local inference only)

**Experiment phases:**
```
Phase 0 (0.5 day): Audit 10 test resumes. Count leading-verb repetitions.
Phase 1 (2 days): Implement post-generation pass. gemma3:1b on Oracle.
                  BRS-check rephrased; revert if BRS drops >10%.
Phase 2 (0.5 day): Re-audit. Confirm diversity metric improved.
                   Monitor: is Oracle latency acceptable? (<3 sec total per resume)
```

**Acceptance criteria:**
- AC1: `_enforce_verb_coherence(bullets: list[str], section_id: str) -> list[str]` runs after step_10 completes for each section
- AC2: Extracts leading verb from each bullet (first word after optional "●" marker)
- AC3: For each duplicate leading verb (>1× in section) → Oracle gemma3:1b prompt: `"Rephrase this resume bullet without using the verb '{verb}': {bullet}"`
- AC4: BRS of rephrased bullet vs. original — if rephrased BRS < original BRS × 0.90 → revert to original
- AC5: Max 1 rephrase attempt per bullet (no retry loop)
- AC6: Oracle unavailable → skip coherence pass silently; log warning in telemetry; not a blocking error
- AC7: Runs AFTER step_11 ranking (ranking order unaffected — coherence enforced on already-ranked list)

**User story:**
> As a job seeker applying to senior roles, I want variety in action verbs so my resume reads as thoughtful and deliberate — not as if I found one verb and used it six times in the same section.

**Test cases:**

| Input | Expected outcome |
|---|---|
| 4 bullets in Sprinklr section; 3 start with "Led" | 2 of the "Led" bullets rephrased ("Directed", "Oversaw"); BRS maintained |
| 6 bullets, all unique leading verbs | No change (pass finds no duplicates) |
| Oracle gemma3:1b unreachable | Pass skipped silently; original bullets unchanged; warning in telemetry |
| Rephrased bullet BRS drops >10% | Revert to original; logged as "reverted — quality preserved" |

**Files touched:**
- `resume/lib/coherence.py` (new — `_enforce_verb_coherence()`, Oracle call wrapper)
- `resume/orchestrator.py` (call after step_11, before step_12)
- `resume/lib/oracle_client.py` (existing or new — gemma3:1b inference wrapper)
- `tests/test_verb_coherence.py`

**Dependencies:** S5.1 (embedding alignment done first — coherence runs post-ranking which uses embedding scores). Oracle VPS must be reachable.

---

### 7.S5.7 — Fine-tuned fabrication guard (asymmetric loss, gemma3:1b)

**Feature description:** This is the highest-scoring item in Sprint 5 (83/100) and addresses the only catastrophic-risk pain in the entire pipeline: a fabricated metric slipping into a resume, being cited in an interview, and destroying the candidate's credibility. The current step_10b guard uses a zero-shot LLM prompt with no threshold control — balanced accuracy, not asymmetric risk management. A false negative (fabrication slips through) is catastrophically worse than a false positive (valid claim wrongly rejected). This item replaces the zero-shot guard with a fine-tuned `gemma3:1b` classifier trained with asymmetric cross-entropy loss (false negative penalty weight = 5×), on labeled `(bullet, source_excerpt, grounded/fabricated)` triplets from real pipeline runs. Hard negatives (numbers within 20% of actual) explicitly over-represented in training — this is exactly where zero-shot LLMs fail most.

**⚠️ 3-week timeline. Data collection starts Sprint 1 (parallel — passive instrumentation). Fine-tuning starts Sprint 5. DO NOT start S5.7 without confirmed Phase 0 baseline showing FNR > 3% — if current guard is already performing well, skip this item entirely.**

**Baseline metrics (Phase 0 — start NOW, Sprint 1):**
- Instrument step_10b to log: `(bullet_text, source_excerpt, guard_decision)` to `~/.linkright/training-data/fabrication-guard/` (gitignored, non-PII only)
- Collect 300 triplets from real pipeline runs on test corpus
- Human-annotate: for each triplet, verify guard_decision is correct (ground truth)
- Measure FNR (fabrication slips) + FPR (valid claims wrongly rejected)
- **Gate rule:** if Phase 0 FNR < 3% → skip S5.7 entirely (current guard is good enough)

**Success metrics:**
- FNR post fine-tune on 50-pair held-out test set: <2%
- FPR post fine-tune: <12% (asymmetric — over-rejection acceptable; false safety is not)
- step_10b per-bullet latency: <100ms (10 bullets = <1 sec vs. current 30-50 sec total)
- API calls for fabrication guard: 0 for locally-classified bullets; API only for borderline cases (confidence < 0.85)

**Experiment phases:**
```
Phase 0 — Baseline measurement (Sprint 1-4 passive, 4 weeks):
  1. Add step_10b instrumentation — log (bullet, source_excerpt, decision) to disk
  2. Collect 300 real triplets from test-corpus pipeline runs
  3. Human-annotate: verify each guard_decision correctness
  4. Compute FNR + FPR on annotated set
  5. Gate: FNR < 3% → STOP. Current guard sufficient. Close S5.7.
     FNR ≥ 3% → proceed to Phase 1.

Phase 1 — Data cleaning + fine-tune (Sprint 5 week 1):
  1. Remove uncertain-annotation triplets
  2. Split: 200 train / 50 val / 50 test (stratified)
  3. Augment with 50 synthetic hard negatives (±20% of actual numbers)
  4. QLoRA fine-tune gemma3:1b:
       Loss: asymmetric cross-entropy (FN weight=5.0, FP weight=1.0)
       Epochs: 3 with val-set eval after each
       Library: HuggingFace PEFT + TRL (SFTTrainer with custom loss)
       Hardware: M1 16GB or Oracle VPS

Phase 2 — Evaluation + deployment (Sprint 5 week 2):
  1. Eval on 50-pair held-out test set
  2. Ship ONLY IF: FNR < 2% AND FPR < 12% (non-negotiable quality gate)
  3. Deploy hybrid: local model classifies; if confidence < 0.85 → API verifies
  4. Monitor first 100 production runs for unexpected FP spikes
```

**Acceptance criteria:**
- AC1: Fine-tuned model achieves FNR < 2% on 50-pair held-out test set (measured, not inferred, before deployment)
- AC2: Fine-tuned model achieves FPR < 12% on same test set
- AC3: Model served via Oracle gemma3:1b with LoRA adapter loaded (~80-100MB adapter on existing base model — no new download)
- AC4: Hybrid mode: `if confidence < 0.85 → escalate to API verification` — confidence is the model's softmax output for "fabricated" class
- AC5: Phase 0 instrumentation logs at `~/.linkright/training-data/fabrication-guard/` (gitignored, non-PII only)
- AC6: `linkright train fabrication-guard --data-path <path>` CLI command documents the training recipe (reproducible fine-tuning for future retraining as pipeline evolves)
- AC7: Phase 0 gate strictly enforced — if FNR already < 3% → close S5.7 without implementation

**User story:**
> As a job seeker, I need absolute confidence that my resume contains zero metrics I didn't actually achieve — because one fabricated number in a technical interview destroys my credibility and can blacklist me at the company forever. The tool's guarantee must be real, not probabilistic.

**Test cases (post-training eval on held-out 50 pairs):**

| Bullet claim | Source text | Expected verdict |
|---|---|---|
| "Saved $5M" | Source: "$4.8M savings" (+4% of actual) | FABRICATED (hard negative — close but not exact) |
| "Saved $4.8M in annual ops cost" | Source: "$4.8M savings" | GROUNDED |
| "Led 50-engineer team" | Source: "30 engineers" | FABRICATED |
| "Led 30-engineer team" | Source: "30 engineers" | GROUNDED |
| "Improved NPS by 25 points" | Source: "Improved NPS" (no number) | FABRICATED (metric hallucinated) |
| "Improved NPS" | Source: "Improved NPS by 25 points" | GROUNDED (understated, not fabricated) |
| Confidence score 0.82 (<0.85 threshold) | — | Escalate to API; uncertain |

**Files touched:**
- `resume/lib/fabrication_guard.py` (new — fine-tuned model inference + hybrid decision logic)
- `resume/orchestrator.py: step_10b` (call `fabrication_guard.classify()` instead of direct LLM call)
- `linkright/cli.py` (new `linkright train fabrication-guard` subcommand)
- `scripts/collect_fabrication_guard_data.py` (new — step_10b log parser → training-data format)
- `scripts/train_fabrication_guard.py` (new — QLoRA fine-tune script)
- `tests/test_fabrication_guard_finetuned.py` (eval on held-out test set)
- `~/.linkright/training-data/fabrication-guard/` (gitignored)

**Dependencies:**
- S1.2 (fix fabrication guard verb-stripping bug) **must ship first** — Phase 0 training data must not include false positives from the existing bug. Contaminated training data → contaminated model.
- Phase 0 instrumentation must start in Sprint 1 (parallel, passive) — data collection is the long lead time.
- Oracle VPS + M1 16GB for QLoRA training (infrastructure already available per `reference_oracle_ollama.md`).

---

### 7.S5.0 — CLI pre-flight dependency guards

**Feature description:** Commands currently dispatch their full pipeline before checking whether required prerequisites exist. `linkright resume tailor` crashes with a Python traceback ("Cannot read an empty file") when profile has never been created. Same pattern affects all harness commands and `profile create` on corrupt PDFs. Add lightweight pre-flight guards that run at the CLI boundary, print an actionable "run X first" message, and exit cleanly before any pipeline work starts.

**Dependency chain enforced:**

```
linkright setup / keys add          → creates config + LLM key
linkright profile create <pdf>      → creates ~/.linkright/profile/metadata.yaml
        ↓
linkright resume tailor             → requires: profile + LLM key + JD
linkright cover-letter              → requires: profile + LLM key + JD
        ↓
linkright resume improve / critique / practice / fill-metrics / score / strategy-review
                                    → requires: profile + prior tailor run
```

**Acceptance criteria:**
- AC1: `linkright resume tailor` with no profile → prints "✗ No profile found. Run: linkright profile create..." + exits 1 (no traceback)
- AC2: `linkright resume tailor` in direct mode with no key → prints "✗ No LLM API key configured. Run: linkright keys add groq..." + exits 1
- AC3: `linkright resume improve` with no prior tailor run → prints "✗ No tailor run found. Run: linkright resume tailor..." + exits 1
- AC4: `linkright profile create` with corrupt/empty PDF → prints "✗ Cannot read PDF..." + exits 1 (no pypdf traceback)
- AC5: All guards are no-ops when prerequisites are satisfied — normal pipeline execution unaffected

**User story:**
> As a first-time user who installs linkright and immediately runs `linkright resume tailor`, I want to see "No profile found — run profile create first" instead of a Python traceback, so I know exactly what to do next.

**Files touched:**
- `resume/lib/preflight.py` (NEW — `require_profile()`, `require_llm_key()`, `require_tailor_run()`)
- `resume/cli.py` — add guards to `tailor`, `improve`, `fill-metrics`, `practice`, `strategy-review`, `critique`
- `profile/cli.py` — add PDF readability guard in `create_cmd`

**Dependencies:** none. Standalone pre-check — no pipeline code touched.

---

## 8. Quality / Testing Strategy

### 8.1 TDD

Every code change starts with a failing test. The test is committed in the same PR that introduces the fix or feature. Test-suite gate: all tests must pass before PR merges.

### 8.2 Prior-art

LinkRight already has a quality-iteration framework in `e2e_diagnostic_run/`:
- `iteration_runner.py` — multi-iteration loop driver
- `deep_rca.py` — root-cause analysis on regressions
- `analyze_run_04.py` — per-run statistical analysis
- `run_pipeline.py` — single-run pipeline executor
- `runs/` — historical run data

This PRD does NOT replace that framework — it extends it (see §8.4).

### 8.3 Methodology

Per memory `feedback_99pct_hypothesis_loop.md`: iterative improvement targeting 99% accuracy via hypothesis-test-keep-or-revert cycles, single-variable experiments only.

### 8.4 Autonomous testing pipeline (F-AUT, new feature)

**Driver:** Playwright (browser automation for UI flows on the website) + Python harness (for CLI flows on `linkright resume tailor`).

**Loop:**
```
1. baseline_score = run(test_corpus, current_codebase)
2. for each scorecard_dimension below target:
       hypothesis = generate_hypothesis(dimension, deep_rca)
       apply(hypothesis)  # single-variable change
       new_score = run(test_corpus, mutated_codebase)
       if new_score > baseline_score:
           commit; baseline_score = new_score
       else:
           revert
3. repeat until all dimensions pass OR human-review-required
```

**Hypothesis style:** Karpathy-research-style — testable, falsifiable, single-variable. Examples:
- "Hypothesis: pre-stored acronym bank cuts step_14 LLM calls by ≥50%"
- "Hypothesis: signal-weighting matrix shifts top-1/3 bullets for executive-level resumes"

**Storage:** results in `e2e_diagnostic_run/runs/<date>_<hypothesis>/`, following existing pattern.

**Trigger:**
- Nightly cron (on Satvik's machine or Oracle VPS)
- On-demand: `linkright iterate --target=token-savings` (CLI flag)

**Inputs needed:** see §10 — Satvik provides real resumes + JDs (NOT mocked).

### 8.5 Scoring framework adjustments (new this PRD)

Adjust `resume/scorecard.py` to score additional dimensions:

1. **Subliminal-signal score** — peer-vs-applicant phrase ratio (S4.1), verb-domain-match (S2.2/S2.3), career-level vocab match (S4.2)
2. **Experience-rounding compliance** — `years_to_display()` correctly applied per §5
3. **Section-definition routing accuracy** — each entry routed per §3 definitions (verified against a labeled test set)
4. **Metric-magnitude consistency** — per S4.3
5. **JD-coverage %** — currently computed but not surfaced; surface in success box (S4.4)

Each new dimension is scored 0-100 like existing dimensions and weighted in the composite score.

---

## 9. Workflow (spec-driven + bd + graphify + subagents + manual QA)

### 9.1 Spec-driven development

Order: PRD → features → user stories → bd issues → TDD implementation.

**bd-issue naming convention:** `F-<sprint><id>: <title> [PRD §6 <id>]`. Example: `F-S1.1: Experience rounding rule [PRD §6 S1.1]`. PRD section number in title means every issue is traceable back to the PRD.

**Description template** (per memory `feedback_bd_workflow_quality_tools.md` style):
```
## Why this issue exists
<one paragraph, written PM-style>

## Acceptance criteria
- AC1: <verifiable>
- AC2: ...

## Test cases
- Input X → Expected Y
- Input Z → Expected W

## Files touched
- <file:line>

## Dependencies
- <other bd issue IDs>

## PRD reference
[PRD §6 S1.1] · `# LinkRight PRD.md` line N
```

### 9.2 TDD

Each bd issue's "Test cases" section directly drives the first commit — a failing test. Then the fix. Then refactor.

### 9.3 Graphify refresh

Per CLAUDE.md mandatory rule + memory `feedback_graphify_auto_refresh_policy.md`:
- Auto-refresh via post-merge git hook (real merges trigger graph rebuild)
- Daily cron fallback
- Manual invocation after any code change touching ≥3 files
- Built-in hook install: inner repo (`repo/`) only — outer repo (`linkright_production/`) doesn't have code

### 9.4 Subagent dispatch

Per memory `feedback_three_agent_autonomous_workflow.md`:
- Every implementation task delegated to `product-owner-qa` orchestrator
- PO runs `designer-developer` ↔ `adversarial-reviewer` ↔ QA loop autonomously
- Iteration budget: 3 cycles; then ESCALATE
- Satvik isn't involved between dispatch and ship

Per memory `feedback_pr_merge_gate.md`:
- Final merge gate: explicit `adversarial-reviewer` dispatch AFTER PO returns SHIP
- Verdict: ✅ SIGN OFF or ❌ BLOCK
- If BLOCK → re-dispatch PO with blockers; loop

### 9.5 Manual QA gate

After all bd issues for a sprint close + reviewer signs off, run §11 manual QA checklist. Failures from QA go back into the sprint as new bd issues or escalate to next sprint.

---

## 10. Inputs needed from Satvik (test data — NOT mocked)

Per memory `feedback_no_mock_test_data.md` (this turn) + memory `feedback_one_resume_at_a_time.md`: real data, not mocked.

### 10.1 Resumes (≥5 PDFs)

Cover the 5 career levels:
- 1 fresher (no professional experience, education-heavy)
- 1 entry-level (1-2 years)
- 1 mid-level (3-5 years) — Satvik's own resume qualifies
- 1 senior-level (6-9 years)
- 1 executive (10+ years)

**Stage at:** `~/.linkright/test-corpus/resumes/` (gitignored — outside repo).

### 10.2 Job descriptions (≥10 .md files)

Cover 10 industries: tech, finance, healthcare, marketing, legal, sales, product, design, data, ops.

**Stage at:** `~/.linkright/test-corpus/jds/` (gitignored).

### 10.3 Edge-case resumes (3-5 optional)

For robustness testing:
- Resume with heavy acronym density (defense, healthcare, finance)
- Resume with non-Latin name characters
- Resume with employment gaps (≥6 months)
- Resume with multi-role companies (promotions)
- Resume with side projects + freelance (S3.2 routing test)

**Stage at:** `~/.linkright/test-corpus/edge-cases/`.

### 10.4 What I (Claude) need to know from Satvik to proceed

- Confirm test-corpus directory location is acceptable, OR specify alternate
- Confirm timing — when can the corpus be staged? (Sprint 2 starts 2026-05-18, so by 2026-05-17 ideally)
- Indicate whether the corpus is OK to be shared in `runs/` outputs (PII scrub level)

---

## 11. Manual QA Checklist (end-of-PRD gate, Satvik-runnable)

Stranger-mode walkthrough. Run AFTER all sprint items merged + reviewer signs off. Each item: action + expected outcome + bug-report template.

| # | Step | Action | Expected outcome | If fails |
|---|---|---|---|---|
| 11.1 | Install / setup | `pipx install linkright`, `linkright setup`, `linkright doctor`, `linkright setup --check` | All green, no false negatives, no HF Hub warning leak, doctor + check verdicts consistent | Capture full terminal output + file new bd issue |
| 11.2 | Profile creation | `linkright profile create -r resume.pdf --yes` | Section routing matches §3 definitions; truth-engine prompt verifies contact details | Note which entries routed wrong; new bd issue |
| 11.3 | Tailor run (golden) | `linkright resume tailor -r resume.pdf -j jd.md --no-pause` | 1-page PDF, no "0+ years", no broken bullets, ≥80% width-hit | Capture vision.md + 14_final_resume.html + PDF |
| 11.4 | Summary verification | Open PDF, read summary paragraph | Ceiling-rounded years OR fresher-drop applied per §5 | File against S1.1 |
| 11.5 | Width hit-rate | Read vision.md width-band stats | ≥80% bullets in 108-120 char band | File against width-fit issues |
| 11.6 | Acronym preservation | Search PDF for known acronyms (Gen-AI, AML, RBAC, K8s) | All preserved verbatim, no broken expansion | File against S1.5 |
| 11.7 | Truth Engine spot-check | Verify no metric appears in PDF that's not in source resume | No fabricated metrics; personal details correct | File against S1.2 / S3.3 |
| 11.8 | Token telemetry | Read 16_telemetry.json | Total tokens <13,000 per run | If higher, investigate which step exceeded — file bd issue |
| 11.9 | Cache hit | Run `tailor` second time on same resume + different JD | Profile cache hit, "saves ~30-60s" message shown | File if cache miss when shouldn't be |
| 11.10 | Edge cases | Run on fresher / executive / multi-role resumes (corpus from §10) | Section routing correct, summary handling correct, no errors | File per edge case |

**Reporting template** for failures:
```
QA failure #<n>
Step: 11.<x>
Expected: ...
Actual: ...
Severity: ❌ blocker / ⚠️ friction / 🟢 good
Reproduce: <exact commands run>
Artifacts: <vision.md path, PDF path, terminal log>
```

---

## 12. Open Questions (resolve before implementation kickoff)

| # | Question | Owner | Resolve by |
|---|---|---|---|
| 12.1 | ✅ RESOLVED 2026-05-11 — exam-tested credential → §3.5 Certificates; completion-only program → §3.4 Courses. Coursera Specialization with issued PDF but no exam = §3.4 Courses. | Satvik | Done |
| 12.2 | Subliminal-signal scoring weights — empirical (run autonomous testing pipeline to learn) or heuristic (Satvik picks)? Proposed: heuristic for v1, refine empirically in autonomous-pipeline iterations | Satvik | Sprint 3 kickoff |
| 12.3 | Graphify post-merge hook installation — inner repo (`repo/`) only, or outer too? Proposed: inner only since outer has no code | Claude (already decided) | Done |
| 12.4 | LLM provider preference for autonomous testing pipeline — direct mode (free tier) or agent mode (subscription)? Proposed: direct mode default (per memory `feedback_never_agent_mode_for_hypothesis_tests.md`) | Claude (already decided) | Done |
| 12.5 | Where does §3.7 (Organisations) entry render in resume — same as Awards or its own section? Proposed: same block as Awards & Recognitions for v1 | Satvik | Sprint 3 kickoff |

---

## 13. Appendix

### 13.1 Cross-references

- `# FlowCV Tips.md` (repo root) — Parts 2-7 (audit + scorecard + LinkRight-only rules + gaps + subliminal recommendations + schema audit)
- `# LinkRight Rules.md` (repo root) — Canonical rules enforced today + 🔮 planned items
- `e2e_diagnostic_run/` (repo root) — Prior-art for §8.4 autonomous testing pipeline
- Memory file references (all in `~/.claude/projects/-Users-satvikjain-Documents-linkright-production/memory/`):
  - `feedback_99pct_hypothesis_loop.md` — Karpathy-research-style methodology
  - `feedback_three_agent_autonomous_workflow.md` — PO orchestrator
  - `feedback_pr_merge_gate.md` — final reviewer dispatch
  - `feedback_graphify_auto_refresh_policy.md` — post-merge hook
  - `feedback_one_resume_at_a_time.md` — strict per-sample RCA loop
  - `feedback_never_agent_mode_for_hypothesis_tests.md` — direct-mode default

### 13.2 Glossary

| Term | Definition |
|---|---|
| **BRS** | Bullet Relevance Score — composite of XYZ-completeness + verb strength + metric tier, 0-100 |
| **CU** | Character Unit — Roboto advance-width measurement; ~5% wider for bold |
| **XYZ format** | Impact (X) + Measurement (Y) + Action (Z) bullet structure (Google / Laszlo Bock style) |
| **signal** | Closed-vocabulary classifier for what a bullet demonstrates (leadership, revenue-impact, etc.); 13 valid values |
| **nugget** | Atomic career-experience datum extracted from resume parse; each has one answer + one set of tags |
| **atom** | Same as nugget in some prompts (vendored vocabulary) |
| **fit_loop** | The 1-page enforcement pass; max 5 iterations of escalating shrink strategies |
| **step_NN_*** | Internal pipeline step names (00-16); user-visible labels replaced by S1.3 |
| **🟢 / 🟡 / 🔵 / 🔴** | Idea-tracker statuses: implemented / planned / deferred / rejected |
| **📌 / 🔮** | LinkRight Rules statuses: enforced today / planned |

### 13.3 Source-of-truth file:line table

Compact ref for every rule cited in this PRD. Update when refactoring code.

| Rule | File:line |
|---|---|
| Width band 108-120 | `resume/lib/width_config.py:21-22` |
| CU band 96.33-101.4 | `resume/lib/width_config.py:10-11` |
| Page-fit ideal 85-92% | `resume/scorecard.py:107-143` |
| XYZ format mandate | `resume/lib/prompts.py:99-103, 506-514` |
| Weak verbs blacklist | `resume/scorecard.py:47` |
| Banned phrases | `resume/lib/prompts.py:776` |
| Fabrication guard | `resume/lib/metric_extract.py:84-114` |
| JD-keyword guard | `resume/lib/jd_keyphrase.py` |
| Signal vocab | `resume/orchestrator.py:3526` |
| Signal→questions map | `resume/orchestrator.py:3309` |
| Career-level buckets | `resume/orchestrator.py:206` |
| Bullet budgets | `resume/orchestrator.py:234` |
| Skills stoplist | `resume/orchestrator.py:3189` |
| Synonym bank | `resume/data/synonym_bank.py` |
| Roboto glyph weights | `resume/data/roboto_weights.py` |
| Learned corpus | `resume/data/learned_corpus.py` |
| Strategy enum | `resume/lib/prompts.py:132` |

### 13.4 Refresh policy

Refresh THIS PRD when:
1. A sprint completes — move 🟡 PLANNED items to 🟢 IMPLEMENTED in §4
2. A new audit/QA finds a new gap — add to §4 with status
3. A planned item gets DEFERRED or REJECTED — update status + reason
4. Code refactor changes a file:line in §13.3 — refresh table
5. Success metrics in §2 hit or miss target — update Baseline / Target

---

*Document version 1.1 · Created 2026-05-11 · Updated 2026-05-11 (Session 2) · LinkRight CLI v0.5.16 · Sprint 1-4: 2026-05-11 → 2026-06-08 · Sprint 5 (extended roadmap): 2026-06-08 → 2026-06-22*
