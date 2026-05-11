# LinkRight Rules — Canonical Reference

> Resume-engine rules currently enforced by **LinkRight CLI v0.5.11** (audit date 2026-05-11).
> Source-of-truth: `context/cli/linkright/src/linkright/resume/`.
>
> **Goal:** ship a world-class, 1-page resume tailored to a job description, within strict width-format and token-cost budgets.
>
> **Format note:** mirrors FlowCV's section-by-section structure (see `# FlowCV Tips.md` for the original FlowCV reference). Each rule includes a `file:line` evidence pointer so future maintainers can verify the rule against current code.
>
> **Symbols used below:**
> - 📌 — rule enforced today
> - 🔮 — rule planned (not yet enforced; cross-reference points to `# FlowCV Tips.md` Part 6 or Part 7.2)

---

# Section 1 — Sourced from FlowCV (matched + exceeded by LinkRight)

These are the standard resume-craft rules from FlowCV that LinkRight implements (often more strictly).

### General

- 📌 Keep bullets short. Plain-text width band is **108-120 chars per bullet**, exactly one rendered line. (`resume/lib/width_config.py:21-22`)
- 📌 Summary length: target 150-250 chars; hard-truncate at 300 chars at the nearest sentence boundary. (`resume/orchestrator.py` step_09)
- 📌 Section order is set by `career_level` (fresher / entry / mid / senior / executive). Importance tiers P0 → P3 from `_IMP_ORDER`. (`resume/orchestrator.py:3917`)
- 📌 Reverse-chronological order within Experience and Education sections. Parse contract enforces this. (`resume/lib/prompts.py:183`)
- 📌 View the resume through the employer's lens — bullets ranked by **BRS × 0.3 + JD-token-overlap × 0.7** descending within each role. (`resume/orchestrator.py: step_11_rank`)
- 📌 Never begin a sentence with "I", "My", or "We". Pipeline prompts ban these explicitly. (`resume/lib/prompts.py:114, 525, 709`)
- 📌 Active voice only. Passive constructions like "was built" / "was delivered" are explicitly banned. (`resume/lib/prompts.py:529`)

### Action Words

- 📌 Lead every bullet with an impact verb. "At <Company>, as a/an/the <Role>, I..." prefix is banned (wastes width + flattens diversity). (`resume/lib/prompts.py:522-524`)
- 📌 Weak/filler verbs are penalized at 0.5× in verb-diversity scoring: `worked, helped, assisted, participated, contributed, involved, responsible, duties, tasked, supported, engaged, collaborated, leveraged, utilized, facilitated, ensured, managed`. (`resume/scorecard.py:_WEAK_VERBS` line 47)
- 📌 Banned filler phrases dropped in post-LLM hallucination filter: `by leveraging skills in, resulting in improved, outcome-driven, cross-functional collaboration, drove results, drove outcomes, demonstrated expertise in, showcased proficiency in`. (`resume/lib/prompts.py:776`)
- 📌 **Zero verb repetition** across all paragraphs in the same response. (`resume/lib/prompts.py:443`)
- 📌 **Cross-company verb tracking** — `used_verbs` set is passed forward so a verb used at Company A cannot reappear at Company B. (`resume/lib/prompts.py:447`)
- 📌 Banned adverbs: `successfully, effectively, significantly, consistently`. (`resume/lib/prompts.py:528`)
- 📌 Banned hedge words on numbers: `approximately, around, nearly`. (`resume/lib/prompts.py:531`)
- 🔮 (Planned) Domain-specific impact-verb taxonomy (Tech / PM / Sales / Finance / Legal / etc.) — see `# FlowCV Tips.md` Part 7.2 row 2.

### Personal Details

- 📌 Contact fields parsed at step_01: `name, phone, email, linkedin, portfolio`. (`resume/lib/prompts.py:148`)
- 📌 No social media defaults (Facebook / Instagram) — not in parse contract.
- 🔮 (Planned) Personal-details verification step (photo policy, professional-email check) — see `# FlowCV Tips.md` Part 4 gap 1.
- 🔮 (Planned) Email-format quality check (`firstname.lastname` preferred over `abbygirl129@…`) — see `# FlowCV Tips.md` Part 6 row 6.

### Summary

- 📌 2-3 phrases / 150-250 chars target. (`resume/lib/prompts.py:217-235`)
- 📌 Years-of-experience claimed in the summary MUST NOT exceed candidate's actual years (`career_level` cap enforced). (`resume/lib/prompts.py:150`)
- 📌 Synthesize JD's strongest themes — no fabrication. (`resume/lib/prompts.py:235`)
- 📌 Hard-truncate >300 chars at the nearest sentence boundary. (`resume/orchestrator.py:1741-1755`)
- ⚠️ **Known issue 2026-05-11**: `total_years` calc returning `0.0` for some resumes, producing "0+ years of experience" in summary. Tracked separately.

### Education

- 📌 Parsed fields: `institution, degree, year, gpa, highlights`. (`resume/lib/prompts.py:155`)
- 📌 Highlights copied **VERBATIM** from source — no paraphrasing, no inference. Empty string if not present. (`resume/lib/prompts.py:185`)
- 📌 Reverse-chronological order. (`resume/lib/prompts.py:183`)
- 🔮 (Planned) GPA gating — only render if asked or above-average, with point of reference — see `# FlowCV Tips.md` Part 4 gap 3.

### Professional Experience

- 📌 **XYZ format is mandatory** in every bullet: `X = Impact/Outcome` (lead with this), `Y = Measurement` (concrete digit, %, $, K, M, B), `Z = Action/Contribution` (what YOU did, not team-level). A bullet missing any of X / Y / Z is rejected. (`resume/lib/prompts.py:99-103, 506-514`)
- 📌 **One signal per bullet** — if a source nugget has 3 signals, produce 3 separate bullets. (`resume/lib/prompts.py:495-504`)
- 📌 Closed-vocabulary signal enum (13 values): `leadership, regulatory-tech, revenue-impact, data-driven, cost-reduction, growth, scale, executive-influence, build-execution, user-empathy, ambiguity-resolution, automation, execution`. (`resume/orchestrator.py:3526`)
- 📌 **Numeric fidelity** — every number in a bullet must appear verbatim (or rounded to the same magnitude tier, ±25%) in at least one cited source atom. Year free-pass. (`resume/lib/metric_extract.py:84-114`)
- 📌 **Metric placeholders** (`'X%'`, `'$YM'`, `'Z hours'`) are offered to the user when no source metric exists, instead of fabricating. (`resume/cli.py: fill-metrics`)
- 📌 **Cross-company fact isolation** — a bullet attributed to Company A may cite ONLY atom_ids from Company A's pool. Cross-company citation is rejected. (`resume/lib/prompts.py:579-588`)
- 📌 **Metrics-only bolding** — wrap ONLY numeric metrics with their symbols (`$, %, K, M, B, x, +, ratio, hrs`) in `<b>...</b>`. Impact verbs, action phrases, JD keywords, project names, technologies remain plain. (`resume/lib/prompts.py:438-441`)
- 📌 **Bullet length pipeline**: verbose paragraph at step_10A (150-200 chars) → condense at step_12 to 108-120 chars → width-tune at step_13 to 96.33-101.4 CU. Starting high means step_13 always SHRINKS (LLM strength). (`resume/lib/width_config.py:6-15`)
- 📌 Bullets sorted within each role by **BRS × 0.3 + JD-token-overlap × 0.7** DESC. (`resume/orchestrator.py: step_11_rank`)
- 📌 Promotion in same company renders as a **separate role block**, not a merged entry. Preserves career-growth signal.
- 📌 No-metric fallback: produce a qualitative bullet (still XYZ format, but Y = scope/scale word like "across multiple teams") rather than inventing a number. Skipping is the last resort. (`resume/lib/prompts.py:605-611`)

### Skills

- 📌 Skills section max **3-5 lines** in final render.
- 📌 **Tier scoring** for skill ranking: must-have (+10) / nice-to-have (+7) / JD-keyword (+5) / source-skill (+3) / acronym (+1) / generic (+0). Render in tier order DESC.
- 📌 Generic single-word "skills" filtered via stoplist (28 entries): `quality, marketing, documentation, email, forms, reliability, support, insight, fixes, content, tracking, enablement, communication, writing, design, engineering, strategy, management, leadership, operations, ai-powered, all-in-one, white-label, ai-driven assistance, help content, support insight, product fixes, time-to-ship, triggers/actions, workflow usage`. Multi-word forms pass (e.g. "quality assurance" passes; "quality" alone doesn't). (`resume/orchestrator.py:3189`)
- 📌 Acronyms preserved verbatim in skill names. (`resume/lib/prompts.py:574`)
- 📌 Drop generics first when space is tight (skills trim happens BEFORE width fill).

### Custom Sections

These are not all parsed today. See `# FlowCV Tips.md` Part 2.8 for the matrix.

- 📌 **Interests** — comma-separated string, rendered at bottom of resume. (`resume/lib/prompts.py:159`)
- 📌 **Awards & Recognitions** — 2 bullets default budget. Parsed at step_07. (`resume/lib/prompts.py:158, 196`)
- 📌 **Projects (independent_project nuggets)** — surface only when `bullet_budget.projects > 0` AND JD context suggests projects matter (platform / engineering / research roles). (`resume/lib/prompts.py:196`)
- 📌 **Side-project routing rule** (Satvik 2026-04-22) — overlapping / Freelance / Pro-Bono entries route to Projects, not Professional Experience.
- ❌ **Languages, Courses, Organisations, Publications, References, Certificates** — not in parse contract today. (`# FlowCV Tips.md` Part 2.8)

---

# Section 2 — LinkRight-specific (no FlowCV equivalent)

These rules are LinkRight's value-add on top of standard resume guidance — most are oriented around the 1-page constraint, fabrication prevention, and JD-fit ranking.

### Width & Formatting (1-page hard constraint)

- 📌 **Single A4 page, no exceptions.** `pages != 1` → page-fit score 0 (hard fail). (`resume/scorecard.py:124-125`)
- 📌 **Plain-text char band per bullet:** 108-120 chars (`STEP12_MIN_CHARS = 108`, `STEP12_MAX_CHARS = 120`). (`resume/lib/width_config.py:21-22`)
- 📌 **Roboto CU band per rendered line:** 96.33-101.4 CU (derived from Roboto advance-width measurement at 10pt). (`resume/lib/width_config.py:10-11`)
- 📌 **Catastrophic-undershoot threshold:** anything below 95 plain chars triggers a retry. (`resume/lib/width_config.py:12-13`)
- 📌 **Lenient band:** -1 / +7 CU around target for "visually clean" bullets (94 CU is indistinguishable from 96 on paper). (`resume/lib/width_config.py:14-15`)
- 📌 **fit_loop** max 5 iterations with escalating shrink strategies. (`resume/lib/fit_loop.py`)
- 📌 **Page utilization IDEAL band:** 85-92% (target ~90%, breathing space at bottom). Updated from 95% on 2026-05-02. (`resume/scorecard.py:107-143`)
- 📌 **Header shrink-to-fit:** name + role-title shrink proportionally with a 14pt floor. Drop team-name suffix after em-dash before truncating. (`resume/orchestrator.py: _compute_header_font_size`)
- 📌 **Width expansion cascade** (when bullet < 108 chars): articles → contractions → preposition swaps → numeral spellings → metric placeholders. Each step keeps gains on partial success. (`resume/lib/width_poc.py`)
- 📌 **SYNONYM_BANK** for width tuning — ~220 trim/expand pairs with measured char-delta (e.g. `"application" ↔ "app"`, delta -8.0). (`resume/data/synonym_bank.py`)

### Truth Engine

LinkRight enforces fact-fidelity in three layers. Layers 1 and 3 are planned; layer 2 is active.

- 🔮 **Layer 1 — Personal-details verification (planned).** Surface phone / email / LinkedIn / portfolio to user for confirmation at pipeline start. See `# FlowCV Tips.md` Part 4 gap 1. Memory: `feedback_personal_details_verify_at_start.md`.
- 📌 **Layer 2 — step_10b fabrication guards (active).**
  - **`metric_extract` guard:** rejects bullets with numbers outside ±25% magnitude tier of source. Year free-pass. (`resume/lib/metric_extract.py:84-114`)
  - **`jd_keyphrase` guard:** rejects bullets with JD keywords that don't appear in the candidate's source nuggets (no JD-fishing). (`resume/lib/jd_keyphrase.py`)
  - **Hallucination phrase filter:** 8 banned phrases stripped post-LLM. (`resume/lib/prompts.py:776`)
- 🔮 **Layer 3 — End-of-pipeline critique step (planned).** After step_15, LLM critiques the resume + lists 5 issues + offers 3 fix options including "manual edit". Memory: `feedback_end_of_pipeline_critique_step.md`.
- 📌 **Years-of-experience cap:** summary cannot claim more years than `career_level` bucket allows. (`resume/lib/prompts.py:150, 175-181`)
- 📌 **JD keyword no-contamination rule:** `jd_keywords` may contain only terms appearing literally in the JD text — never leaked from resume context. (`resume/lib/prompts.py:174`)
- 📌 **Cross-company atom-id citation forbidden** — see Section 1 → Professional Experience.

### Bullet Ranking (BRS × JD-alignment)

- 📌 **BRS score** (Bullet Relevance Score) computed at step_11 from XYZ-completeness + verb strength + metric tier. Normalized 0-1 or scaled 0-100 (auto-detected). (`resume/scorecard.py:_s_brs_top_pct`)
- 📌 **JD-token overlap weighting:** 0.7 (dominant) vs 0.3 BRS in combined rank. JD-fit matters more than raw bullet quality.
- 📌 **Within each role**, bullets sorted by combined score DESC.
- 📌 **Recruiter 6-second scan** lands on top 1/3 of bullets — highest-fit content lives there.
- 🔮 (Planned) Company-prestige tier weighting in BRS — see `# FlowCV Tips.md` Part 6 row 1.
- 🔮 (Planned) Career-level signal-weighting matrix (13 × 5) — see `# FlowCV Tips.md` Part 7.2 row 3.

### Acronym & Vocabulary Preservation

- 📌 **VERBATIM rule:** every number, proper noun, and acronym preserved letter-for-letter through condense + width-tune steps. (`resume/lib/prompts.py:574`)
- 📌 **Known-acronym exempt set** (42 entries): PM, AI, ML, AWS, API, CSS, … — exempt from expansion check during scoring. (`resume/scorecard.py:_COMMON_KNOWN_ACRONYMS` line 329)
- 📌 **Past-tense irregulars set** (~60 entries) used by tense-consistency check for past roles. (`resume/scorecard.py:_PAST_TENSE_IRREGULARS` line 265)
- 📌 **learned_corpus** — persistent JSON file that accumulates acronym expansions and vocabulary candidates across runs (self-improving). (`resume/data/learned_corpus.py`)
- 🔮 (Planned) Pre-loaded acronym bank (~250 entries across 12 domains: tech, cloud, devops, data, AI, security, business, product, healthcare, marketing, HR, finance) — see `# FlowCV Tips.md` Part 7.2 row 1.

### Header & Visual Design (Resume PDF)

- 📌 **Single-page A4, Roboto font family** (Regular + Bold).
- 📌 **Per-glyph advance-width** measured for both weights (~100+ glyphs) — drives CU calculations. (`resume/data/roboto_weights.py`)
- 📌 **Optional brand colors** — `theme_colors` dict with up to 4 colors (`brand_primary / brand_secondary / brand_tertiary / brand_quaternary`).
- 📌 **Brand color usage:** apply to **metrics + dividers + accent rules only**. Body text stays black. (`resume/orchestrator.py:3749-3752`)
- 📌 **Max 3 active colors** per resume (avoid visual noise).
- 📌 **Header layout:** name (large) + role title side-by-side; proportional shrink-to-fit with 14pt floor; drop team-name suffix after em-dash before truncating.
- 📌 **Section dividers** use accent color from theme_colors when brand-mode active; default dark-gray otherwise.

### CLI Terminal UI Patterns (Established 2026-05-11, S1.8)

Visual language for ALL `linkright` CLI surfaces — mirrors Claude Code's terminal polish while using LinkRight's design-system palette (not Anthropic's). Reference images logged in PRD §7.S1.8.

- 🔮 (Planned S1.8) **Single Rich theme** — `LR_THEME` from `linkright/ui/theme.py`. All `Console()` instances use `Console(theme=LR_THEME)`. No hardcoded ANSI escapes or inline `style="cyan"` strings.
- 🔮 (Planned S1.8) **Color palette** — sourced from `tools/assemble_html.py:ThemeColors`:
  - `brand_primary` `#4285F4` → command names, info state, key emphasis, banner anchor
  - `brand_secondary` `#EA4335` → error state, blocker tags
  - `metric_positive` `#34A853` → success state, ✓ marks
  - `metric_negative` `#EA4335` → regression markers
  - `text_secondary` `grey50` (≈ `#5F6368`) → italic recap, metadata, "Allowed by auto mode classifier"-style annotations, file paths
  - `divider` `grey70` (≈ `#DADCE0`) → section dividers, horizontal rules, table borders
- 🔮 (Planned S1.8) **6 canonical rendering primitives** in `linkright/ui/patterns.py`:
  1. `picker(question, options, header)` — AskUserQuestion-style numbered options with current-selection highlight + checkbox header bar
  2. `status_event(emoji, label, body, allowed_by=None)` — `●` bullet + emoji + bold label + body + optional grey "Allowed by auto mode classifier" footer
  3. `insight_block(text)` — `★ Insight` headline with horizontal rule top + bottom
  4. `code_block(content, lang=None)` — green-left-border code panel
  5. `progress_indicator(label, elapsed, tokens=None)` — "Waddling… (2m 3s · ↓ 8.6k tokens)" style line
  6. `tree_branch(items)` — `└─` / `├─` style nested indent renderer
- 🔮 (Planned S1.8) **Tree-indented output for multi-line status** — primary level uses `●`, sub-levels use `└─` and `├─`. Mimics Claude Code's terminal hierarchy.
- 🔮 (Planned S1.8) **Italic grey for metadata** — recap lines, file paths, "+N lines (ctrl+o to expand)" affordances all rendered in `text_secondary` italic.
- 🔮 (Planned S1.8) **Emoji-prefixed section headers** — `🎯 Win`, `👤 User impact`, `🚀 What's next`, `★ Insight`, `📥 Next action`, etc. Consistent across surfaces.
- 🔮 (Planned S1.8) **Time-elapsed + token counter** in any long-running spinner — "Worked for 11m 37s" footer pattern. Honest cost transparency.
- 🔮 (Planned S1.8) **Welcome banner** — LINKRIGHT ASCII art uses brand-primary gradient anchor; "Your local-first career OS · $0 to run" subline in text-secondary; divider line in `divider` color; version in `brand_primary`.
- 🔮 (Planned S1.8) **Snapshot tests** lock the rendered output for every CLI surface — `tests/test_cli_ui_snapshot.py` + golden files in `tests/snapshots/`. Future PRs that touch UI must update snapshots intentionally.
- 🔮 **Mascot character** — DEFERRED to Q3 2026. Will live in `linkright/ui/mascot.py`. Branding asset for welcome banner (like Claude Code's blob creature). Out of v1 scope.

**Why this rule matters:** First-impression polish is the highest-leverage trust signal in a CLI tool. Claude Code's tight tree-indented output + sensible whitespace + consistent color hierarchy is what makes it FEEL trustworthy in 5 seconds. LinkRight inherits the same polish floor — never below.

### Token & Cost Optimization

- 📌 **LLM cascade** (free-tier first): Groq → Cerebras → Cloudflare → Gemini → SambaNova → Z.ai → OpenRouter. (`resume/cli.py`, `llm/direct.py`)
- 📌 **Three dispatch modes:** `direct` (HTTP API, default — BYOK), `agent` (subprocess to claude / opencode / gemini CLI), `mcp` (MCP server). (`llm/direct.py`)
- 📌 **Direct-mode default for multi-pipeline runs** — agent-mode burns subscription quota faster. Memory: `feedback_never_agent_mode_for_hypothesis_tests.md`.
- 📌 **Telemetry mandatory** — every run writes `16_telemetry.json` with token counts + cost. (`resume/cli.py: step_16`)
- 📌 **Per-step batching:** `ENABLE_BATCH_STEP_10=1` flag generates paragraphs for ALL companies in ONE LLM call (~50% token reduction, 66% fewer round-trips). Falls back to per-company on JSON failure. (`resume/lib/prompts.py:480-483`)
- 📌 **Persistent profile cache** at `~/.linkright/profile/` — `step_00 / step_01 / step_02 / step_03` artifacts reused across tailor runs (saves 30-60 sec per run).
- 📌 **Embedder cascade** (free-first): Oracle nomic-embed-text → fastembed BAAI/bge-small-en-v1.5 (default) → sentence-transformers → SHA-256 stub. Tier recorded in `metadata.yaml`; tailor refuses cache reuse on tier mismatch.
- 📌 **Bullet-budget cap** prevents over-generation: 12-15 bullets for one A4 page; `bullet_budget.projects` 0-4 depending on JD relevance. (`resume/lib/prompts.py:196`)
- 🔮 (Planned) Pre-load acronym bank + verb taxonomy + signal-weighting matrix → estimated 3-5 LLM round-trips eliminated per run (30-50% token reduction at step_10 / step_14). See `# FlowCV Tips.md` Part 7.2.

### Strategy Selection

- 📌 **5 strategies** picked at step_07 based on JD emphasis: `METRIC_BOMBARDMENT, SKILL_MATCHING, LEADERSHIP_NARRATIVE, TRANSFORMATION_STORY, BALANCED`. (`resume/lib/prompts.py:132`)
- 📌 **One strategy per JD**, applied across all bullet-generation steps.
- 📌 Strategy choice surfaced in `strategy_reason` (one-sentence justification) for user review at strategy checkpoint.

### Interactive Checkpoints

- 📌 **Pipeline pauses** at 4 checkpoints by default; user types Enter to advance, Ctrl-C to abort. (`resume/orchestrator.py: _see_and_continue` line 37-52)
- 📌 **Skip-all flag:** `LR_NO_PAUSE=1` env var or `--no-pause` CLI flag for non-interactive runs.
- 📌 **vision.md logbook** appended at each checkpoint with timestamps + decisions.
- 🔮 (Planned) **Strategy-review checkpoint at step_07b** — surface outline + width + height distributions to user BEFORE step_10 verbose-bullet generation. Memory: `feedback_strategy_human_in_the_loop.md`.

### Subliminal Signaling

⚠️ Forward-looking section — these capabilities are NOT enforced today. Documented here so the canonical doc is complete. See `# FlowCV Tips.md` Part 6 for the full 10-item recommendation set.

- 🔮 **Peer-language vs applicant-language bank** keyed by JD seniority — Part 6 row 2.
- 🔮 **Career-level vocabulary profile** (exec=authority, mid=credibility, entry=energy) — Part 6 row 4.
- 🔮 **Composure / intellectual-honesty framing** when source has gaps — Part 6 row 3.
- 🔮 **Metric magnitude consistency enforcement** (never put 5% next to $50B) — Part 6 row 5.
- 🔮 **Audience-aware show-vs-tell templates** — Part 6 row 8.
- 🔮 **Industry-domain verb taxonomy** — Part 6 row 9.
- 🔮 **Cluster-aware JD requirement matching** — Part 6 row 10.

### Pre-stored Data Layer

See `# FlowCV Tips.md` Part 7.1 for the full table of 22 pre-stored lookups. Summary by category:

- 📌 **Verb dictionaries:** `_WEAK_VERBS` (16), `_PAST_TENSE_IRREGULARS` (~60).
- 📌 **Acronym dictionaries:** `_COMMON_KNOWN_ACRONYMS` (42); `learned_corpus` (persistent, grows per run).
- 📌 **Regex patterns:** `_MAG_BILLIONS / _THOUSANDS / _PCT` (scorecard.py), `_TOKEN_RE / _ACRO_RE` (jd_keyphrase.py), `_METRIC_PATTERNS` (width_poc.py), `_NUM_RE` (metric_extract.py), `PROOF_REGEX` (prompts.py:789).
- 📌 **Stop / ban lists:** `_STOPWORDS` (60+, jd_keyphrase.py), `GENERIC_SINGLE_WORDS` (28), `BANNED_PHRASES` (8).
- 📌 **Bucket maps:** `_CAREER_LEVEL_MIN_YEARS` (5), `_CAREER_LEVEL_TO_PROFILE` (5), `_BULLET_BUDGETS` (5×3), `_IMP_ORDER` (4), `_MONTHS` (12).
- 📌 **Signal vocab:** `_VALID_SIGNALS` (13), `_SIGNAL_TO_QUESTIONS` (11 signals × 2-3 Q each).
- 📌 **Synonyms / weights:** `SYNONYM_BANK` (~220 pairs), `ROBOTO_REGULAR_WEIGHTS / BOLD_WEIGHTS` (100+ glyphs each).
- 📌 **Strategy enum:** 5 strategies.

🔮 (Planned additions — 10 layers) — see `# FlowCV Tips.md` Part 7.2.

---

# Appendix A — Cross-references

- Full FlowCV ↔ LinkRight scorecard with status (✅ / 🔼 / 🟡 / ❌) per rule: `# FlowCV Tips.md` Part 2.
- LinkRight-only rules with detailed evidence: `# FlowCV Tips.md` Part 3.
- Gaps where LinkRight misses FlowCV rules: `# FlowCV Tips.md` Part 4.
- Subliminal-signal improvement recommendations: `# FlowCV Tips.md` Part 6.
- Pre-stored data schema audit + 10-item recommendation set: `# FlowCV Tips.md` Part 7.

# Appendix B — Refresh policy

This document is the canonical rules reference for LinkRight CLI. Refresh it whenever:

1. A prompt string in `resume/lib/prompts.py` changes a banned phrase, format mandate, or weight.
2. A scoring weight or band in `resume/scorecard.py` or `resume/lib/width_config.py` changes.
3. A new pre-stored data layer is added (item from `# FlowCV Tips.md` Part 7.2 lands).
4. A new step is inserted into the pipeline (step_07b strategy-review, step_15b critique, etc.).
5. CLI flags or environment variables for runtime behavior change.

Cite the new `file:line` in the refresh.

---

*Document version 1.0 · Created 2026-05-11 · LinkRight CLI v0.5.11*
