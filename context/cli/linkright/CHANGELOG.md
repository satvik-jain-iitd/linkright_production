# Changelog

## [0.9.4] - 2026-05-14

### Fixed
- **Startup crash after v0.9.3 — harness scorecard types moved into src:** `linkright` crashed on startup with `ModuleNotFoundError: No module named 'harness'` because `harness/` was gitignored in the previous release but `linkright.jobsearch.evaluator`, `linkright.jobsearch.scorecard`, `linkright.resume.scorecard`, `linkright.content.scorecard`, and `linkright.interview.scorecard` all imported `Dimension`, `DimensionResult`, `Scorecard`, and `grade_from_score` from `harness.scorecard` at module load time. Fix: moved these types into `src/linkright/_scorecard_base.py` (canonical new home) and updated all five import sites. Removed `harness*` from `pyproject.toml` package discovery — `where` is now `["src"]` only. No behaviour changes.


## [0.9.3] - 2026-05-14

### Added
- **UAT Cluster E1 — Tokens & Iconography foundation:** Added `linkright/ui/icons.py` — frozen `ICON` constant with the canonical symbol set extracted from Claude Code TUI design language (prompt indicators, status glyphs, tree branches, arrows, tab/picker state, separators, BMAD aliases). Extended `linkright/ui/theme.py` palette with 15 new aliases (`tui.coral`, `tui.cyan`, `tui.muted`, `tui.hi_white`, BMAD semantic aliases, etc.) — all additive; legacy palette preserved. Added 14-case snapshot test suite at `tests/test_icons.py` covering every symbol, helper function, BMAD mapping, frozen-invariant, and palette presence. Foundation PR for the broader Cluster E redesign (#14, #16, #17, #19, #20, #21, #22, #29, #30 land in E2 + E3); this PR specifically resolves UAT bugs #18 (emoji inconsistency), #23 (BMAD iconography), and #24 (prompt-character consistency). Full pattern catalog at `specs/cluster-e-ui-design-system.md`.
- **UAT Cluster E2 — Layout primitives:** Added `linkright/ui/layout.py` with seven new TUI primitives layered on the E1 tokens + iconography foundation: `horizontal_divider()` / `turn_divider()` to wrap role-based interactions with structural rules (#14), `sticky_footer(tier, mode, status)` rendering a single-line three-segment badge bar with semantic colors — gold/orange tier, mint/teal mode, muted status — and automatic vertical stacking on narrow terminals (#16), `tab_bar()` for display + `tab_navigate()` interactive prompt_toolkit navigator binding Tab / Shift-Tab / Left / Right / h / l keys with a numbered-picker non-TTY fallback so headless contexts never silently no-op (#17), and `l_branch_tip()` / `l_branch_group()` rendering muted-gray `└` / `├` branch lines for secondary information and tip clusters (#22). Wired the divider + tip + sticky-footer into three surfaces per spec §2/§3 of `specs/cluster-e-ui-design-system.md`: (a) `linkright doctor` success + failure paths and the no-subcommand `linkright` cheat-sheet; (b) `linkright profile show` — `horizontal_divider` between the populated tree and the "not yet populated" advisory block plus `sticky_footer(mode='profile', status=N nuggets)` at the surface bottom; (c) `linkright resume tailor` — `horizontal_divider` before the success card plus `sticky_footer(mode='tailor', status=duration)` after, both placed outside the orchestrator's `rich.live` progress region so they never overlap streaming updates. Migrated the existing "Tip: edit ~/.linkright/config.yaml" line in `setup_wizard.py` and the "Tip: add these sections..." line in `profile/render.py` to the new `l_branch_tip()` primitive. **Bug #17 — partial fix:** Shipped `tab_navigate()` primitive + opt-in routing in `linkright.prompts.prompt_for_choice` via `LR_PICKER_STYLE=tabs` env var. The routing gate (≤4 options AND ≤30-char labels) currently matches the short-label `PROVIDER_OPTIONS` picker in setup wizard; longer-label pickers (`MODE_OPTIONS`, `EMBEDDER_OPTIONS`, `PDF_OPTIONS`, `prompt_for_resume_source`, `prompt_for_jd_input` — all 33-70-char labels) still fall back to questionary's vertical select. End-to-end Tab/Shift-Tab keyboard nav across every multi-step picker is **deferred to a follow-up cluster** that either (a) shortens picker labels to fit the tab-bar gate or (b) widens the gate + lazily wraps long labels. Default UX is unchanged unless the env var is set. All primitives are additive — no E1 work was refactored. Test suite expanded to 32 cases at `tests/test_uat_cluster_e2.py`: the original 26 (rule character + width + indent, sticky-footer semantic colors via ANSI assertion + narrow-terminal stacking, tab_bar markers, tab_navigate non-TTY fallback paths, L-branch alignment under multi-byte content) plus 6 new wiring tests — 3 for `prompt_for_choice` ↔ `tab_navigate` routing (env-var on → tab path, env-var off → questionary path, long-label fallback), 1 boundary-check on the eligibility predicate, 1 for `_render_success_card` emitting the divider + sticky_footer at the tailor exit boundary, and 1 for `show_profile` emitting the sticky_footer. Resolves UAT bugs #14, #16, #22 fully + #17 partially (primitive + opt-in routing; full wiring deferred).
- **UAT Cluster E3 — Pickers, progress, sub-context, priority legend:** Five strictly-additive UI primitives layered on top of the E1 token foundation.
  - **#19 "Type something" sentinel** — `linkright.ui.lr_select_with_custom()` augments any numbered picker with a "Type something…" final entry; the user can drop into a free-text prompt instead of being stuck with pre-baked options. Opaque sentinel value (`__lr_custom_input__`) avoids collisions with real choice labels. Cancellation and blank-typed-input paths return `None` cleanly.
  - **#20 `●` user-input echo** — `user_input_echo(text, label=...)` (facade: `step_echo_input`) renders previously-submitted user answers with the high-contrast white bullet (`tui.hi_white` = `#F5F5F7`), mirroring Claude Code's pattern of echoing the user's last answer back before continuing. Wired into the profile-enrich follow-up flow as the first concrete call site.
  - **#21 Coral progress verb + muted telemetry** — `progress_verb(verb, telemetry=...)` (facade: `step_progress`) renders `*  Smooshing nuggets  32/128 · 0.8s/batch` with coral verb (`tui.coral` = `#EE6F4F`, already in E1 palette) and muted-grey telemetry tail (`tui.muted` = `#8E8E93`). `+` icon variant auto-switches the icon colour to `tui.green` for "thinking" semantics. Wired into resume orchestrator step_03 (extract nuggets) and step_03b (embed) so long-running operations no longer feel hung.
  - **#29 Quantified Priority Legend** — New `linkright/profile/priority_legend.py` module replaces the vague `core / strong / supporting / context-only` definitions with evidence-shape criteria:
    - **P0** = named outcome AND at least one quantified metric (number with unit or %/$/x/+ symbol)
    - **P1** = named method, decision, deliverable, or outcome BUT no quantified number
    - **P2** = activity with specific context (company, role, team, tech) but no named outcome or metric
    - **P3** = generic statement, no specific context / outcome / metric — candidate for audit/cleanup
    These descriptions describe SHAPE OF EVIDENCE, not absolute thresholds (cross-domain safe — works for designer / scientist / marketer resumes that may not have $-denominated metrics). Importance assignment is reproducible by the LLM extractor and inspectable by the user using the same rule book. `profile/render.py` now imports `format_legend_inline()` + `priority_badge()` from this module (single source of truth — legend definitions cannot drift from the LLM prompt criteria).
  - **#30 Muted sub-context (Claude Code pattern)** — `muted_detail(text, label=...)` (facade: `step_meta`) renders secondary metadata, timestamps, or paths in `tui.muted` (#8E8E93, WCAG AA on both light + dark terminal backgrounds). `claude_metadata(pairs)` renders a compact `· Run: a3f2 · Model: gemma3:1b · Tokens: 1.2k` footer for run summaries.
  - 35-case test suite at `tests/test_uat_cluster_e3.py` covers every primitive, hex-colour assertion (via Rich `export_html`), sentinel collision protection, render.py single-source-of-truth invariant, priority-tier MECE check, and a cross-bug regression that E1 primitives still work. All E1 tests still pass.

### Fixed
- **UAT #4 — `profile create` `.md` file rejected as "invalid pdf header":** Auto-route `.md` and `.markdown` files passed via `-r/--resume` into the existing markdown-ingest path. Users no longer need to remember which flag matches which extension; the CLI infers from file extension. Fix in `profile/cli.py:155` before the PDF readability guard.
- **UAT #37 — `linkright tailor` contact-verify infinite loop:** The exit option in the contact-verification menu was labeled `"s — skip all (keep as-is)"`, which users read as "discard my edits" rather than "I'm done". Renamed to `"✓  All correct — save & continue"` and placed at the top of the choice list with a visual checkmark; also clarified the prompt copy and the input() fallback hint. The underlying `value="s"` is preserved so the existing exit logic at `orchestrator.py:1042` is untouched. Fix in `resume/orchestrator.py:1024-1035` and the input-fallback at `:1058-1061`.
- **UAT #40 — Destructive "No" on continue prompts kills pipeline with traceback:** Replaced `click.confirm(..., abort=True)` at two gate sites (`_see_and_continue` line 53, `_strategy_review_gate` line 134) with `abort=False` + a clean `sys.exit(0)` and an informative restart hint. Pressing "No" now feels like pausing the pipeline rather than triggering a self-destruct error. The inline edit-and-retry menu (Cluster C) will replace the restart hint in a follow-up PR.
- **UAT #2 — Terminal noise (`[tokens] …` raw telemetry leaking into UX):** The two `print("[tokens] …")` sites in `llm/direct.py` (pre-send estimate + post-call usage) now gate behind a new `_debug_enabled()` helper that checks `LR_DEBUG` / `LR_VERBOSE` env vars. Default-off, so `linkright tailor` / `linkright profile create` no longer interleave raw telemetry with friendly progress verbs. Token data is still captured in the per-call `usage` dict and ends up in `16_telemetry.json`, so we lose nothing operationally. Opt in via `LR_DEBUG=1` (or `LR_DEBUG=on` / `y` / `yes` / `true` — common shell truthy variants are all accepted) when diagnosing pipeline LLM behaviour.
- **UAT #6 — `profile create` accepts any PDF / .md as a resume (certificates, cover letters):** Added `_looks_like_resume()` heuristic in `profile/cli.py` that runs BEFORE the 30-90 sec extract pipeline. Scores 4 deterministic signals — keyword density (≥3 of 'experience', 'education', 'skills', verb stems…), email regex, phone regex, ≥400 char body. Keyword matching is now **word-boundary regex** (`\bintern\b`), so cover letters that mention "international team" no longer pick up free hits via substring matching. Cover-letter giveaway phrases ("Dear Hiring Manager", "Sincerely,", "I am writing to", "Please find attached", "my qualifications", etc.) are detected via `_cover_letter_signal_count()` and treated as a **soft missing signal** — when 2+ distinct phrases are present (real cover letters have both an opener and a closer), one point is subtracted from the 4-signal pass count, so the realistic cover-letter case (header contact ⇒ email+phone+length pass, but ≤2 keyword hits and a soft-penalty) drops below the ≥3 threshold and fails. A single embedded phrase (e.g., a quoted testimonial "Best regards, John — VP at X" on an actual resume) does not trigger the penalty. The existing `_prompt_resume_lookalike_override` remains the user-facing escape hatch when the heuristic disagrees with the user. If the file fails the heuristic, an interactive warning lists the missing signals; user can override (`y`) or cancel (`N`, default). Under `--yes` the heuristic still RUNS but warns to stderr instead of prompting (scripted automation must not block; `--yes` no longer silently disables the safety net). Empty / unreadable extracts pass through to avoid false-blocking — the existing PDF readability guard handles truly corrupt files.
- **UAT #9 — `--force` flag suggestion replaced with interactive overwrite picker:** When a profile already exists at `~/.linkright/profile/`, TTY users now see a `lr_select` picker with three choices: "Keep existing (cancel)", "Overwrite (wipe + re-ingest, existing data backed up)", "View existing first". Esc / cancel defaults to the safe "Keep" option. Paste-to-existing-profile (`--from-paste` on top of an existing profile) routes through the same 3-option picker — appending paste content to an existing profile is deferred to a future cluster (its own design pass; an additive picker option that silently mutates a trusted profile carries non-trivial UX-surprise risk). Non-TTY (CI / pipe) paths preserve the legacy `--force`-suggesting error so automation behaviour is unchanged. `--force` remains the explicit opt-in for unattended overwrite.
- **UAT #11 — "Paste resume text" option restored to `prompt_for_resume_source`, with a complete profile (not a half-built one):** The picker now offers two first-class options (file vs paste); selecting "Paste" drops the user into `questionary.text(multiline=True)` (Esc+Enter to submit). The captured body is routed through the existing markdown-ingest path **and** synthesises a minimal `metadata.yaml` (created_at, embedder_tier, embedder_model, dim, n_nuggets, source: "paste", profile_version) — without that file every downstream command (`profile show` / `status` / `tailor` / `enrich` / `graph` / `delete-nugget` / `edit-contact`) reports "No profile found", leaving the user with an unusable half-built profile. The paste-text tempfile is materialised only AFTER all guards (overwrite picker, sanity heuristic) pass and is wiped in a `try/finally` block, so PII no longer leaks to `/tmp/linkright-paste-*` indefinitely (especially when the user picked "Keep" at the overwrite picker — that path used to leak too). A scripted equivalent is exposed as `--from-paste`; the legacy `--paste` flag (previously a "Day 2 — coming soon" stub) now aliases the same path. Empty paste produces a clean error rather than running the pipeline. New tests in `test_uat_cluster_b_medium.py` cover post-conditions on disk (metadata.yaml exists + has required fields, tempfile dir is gone, `profile status` recognises the profile) — not just mock-was-called assertions. The `_write_markdown_only_metadata` helper distinguishes the **new-profile path** (no prior `metadata.yaml` — writes the full set of live-detected fields) from the **augment / append path** (prior `metadata.yaml` exists — only bumps `n_nuggets` additively and stamps `last_updated`, NEVER touches `embedder_tier` / `embedder_model` / `dim` / `created_at` / PDF-side `source_pdf_sha256` provenance). Without that branching, augmenting an Oracle-embedded PDF profile (tier=oracle, dim=768) with `--from-markdown` in a fastembed env would silently flip the metadata label to fastembed (dim=384) while `embeddings.npz` still held 768-dim vectors, desyncing the `resume tailor` cache-tier check.
- **UAT #1 — `linkright doctor` suggested `--auto-fix` even with no fixable issues:** The closing message previously always recommended `linkright doctor --auto-fix` after any failures. Bug: if all failures were manual-only (no extractable `pip install` command), `--auto-fix` would print `"no auto-fix available"` for every row — eroding user trust. Now scans `rows` for failures with an extractable fix command and only suggests `--auto-fix` when at least one fixable failure exists. Otherwise shows: `"No auto-fix available; see the manual hints above or run linkright setup."` Fix in `cli.py:587-605`.
- **UAT #5 — Name extraction picks up greetings ("Dear Satvik Jain"):** The name heuristic in `_extract_contact` accepted any 2-4-word capitalized line with no digits/@ — so cover-letter style openers ("Dear ...", "Mr. ...", "Hi ...") got stored as the candidate's name. Added a greeting-prefix stripper covering 20+ common prefixes (Dear, Hi, Hello, Mr./Mrs./Ms./Dr./Prof., Sir, Madam, Respected, Shri, Smt., To/To:, Greetings) BEFORE applying the heuristic. Verified against 7 inputs including Indian honorifics. Fix in `profile/pipeline.py:287-318`.
- **UAT #7 — `linkright profile show` exposes internal metadata in header:** Default header showed absolute profile path, embedder tier+model+dim, and embed counts — none of which are meaningful for the user reading their own profile. Default header now shows only `Created / Nuggets / Highlights`; pass `--full` to see all internal metadata (path, embedder details, embed counts). Fix in `profile/render.py:175-194`.
- **UAT #8 — Nuggets truncated at 120 chars, hiding user's own data:** 120-char cutoff was too aggressive — bullets like `"Drove 20+ UX research sessions at American Express with compliance analysts across 6 regions, designing 3 AML capability UIs end-to-end"` (191 chars) got cut mid-sentence. Bumped default truncation limit to 240 chars (sentence-length). `--full` flag continues to disable truncation entirely. Tip line + legend updated to reflect new limit. Fix in `profile/render.py:214-228`.
- **UAT #33 — JD Analysis surfaces P0/P1/P2 requirements:** Previously the JD-analysis step ran silently; the user saw only "5 requirements identified" with no visibility into what the system extracted. New `_render_jd_requirements_panel()` in `resume/orchestrator.py` renders a Rich panel right after `step_07_phase_1_2` showing target role + strategy + requirements bucketed by importance (P0 must-have / P1 preferred / P2 optional) + top 8 JD keywords. Read-only display — does not gate the pipeline. Skipped when `LR_NO_PAUSE=1` (CI). Source: `resume/orchestrator.py:64` (helper) + `:6076` (call site).
- **UAT #34 — Cache info shows what was reused + how to inspect:** "✓ Profile cache hit — reusing 4 artifacts" was opaque. Expanded `tailor` command's cache pre-populate block in `resume/cli.py` to render in plain English which artifacts were copied (raw resume text / parsed structure / extracted nuggets / nugget embeddings), where they live (`~/.linkright/profile/`), and the recovery command (`linkright profile show`). Lines are routed through the muted "Run details" block introduced for #36. Source: `resume/cli.py:330-405`.
- **UAT #35 — Contact Info Desync fixed:** `linkright contact` writes to `~/.linkright/profile/contact.yaml`, but `step_01b_verify_contact_details` previously only merged `profile_overrides.json` on top of the parsed contact — so users who updated contact details via the dedicated `linkright contact` command saw STALE parse-time data in the tailor verify panel. Fix: precedence chain is now `profile_overrides.json > contact.yaml > parsed step_01 extract`. `load_contact()` is called inside step_01b and merged via per-key truthy check; corrupt YAML never blocks the pipeline (best-effort merge). Source: `resume/orchestrator.py:1205`.
- **UAT #36 — Pipeline Execution screen visual hierarchy:** Run ID / Output / LLM mode / Cache lines rendered at the same prominence as user-facing prompts, creating clutter at the moment the user wants to scan the next step. Recast them as a muted "Run details" block via ANSI dim (`\033[2m`) so the eye lands on the next prompt heading instead of run plumbing. Source: `resume/cli.py:380-405`.
- **UAT #38 — JD analysis moved earlier in the pipeline:** Previously `step_07_phase_1_2` ran as step 5 of 9 (after PDF read / parse / contact verify / nugget extract / embed). Users wanted to see the system's JD interpretation immediately after providing input; nuggets crunched silently for 30-60s before any JD acknowledgement. New order: PDF read → parse → contact verify → **JD load + analyze + requirements panel (#33)** → nuggets extract → embed → embed reqs → role scoring. `step_07` only needs `jd_text + raw_text` (no nuggets), so the move is safe; `step_06` (role scoring) still runs after `step_03` (embed nuggets). Step indices renumbered 1-9. Source: `resume/orchestrator.py:6052-6182`.
- **UAT #39 — Strategy Review surfaces layout fit insights:** `_strategy_review_gate` previously showed only company inclusion + bullet counts. Users couldn't trust the 1-page fit until the PDF rendered. New helper `_estimate_section_heights()` computes a per-section mm estimate (Header/Summary/Experience/Education/Skills/Projects) anchored on `fit_loop.py`'s exact ELEM dict (header_block=21.34mm, bullet_line=4.52mm, page=271.6mm). Strategy Review now renders: per-section mm/% of page + a unicode bar, total page utilization %, and a HIGH/MEDIUM/LOW 1-page fit probability tag aligned with fit_loop's IDEAL band (85-92%). LOW fit triggers a contextual warning (overflow >105% → suggest dropping bullets; sparse <75% → suggest adding a project/skill row). Heuristic operates on the structured plan (pre-render), but mirrors the post-render util math element-for-element so the user sees the same band the renderer will. Source: `resume/orchestrator.py:148` (helper) + `:305` (render block) + `:6292` (call site).
- **UAT #39 follow-up (Cluster C cycle 2) — heuristic re-calibrated against fit_loop truth-source:** The cycle-1 `_estimate_section_heights()` used a 47-line A4 capacity heuristic that miscalibrated by ~22% versus the prod renderer (which uses 271.6mm ÷ 4.52mm/bullet ≈ 60 bullet-equivalents). Empirical tests showed a 45-bullet plan inside fit_loop's IDEAL 85-92% band reporting LOW @ 144.7% (false overflow) while a 25-bullet sparse plan reported HIGH @ 102% (false confidence) — directly inverting the Truth-Engine intent. Re-implemented to mirror `fit_loop._estimate_util_from_html` element-for-element: same ELEM mm dict, same CHARS_PER_LINE=120 (was 75), same 271.6mm page height. HIGH band tightened from 85-105% to 85-92% so cycle-1 HIGH no longer accepts plans fit_loop flags as over-utilized. Added regression tests pinning the 25/30/45-bullet cases to fit_loop math so future drift gets caught.
- **UAT #39 polish (cycle 2) — Strategy Review trimmed of JD-panel redundancy:** Target / Strategy / Top JD keywords rows were duplicated between the new JD requirements panel (#33) and the strategy gate, ~30s apart. Strategy gate now shows a single "For: <role>" header and skips the duplicate Strategy / Keywords rows — the gate's purpose is plan + layout fit, not JD recap. Cleaner scan path.
- **UAT #34 polish (cycle 2) — cache hint respects `$LINKRIGHT_HOME`:** Cache-hit message hardcoded `~/.linkright/profile/` literal even for users with a custom `LINKRIGHT_HOME`. Now interpolates the resolved `profile_dir_for_msg` Path, rendering with `~` when under HOME and absolute otherwise.
- **UAT bug-log status sync:** Marked Fixed in `harness/UAT_BUG_LOG.md` for #33, #34, #35, #36, #38, #39. Cluster Tracker reflects Cluster C ✅ SHIPPED.
- **UAT #25 — Nugget pool pollution (static facts mixed with experience):** Added a deterministic `nugget_class` field (`fact` / `experience` / `skill`) stamped on every nugget at persist time. `fact` covers `education`, `certification`, `award`, `language`, `publication`, `interest`, `course`, `voluntary`, `organisation`, `summary` — these are static reference data that should not feed the JD-aligned bullet retrieval pool. `skill` is its own tier (Python / SQL / etc.) feeding the skills block, not the bullet block. `experience` is the default for `work_experience` and `independent_project` plus any unrecognised type (defensive — legacy nuggets without a type field don't silently disappear from retrieval). Helper in `profile/nugget_utils.py:class_of`; `classify_in_place()` backfills on every persist. **Cycle-2 wiring (PR #165 round-2 BLOCK fix):** `step_08_retrieve_per_company` (in `resume/orchestrator.py`) now filters the cosine-ranking pool to `class_of(n) == "experience"` BEFORE company-bucket grouping, so fact / skill nuggets — even when they carry a matching `company` field — never compete with achievement bullets for JD-aligned retrieval slots. Legacy nuggets without `nugget_class` default to "experience" (zero backward-compat risk). Tests in `tests/test_uat_cluster_d.py::TestNuggetClassification` (8 cases incl. end-to-end persist check) and `::TestStep08RetrievalPoolFilter` (2 cases: skill-class-with-matching-company excluded; legacy-no-class still pooled).
- **UAT #26 — Improper nugget ordering (P0s landing at the bottom):** Added `sort_by_priority()` (stable sort, P0 → P1 → P2 → P3 → unknown) applied at every read/write site: `pipeline.persist()` rewrites `nuggets.jsonl` in priority order; `enrich.append_nuggets()` reads existing rows, merges new ones, re-sorts, rewrites both `nuggets.jsonl` AND `highlights.jsonl` (the old append-only path caused freshly-enriched P0 nuggets to land at the end of the file and render last under their company on `profile show`); `render.show_profile()` applies the sort before grouping into the tree. Stability is critical — within the same priority bucket the LLM's extraction order is preserved, so users don't see priority ordering randomly shift between runs. Tests cover sort correctness, stability, unknown-importance handling, and end-to-end persist verification.
- **UAT #27 — Entity extraction failure (LLM says "unknown" / "none"):** Deterministic fallback resolver in `profile/nugget_utils.py:resolve_entity`. When the Groq 70B nugget extractor emits `company: none` (or `unknown`, `null`, `n/a`, `tbd`) on a work_experience nugget, three strategies run in order: (1) match against `parsed["companies"]` from step_01 — if a company name appears verbatim in the nugget's `answer`, fill it in (also fills `role` when the parsed title matches the answer); (2) "at <Company>" pattern in the answer with verified containment in raw resume text (anti-fabrication: never invent a name that isn't on the resume); (3) silent skip when nothing matches. Critically, never overwrites a non-missing value — preserves LLM-set company/role even if the parser disagrees. Audit-trail flag `_entity_resolved_by` records which strategy fired. Called in `pipeline.parse_and_extract()` between embed and persist.
- **UAT #28 — Missing "Gap-Filling" loop:** Added `gap_filling_targets()` helper that scans the freshly-extracted nugget batch for `work_experience` rows missing `company` or `role`. Skips `independent_project` (conventionally no company) and skill / fact classes (different curation flows). Bounded at 5 gaps surfaced per pipeline run — never displays a 30-question inquisition. Result attached to `parse_and_extract()` return dict as `gaps`; CLI's `create_cmd` surfaces them as a numbered warning list pointing users at `linkright profile enrich` / `linkright profile audit` for follow-up. Under `--yes` / non-TTY paths the same warning prints (no interactive blocking). **Cycle-2 fix (round-2 BLOCK CRITICAL #1):** dropped `dates` from the gap-fields tuple. The `NUGGET_EXTRACT_MD` prompt schema emits NO per-nugget date field — checking `start_date` / `date_range` on every work_experience nugget was a guaranteed false-positive that saturated the 5-cap surface on every run, turning the new gap-fill signal into noise. Dates live on `parsed.experiences[]` (role-level, not nugget-level) and belong in a future date-audit pass. Future cluster will wire a true inline prompt loop; this PR delivers the discovery surface so users at least know what's missing.
- **UAT #31 — Vague / fluff metrics (e.g., "Increased business value by 100%"):** Added `is_fluff_metric()` detector using a two-signal rule — flags must combine (a) a fluff noun (`business value`, `synergy`, `stakeholder value`, `engagement`, `productivity`, `morale`, `visibility`, `innovation`, etc.) OR a vague intensifier (`significantly`, `substantially`, `tremendously`) AND (b) a suspiciously round percentage (100/150/200/300/500/1000%) OR an `Nx` multiplier (10x, 5x). Two-signal rule keeps concrete metrics passing through unaffected: `"Increased revenue 100% YoY"` (concrete noun `revenue` → keep), `"Shipped 100% test coverage"` (no fluff noun → keep), `"Drove engagement across 6 markets"` (no number → keep). Wired into `enrich.extract_from_answer()` so the LLM-generated nugget is rejected at extraction time before it ever reaches persist. **Cycle-2 fix (round-2 BLOCK MED — silent fluff rejection):** the function now returns a sentinel dict `{"_rejected": "fluff_metric", "_preview": "..."}` instead of `None` on fluff. The caller (`enrich_session`) checks `_rejected` and renders a specific, actionable warning ("Answer rejected as fluff-metric — '...'. Try a concrete number (revenue, users, latency, hours saved).") so users can distinguish a fluff-reject from a generic LLM-call failure. Catches the documented UAT offender and the variants the LLM cycles through.
- **UAT #32 — Missing Nugget Audit / Cleanup Phase:** New `profile/audit.py` module with `run_audit()` that performs an idempotent re-pass over existing nuggets: backfills missing `nugget_class` (#25 retro for legacy profiles), re-resolves "unknown" company / role using parsed-resume headers and raw text (#27 retro), detects fluff metrics in existing rows and demotes them to P3 with `_audit_flags: ["fluff_metric"]` (#31 retro for pre-existing offenders), and re-sorts both `nuggets.jsonl` and `highlights.jsonl` by priority (#26 retro). NEVER deletes a nugget — user retains full control via `delete-nugget` and truth-engine. Idempotent at the file layer: clean profile produces zero rewrites (verified via mtime stability test). Surfaced as a new CLI subcommand `linkright profile audit` (alias `linkright profile a`) — reports counts of classified / entity_resolved / fluff_demoted / reprioritised. Useful after multiple `profile enrich` sessions accumulate noise.
- **UAT bug-log status sync:** Marked Fixed in `harness/UAT_BUG_LOG.md` for all six bugs landed in this PR (#25, #26, #27, #28, #31, #32). Progress count bumped to 21/40 fixed, 18 pending, 1 deferred. Cluster D entry updated from "Pending" to "✅ THIS PR".
- **Cycle-2 polish (round-2 BLOCK HIGH + LOW):** Added 2 CliRunner tests for `linkright profile audit` covering both the success path (fluff P0 → demoted to P3 on disk, exit 0, "Profile audit complete." message) and the no-profile path (exit 1, "No profile found" in output). Per `feedback_clirunner_test_mock_assertions.md`, each test asserts `exit_code` AND a post-condition. Persist now strips the transient `_entity_resolved_by` debugging field from `nuggets.jsonl` (in-memory only) so the on-disk shape stays clean — re-running audit re-sets it when entity resolution fires.
- **UAT #5 hardening — Indian + regional honorific prefixes:** Cluster B-small (PR #159) added `dear / mr. / mrs. / sir / respected / shri / smt.` prefix stripping to the name-extraction heuristic. This polish extends the prefix list to cover regional + religious + honour titles commonly found on Indian-market certificate-style PDFs: `thiru`, `thiruvalar` (Tamil Mr.), `rev. / fr. / sis.` (religious), `hon. / honorable / honourable`, `late` (deceased). All these markers modify the SAME person named on the line, so stripping is safe. Strengthens defense against bug #5 root cause for the broader user base. Fix in `profile/pipeline.py:296-307`.
- **UAT #5 — relationship-marker line rejection (AR-1 adversarial review fix):** Pre-merge adversarial review caught that `s/o / d/o / w/o` (son-of / daughter-of / wife-of) markers indicate the line names a RELATIVE of the candidate, NOT the candidate themselves. Stripping these prefixes and storing the remainder would store the FATHER / MOTHER / HUSBAND's name as `candidate.name` — data integrity bug. Verified PoC: `"S/o Mr. Rajesh Jain"` → strip cycle → `"Rajesh Jain"` (the father). Fixed by introducing a separate `_REJECT_LINE_PREFIXES` set (`s/o`, `d/o`, `w/o`, `h/o`, `son of`, `daughter of`, `wife of`, `husband of`, `father's name`, `mother's name`, `spouse's name`) — relationship-marker lines are now SKIPPED entirely during name extraction. Fix in `profile/pipeline.py:309-326`.
- **UAT #10 — `profile create` interactive picker simplified:** Removed the "Folder containing my resume (auto-detect first PDF)" option from `prompt_for_resume_source` — the secondary option added complexity without serving the typical user. Power users who want folder mode can still pass `--from-folder` on the command line; the flag stays available, just no longer surfaces as an interactive choice. Default `flag_hint` updated from `"-r/--resume / --from-folder"` to `"-r/--resume"`. Fix in `prompts/__init__.py:377-401`.
- **UAT bug-log status sync:** Marked Fixed in `harness/UAT_BUG_LOG.md` for all bugs landed in PRs #157 (A: #4, #37, #40), #158 (E1: #18, #23, #24), #159 (B-small: #1, #5, #7, #8), and this PR (#5 hardening, #10). Added Progress section showing 11/40 fixed, 28 pending, 1 deferred. Updated Cluster Tracker section with current sub-PR breakdown (B-small/B-medium/B-truth-engine/E1/E2/E3/E4).

### Changed
- **UAT #17 — Tab navigation complete fix (two-tier label design):** Tabs are now the **default** picker for all `prompt_for_choice` calls with ≤ 6 options — no env var required. Opt-out with `LR_PICKER_STYLE=list` to force questionary's vertical select (useful for accessibility or CI environments where arrow keys are unavailable). Removed the previous 30-char label gate, replacing it with a two-tier label model: every option carries a short `label` (≤ 15 chars, shown in the tab bar) plus an optional `description` (shown on the line below when the tab is focused — progressive disclosure). `tab_navigate()` gains a `descriptions` parameter; focused tab renders `└ <description>` in muted style via a taller `prompt_toolkit` window (height 3 when descriptions present, 2 otherwise). Refactored all picker option dicts in `setup_wizard.py` (`EMBEDDER_OPTIONS`, `PDF_OPTIONS`, `MODE_OPTIONS`) and in `prompts/__init__.py` (`prompt_for_jd_input`, `prompt_for_resume_source`) to use the new `label` + `description` split. Updated test suite in `tests/test_uat_cluster_e2.py`: replaced the obsolete `LR_PICKER_STYLE=tabs` opt-in test and 30-char gate test with updated tests for (a) tabs-by-default behaviour with description forwarding, (b) `LR_PICKER_STYLE=list` forced questionary fallback, (c) 7-option overflow fallback, (d) updated `_tab_picker_eligible` boundary (≤ 6, no char limit), and (e) non-TTY fallback rendering descriptions inline. Resolves UAT bug #17 fully.


## [0.9.2] - 2026-05-12

### Added
- **S6.1 (interactive strategy checkpoint):** Pipeline now pauses after JD analysis to show the strategy (company list, bullet budget, top keywords) and asks for confirmation before the 60-LLM-call bullet generation phase. Press Enter to proceed or N to abort cleanly. Skipped in non-interactive mode (LR_NO_PAUSE=1).

### Fixed
- **S6.2 (CLI polish omnibus):** `tailor --help` groups advanced flags (`--llm-mode`, `--run-id`, `--no-cache`, `--deterministic`, `--seed`, `--no-pause`) with `[Advanced]` prefix and clarifies that `agent` mode requires an external CLI tool (claude, opencode, or gemini). `profile show` replaces literal `none` values with `(untitled)` in the nugget tree. `profile status` shows PDF filename + modified date instead of raw SHA256 (SHA256 moved to `--debug` output); contact fields show `(not set)` instead of literal `none`. Help text jargon removed (`16-step pipeline` comment → plain language). Bullet dedup pass after ranking removes near-duplicate bullets (cosine >0.88 on `_emb` vectors) before condensing; skips silently when embeddings are absent.


## [0.9.1] - 2026-05-12

### Added
- **S5.2 Phase 0 (input hash instrumentation):** `16_telemetry.json` now records `input_hash` (sha256 of resume bytes + JD bytes + pipeline version, length-prefixed to prevent boundary collisions) per run. After 1 week of passive collection, hit rate is measured to gate Phase 1 (actual output caching). No behaviour change for users.
- **S5.6 (Cross-bullet verb coherence enforcer):** Added `resume/lib/coherence.py` with `enforce_verb_coherence()` that detects duplicate leading verbs within a section, rephrases via Oracle gemma3:1b, and reverts if the rephrase is structurally unsound. Runs after step_11 ranking, before step_12. Oracle unavailable → skips silently.

### Fixed
- **CLI keys polish:** Replace `key(s)`/`provider(s)`/`slot(s)` with correct singular/plural throughout `keys add` output. Add duplicate key-value warning — if the same API key is entered twice across slots, user sees `⚠ This key value is already saved as <slot>` instead of silent overwrite.
- **Hotfix (path prompt spaces):** `_sanitize_path_input` no longer truncates unquoted paths containing spaces (e.g. `Ruch_ Dubey_Resume.pdf`). shlex decoding is now applied only when the input uses shell quoting or backslash escapes; bare unquoted paths are passed through verbatim.
- **S5.0 (Pre-flight guards):** Commands now check for required artifacts before dispatching any pipeline logic. `resume tailor` and `cover-letter` guard profile + LLM key; harness commands (`improve`, `fill-metrics`, `practice`, `strategy-review`, `critique`) guard profile + prior tailor run; `profile create` guards PDF readability. Users see a clear "run X first" message instead of a Python traceback.
- **S5.0 polish (pre-flight guards):** Extended require_llm_key to check raw shell env vars (GROQ/GEMINI/CEREBRAS/SAMBANOVA/CLOUDFLARE/OPENROUTER/ZHIPU/Z_AI) in addition to linkright-managed .env — prevents false-block for users with keys set outside linkright. require_tailor_run now uses pipeline artifact sentinel (16_telemetry.json or 14_final_resume.html) instead of dir existence — avoids false-pass on partial/crashed runs. Added require_profile + require_llm_key guards to cover-letter command. Split ImportError from corrupt-PDF exception in profile create.


## [0.9.0] - 2026-05-12

### Added
- **S5.1 (Embedding-based JD-bullet alignment):** step_11_rank now blends BRS score (70%) with Oracle nomic-embed-text cosine alignment (30%) when jd_req_texts are available. Req texts are auto-derived from jd_requirement_clusters canonical_labels when not provided explicitly. Each bullet receives a `_alignment_score` field for telemetry. Semantically richer ranking that adds approximately N Oracle embed calls per run (one per bullet, typically 15-25 calls for a standard resume) when Oracle is live; graceful fallback to BRS-only when Oracle is unreachable or returns empty. Oracle is self-hosted (free), so there is no additional monetary cost, but call count does increase. 7 new tests in tests/test_jd_alignment_embedding.py (all pass).
- **S5.5 (Progressive validation gate):** Added `_should_regenerate()` BRS threshold gate (default 0.60, env: `LR_BRS_THRESHOLD`) between fabrication guard and step_12. Bullets below threshold are flagged `_below_threshold`; success box warns "N bullets below quality threshold" when present.
- **S5.7 Phase 0 (Fabrication guard instrumentation):** Added `_log_guard_decision()` helper that writes `(bullet, source, decision, ts)` triplets to `~/.linkright/training-data/fabrication-guard/<run_id>.jsonl` after each guard evaluation. Passive data collection for future fine-tuning. Never crashes the pipeline (all exceptions silently swallowed).

### Fixed
- **S5.3 (JD keyword contamination fix):** step_07 now strips keywords absent from raw JD text via structural filter; extraction prompt updated with explicit negative instruction. Prevents resume-sourced terms from inflating JD-alignment scores.

### Changed
- **S5.4 (Career level → pure deterministic):** Removed LLM retry loop for career_level in step_07. Classification now always uses `_bucket_from_years(total_years)` — zero run-to-run variance, one fewer API round-trip on mis-classified inputs.


## [0.8.0] - 2026-05-12

### Added
- **S4.1 (Peer-vs-applicant language bank):** Added seniority-tone calibration for
  step_10 bullet generation. New `peer_applicant_bank.yaml` (86 phrase entries across
  3 bands: junior/mid/senior) and `peer_applicant.py` lib map `career_level` → tone
  band and inject a structured verb-guidance section into the PHASE_4A_VERBOSE_SYSTEM
  prompt. Senior/executive candidates now get peer-to-panel verbs (co-led, championed,
  evangelized); junior candidates get strong-contributor verbs (shipped, built, drove).
  Fabrication safeguard preserved: guidance instructs LLM to use verbs only where
  evidence naturally supports it.
- **S4.2 (Career-level vocabulary profile):** Extended `verb_taxonomy.yaml` with a new
  `career_level_preferences` top-level section defining three verb buckets — authority,
  credibility, and energy — for five career levels (fresher / early_career / mid / senior /
  executive). Added `get_career_level_verb_prefs(career_level)` and
  `format_career_vocab_guidance(career_level)` to `verb_taxonomy.py` with alias
  normalisation (e.g. "entry" → early_career). Injected the formatted guidance into the
  `step_10_verbose_bullets` system prompt so the LLM calibrates verb tone by seniority:
  executives get "Oversaw / Governed / Stewarded", mid-level gets "Drove / Optimized /
  Scaled", freshers get "Built / Shipped / Launched". The existing `load_verb_taxonomy`
  is protected from the new section via an explicit skip guard.
- **S4.3 (Metric-magnitude consistency):** Bullets that mix wildly different magnitude tiers (e.g. "5% overhead on a $50B platform") are now penalised up to 15% in step_11 BRS ranking, so recruiters see the most credibly-scoped achievements first.
- **S4.4 (Success box quality signals):** After `linkright resume tailor` completes, the success
  box now shows two quality signals alongside the PDF path and duration:
  `JD Coverage` (X/Y reqs covered, %) read from `artifacts/06_role_scores.json`, and
  `Width hits` (X/Y bullets in 108-120 char target band, %) read from the `width_poc` block
  in `artifacts/16_telemetry.json`. Values below 80% render in coral (#FF5733) as a visual
  warning. Both fields are omitted gracefully when the artifact files are absent or malformed
  (no crash). Adds `_read_quality_metrics()` and `_fmt_metric_value()` helpers to
  `resume/cli.py`. Tests in `tests/test_success_box.py` (17 passing: AC1-AC4).

### Fixed
- **S4.5 (Success box path wrap):** Fixed `linkright resume tailor` success card
  showing the PDF path mid-word wrapped across lines. `_render_success_card` in
  `resume/cli.py` now passes the filename and full path as two separate lines
  (`filename\nfull_path`). `success_card()` in `ui/__init__.py` was updated to
  handle multi-line field values: the first line renders on the key row in accent
  colour, and continuation lines are indented to the value column and rendered
  dimmed. Rich `Text(overflow="fold")` is used for the panel body so that even
  on 80-col terminals the filename component is never broken mid-word (fold only
  occurs at path-separator boundaries). 15 new tests in
  `tests/test_success_box_render.py` verify no mid-word wraps at 80, 100, and
  120 col widths via both the helper primitives and the `success_card()` module
  function.


## [0.7.0] - 2026-05-11

### Added
- **S3.1 (Signal-weighting matrix):** 13-signal × 5-career-level multiplier matrix; step_11 bullet ranking now weights signals differently per career level so executive resumes surface executive-influence bullets first.
- **S3.2 (JD requirement clustering):** Cosine-similarity clustering groups semantically-related JD requirements (e.g. "communicate" + "collaborate" + "stakeholder alignment" → one cluster); step_11 ranking scores against clusters not individual reqs, eliminating keyword-stuffing and reducing LLM calls.
- **S3.4 (Markdown profile ingestion):** Adds `--from-markdown <file.md>` flag to `linkright profile create`.
  Long-form career narrative documents (Obsidian exports, diary-style prose, 95KB career profiles)
  can now be ingested into the nugget store without manual copy-paste.
  New `markdown_ingest.py` module handles: ATX-heading-based chunking, section classification
  (career-relevant / personal-life / mixed), privacy gate (personal-life sections skipped by default,
  `--include-personal` to opt in), one LLM call per chunk (never one giant prompt), deterministic
  Jaccard dedup (≥0.8 token-overlap against existing nuggets), token budget guard (≤50 LLM calls
  per run ≈ 25% of hourly Groq free-tier limit), and end-of-run privacy audit log (sections skipped,
  nuggets extracted, nuggets deduped). Unit tests in `tests/test_markdown_ingest.py` use a minimal
  synthetic document — no real personal data.

### Fixed
- **S3.3 (Truth Engine Layer 1):** Personal-details verification prompt at pipeline start; checks professional email format + LinkedIn slug quality; user can edit/skip each field; --no-pause / LR_NO_PAUSE=1 bypasses for CI/scripted use.
- **S3.3 Blocker 1:** step_01b_verify_contact_details now silently skips on non-TTY stdin (MCP/pipe mode) and catches EOFError from questionary — no more crash in MCP subprocesses.
- **S3.3 Blocker 2:** save_contact() now calls mkdir(parents=True, exist_ok=True) before writing contact.yaml — edits no longer silently lost when ~/.linkright/profile/ doesn't exist.
- **S3.3 Blocker 3:** _UNPROFESSIONAL_WORDS regex now uses \b word boundaries — hotel.manager, catherine.james, radical.ideas no longer false-positive; hotgirl99 still warned (via digit detection; compound words without separator e.g. hotguy are a known gap — rare edge case).


## [0.6.0] - 2026-05-11

### Added
- **S2.1 (Acronym expansion bank):** Pre-stored 293 acronyms across 12 industry domains; step_14 now resolves known acronyms from the bank before falling back to per-run LLM lookup, cutting LLM calls for common acronyms to zero. (#124)
- **S2.2 (Domain verb prefix maps):** Pre-stored strong-verb prefix maps for 8 industry domains; step_10 now deterministically replaces weak verbs (worked/helped/assisted/supported/participated/contributed/involved/utilized/leveraged) without an LLM retry loop. Industry inferred from job title at each company. (#125)
- **S2.3 (Verb taxonomy):** 2D impact-category × industry verb matrix (720 entries, 9 categories × 8 industries × 10 verbs); step_10 now selects verbs matched to both the bullet's achievement type and the candidate's industry domain. S2.2 flat list retained as fallback. (#126)

## [0.5.24] - 2026-05-11

### Added
- **S1.12 (EXPAND mode in page-fit loop):** `fit_loop.py` now detects page
  under-utilization (< 85% of an A4 page) and runs expand strategies before
  declaring success.  Two new strategies:
  - `E1_expand_bullets` (iter 0): increments each company's bullet count by 2,
    capped at 8 per company — surfaces more achievements when the page has room.
  - `E2_surface_projects` (iter 1): removes `Projects` from `dropped_sections`
    and allocates up to 3 project bullets — re-surfaces the Projects section
    when there is measurable space remaining.
  Expand strategies fire ONLY when `util_underflow=True` (util > 0% AND < 85%)
  AND the page is 1-page, unwrapped, and not overflowing — never into a wrapping
  or overflow state. `util_pct=0.0` (no HTML signal) is treated as "no signal"
  so missing-HTML passes still succeed.
- **S1.12 fix in `orchestrator.py`:** `projects_total` is now defaulted to
  `min(3, n_projects)` at the S5-2 bullet-distribution step when the Projects
  section is included in section visibility but the LLM hint omitted the key —
  prevents the Projects section rendering with zero bullets.

## [0.5.23] - 2026-05-11

### Added
- **S1.8 (CLI terminal UI consistency):** `linkright/ui.py` promoted to
  `linkright/ui/` package with two new submodules:
  - `ui/theme.py` — `LR_THEME` Rich theme with 10 named style aliases
    (brand.primary `#4285F4`, brand.secondary `#EA4335`, metric.positive
    `#34A853`, text.secondary `#5F6368`, divider `#DADCE0`, + 5 more)
  - `ui/patterns.py` — 6 rendering primitives: `picker()`, `status_event()`,
    `insight_block()`, `code_block()`, `progress_indicator()`, `tree_branch()`
- All existing `ui.*` public names re-exported from `ui/__init__.py` — zero
  import breakage for callers.
- `doctor` command migrated from raw ANSI escapes (`\033[32m`) to Rich
  `status_event()` calls — output is now colour-safe and respects `NO_COLOR`.
- All `profile/` `Console()` instances updated to `Console(theme=LR_THEME)`.
- `step_done()` and `step_start()` now honour their `accent` parameter.
- 11 new tests in `tests/test_cli_ui_snapshot.py`.

## [0.5.22] - 2026-05-11

### Fixed
- **S1.7 (suppress HF Hub warning leak):** `linkright/__init__.py` now sets
  `HF_HUB_DISABLE_PROGRESS_BARS=1` and `TOKENIZERS_PARALLELISM=false` via
  `os.environ.setdefault` (preserves user overrides), and raises `huggingface_hub`,
  `tokenizers`, and `fastembed` loggers to `ERROR` level before any lazy import
  can trigger them. Prevents progress bars and auth-token warnings from
  appearing in the user's terminal during profile/embed operations.
  7 new tests added (`tests/test_hf_warning_suppression.py`).

## [0.5.21] - 2026-05-11

### Fixed
- **S1.4 (setup --check Groq false-negative):** `run_check()` now calls
  `read_all_managed()` before falling back to `os.environ`, so keys stored via
  `linkright keys add groq` (in `~/.linkright/.env`) are resolved correctly.
  Previously the check showed `✗ not set` even though the pipeline worked.
  8 new unit + integration tests added (`tests/test_setup_check_groq.py`).

## [0.5.20] - 2026-05-11

> Note: 0.5.18 is reserved — claimed by S1.1 (PR #116) and S1.2 (PR #117)
> which branched from the same 0.5.17 base. Whichever merges last must rebase
> to the next available version above the highest merged version.

### Fixed
- **S1.5 (GenAI acronym expansion error):** Moved `_UNIVERSAL_NO_EXPAND` to a
  new shared module `resume/data/no_expand.py` — single source of truth imported
  by both `orchestrator.py` and `scorecard.py`, so the two enforcement layers
  can never drift apart again. Added ~25 AI/ML terms (`GenAI`, `LLM`, `NLP`,
  `MCP`, `RAG`, `GPT`, `BERT`, `GAN`, `MLOps`, `AIOps`, `NLU`, `NLG`, `XAI`,
  `OCR`, `NER`, `OAuth`, `JWT` + others). All 4 no-expand check sites in
  orchestrator now use case-insensitive `_UNIVERSAL_NO_EXPAND_UPPER` to block
  lowercase corpus variants. `_COMMON_KNOWN_ACRONYMS` in scorecard is now a
  direct alias to `_UNIVERSAL_NO_EXPAND` — the identity is enforced by a test.

## [0.5.19] — 2026-05-11

### Fixed
- **S1.2 — fabrication guard stripping real action verbs:** The JD-fishing guard
  in `lib/jd_keyphrase.py` was flagging universal resume action verbs (led, drove,
  managed, built, launched, etc.) as fabricated JD-fishing terms because they
  appear in JD text but may not appear verbatim in source nuggets. The guard was
  designed for domain-specific acronyms (SOX, GDPR, Kubernetes), not generic
  action verbs. Fixed by adding ~80 action verb forms (base, past, progressive,
  plural) to `_STOPWORDS` — they are now transparent to both the resume and
  cover-letter guards. Domain-specific terms like SOX and GDPR still fire
  correctly. 15 new unit tests in `tests/test_fabrication_guard_verbs.py`.

## [0.5.18] — 2026-05-11

### Fixed
- **S1.1 — experience years rounding + fresher-drop:** Summary now uses
  `max(1, math.ceil(total_years))` for non-fresher candidates, so a 4.7-year
  candidate writes "5+ years" instead of "4+ years" and passes adjacent
  year-band JD filters (e.g. "5-7 years" job postings). For `career_level ==
  "fresher"` (total_years == 0, set deterministically by the B1 consistency
  check), the years phrase is omitted entirely from the summary — fixing the
  "0+ years of experience" bug from QA. The B2/F01 hallucination validator is
  also tightened: ceiling-rounded `display_years` replaces the loose
  `user_total_years + 1.0` tolerance. Covered by 13 new unit tests in
  `tests/test_experience_rounding.py`.

## [0.5.17] - 2026-05-11

### Fixed
- **S1.3 (hide internal step names in spinner):** `logbook._verb_for()` fallback
  changed from `f"⚙️  Running {step_name}"` to `"⚙️  Processing..."` — raw
  internal step identifiers (e.g. `step_07_phase_1_2`, `run_start`) no longer
  leak to the user's terminal when a step has no explicit friendly-verb mapping.
  Added `"run_start"` → `"🚀 Starting pipeline"` to `_STEP_VERBS` so the pipeline
  init message is also human-readable.

## [0.5.16] — 2026-05-11

### Fixed
- **PKG-1 REGRESSION (CRITICAL):** HTML resume templates (`resume/templates/*.html`, `templates/*.html`) were re-dropped from the wheel during PR #112's rebase — `package-data` entry from PR #109 (v0.5.13) was inadvertently reverted. v0.5.13/0.5.14/0.5.15 wheels all crash at step 14 with `FileNotFoundError: cv-a4-mid-career.html`. This hotfix restores `"resume/templates/**", "templates/**"` to `[tool.setuptools.package-data]`. Verified locally: wheel built from this commit contains all 4 HTML templates under `linkright/resume/templates/` + the standard template under `linkright/templates/`.

## [0.5.15] — 2026-05-11

### Fixed
- **S1.10 (redo, iter 2):** LinkedIn and Portfolio in resume header now render as
  anchor-text hyperlinks (`<a href="...">LinkedIn</a>` / `<a href="...">Portfolio</a>`)
  instead of full URL strings. Fix applied to **both** render paths:
  - `orchestrator.py` `step_14` post-processor (mid-career template / `linkright tailor`)
  - `linkright/mcp_sync/tools/assemble_html.py` `_create_contact_link` (MCP / `linkright mcp serve`)
  Previously only `linkright/tools/assemble_html.py` was patched; `mcp_sync` path still used
  `color: inherit` (inherits `.contact-info` secondary gray `#5F6368`) and rendered raw URL as
  link text. Both paths now use `var(--ui-text-primary-color)` (resolves to `#202124` per
  Google Material body token — canonical "black" in brand-design-spec rule 2) and render label
  text ("LinkedIn" / "Portfolio"), not the raw URL.
  `_create_contact_link` in `mcp_sync` updated: `anchor_text=""` back-compat parameter added;
  empty URL → returns `""` (caller skips span); URL without scheme → `https://` prepended.
  `_replace_header_content` in `mcp_sync` updated: passes `anchor_text=label` for linkedin/
  portfolio; skips empty-URL spans; omits `<strong>Label</strong>:` prefix for those types.
  **Placeholder mismatch (Blocker 2):** `orchestrator.py` now emits a user-visible
  `sys.stderr.write(...)` warning (previously silent `warnings.warn` — swallowed by callers)
  AND performs partial substitution — fills N placeholders with the first N contact fields
  instead of silently skipping all 4 when the template has fewer than 4 markers.
  `re.DOTALL` flag on S1.10 regex (defensive against newline in URLs).
  Empty URL → no orphan anchor (S6-2 stripper handles; `_create_contact_link` returns "").
  URL without scheme → `https://` prepended defensively.
  Tests at `tests/test_contact_hyperlinks.py` — Section D added covering `mcp_sync` import
  path explicitly (`from linkright.mcp_sync.tools.assemble_html import _create_contact_link`),
  Section E covering partial placeholder substitution + stderr warning.

## [0.5.14] — 2026-05-11

### Fixed
- **S1.9 (iter 3 — NameError on fallback path):** `step_14_assemble_html` referenced `raw_text` as a free name inside the `if not _p12_companies:` fallback block, but `raw_text` was not a parameter of the function — only a local variable in `main()`. When step_07 exhausted all LLM providers the fallback fired and crashed with `NameError: name 'raw_text' is not defined`. Fixed by adding `raw_text: str = ""` to the function signature (default-empty for backward compat) and passing `raw_text` at the call site (`orchestrator.py:5401`). Two regression tests added (tests 13–14 in `test_location_truth_guard.py`): signature introspection guard + fallback-path simulation with empty companies dict.
- **S1.9 (iter 3 — null date_range in step_10):** `co.get("date_range", "")` at step_10 call site (`orchestrator.py:1935`) returns `None` when LLM emits `null`. Changed to `(co.get("date_range") or "")` matching the pattern applied in iter-2.
- **S1.9 (iter 2 — header-context validator):** iter-1 used a naive full-text substring scan for location validation (`_loc in raw_text`). This allowed context-pull false negatives: a city name appearing in a bullet body ("collaborated with NY risk team") would validate as a real role location. Fixed by replacing the scan with a header-context validator (`loc_in_header` in `resume/lib/location_guard.py`). Header-context validator strips locations not present in role-header lines. Substring matches in bullet narrative do NOT validate; only header-row presence does.
- **S1.9 (Blocker 2 — fallback reconstruction path):** the fallback companies list in `step_14_assemble_html` (triggered when step_07 LLM exhausts all providers) now runs `loc_in_header()` on every experience location before including it. Added invariant callable-check assertion so future readers see the structural dependency.
- **S1.9 (Blocker 3 — null date_range):** `co.get('date_range', '')` returns `None` (not `''`) when the LLM emits `"date_range": null`. An f-string then renders `"Gurugram | None"`. All dict-get calls in HTML assembly now use `(co.get('field') or '')` pattern.
- **HTML template:** when location is empty after validation, renders `<span>{dates}</span>` alone — no leading ` | ` separator, no orphan artifacts.
- **Prompt hardening (PHASE_1_2_SYSTEM):** location field schema hint updated to "VERBATIM from a role-header line ONLY (format: Company | Location | Dates)". Parsing rules section adds explicit instruction: location MUST appear in a role-header line; body-context mentions do not validate; never invent.

## [0.5.13] — 2026-05-11

### Fixed
- **S1.10 (redo on canonical repo):** LinkedIn and Portfolio in resume header now render as
  anchor-text hyperlinks (`<a href="...">LinkedIn</a>` / `<a href="...">Portfolio</a>`)
  instead of full URL strings. Applies to the mid-career template via the `step_14`
  post-processor path in `orchestrator.py`, and via the `assemble_html` MCP tool
  `_create_contact_link` for agent-driven usage. `TEMPLATE_PATH` is hardcoded to
  `cv-a4-mid-career.html` — other templates reached via `assemble_html` MCP only.
  Anchor color uses `var(--ui-text-primary-color)` (resolves to body black) per
  brand-design-spec rules 2+4 — no brand blue (`#4285F4`) on contact text.
  `re.DOTALL` flag added to S1.10 regex (defensive against newline in URLs).
  `warnings.warn` fires when fewer than 4 `<!-- PLACEHOLDER -->` markers found.
  Empty URL → no orphan anchor (S6-2 stripper handles; `_create_contact_link` returns "").
  URL without scheme → `https://` prepended defensively.
  35 tests committed at `tests/test_contact_hyperlinks.py`.

## [0.5.12] — 2026-05-11

### Fixed
- **F-S1.11 (iter-2)**: Education section year-placeholder sanitization — three root-cause gaps closed:
  1. `_parse_education` in `md_parse.py` now calls `_sanitize_year()` at parse time (same as projects). LLM-emitted `"Year"` literal from the RESUME_PARSE_FALLBACK prompt was reaching the HTML renderer unchecked.
  2. Orchestrator education render site now calls `_sanitize_year()` as defense-in-depth, catching values that arrive via the step_07 LLM JSON path (bypasses md_parse).
  3. `RESUME_PARSE_FALLBACK` prompt Education example and format rule updated: example changed from `| Year` to `| 2024`; rule extended with "NEVER write the literal word 'Year' — output only Degree | Institution if no year is present".
- **DRY**: Inline `re.compile` + `import re as _re` inside `_project_line` hot-path replaced with the shared `_sanitize_year` import from `md_parse`. Single regex source of truth.
- **Tests**: Added `tests/test_year_sanitization.py` (37 tests) covering all placeholder variants, real-year passthroughs, and integration paths for both Education and Projects parse → render chain. All 37 pass.

## [0.5.11] — 2026-05-10

### Fixed
- **UX-11**: `linkright tailor` — no longer asks for resume when profile exists. Auto-detects `~/.linkright/profile/inputs/resume.pdf` (or `.md`) and uses it silently. Prompt only shown if no profile has been built.
- **UX-12**: `linkright tailor` JD prompt now offers 3 options: (1) path to a JD file, (2) paste JD inline, (3) pick from saved jobs in Oracle DB (`linkright jobs find` feed). Discovery option fetches `jd_text` from `sync.linkright.in/api/discoveries/<id>` and stages to a temp file.

## [0.5.10] — 2026-05-10

### Fixed
- **PROMPT-3**: Removed hard nugget count target (25–45) from `NUGGET_EXTRACT_MD` and orchestrator. Count is now purely resume-content-driven. Hard target caused LLM fabrication risk (SampleCo incident root cause). Gaps threshold lowered to `< 3` (genuine failure signal only).

## [0.5.9] — 2026-05-10

### Changed
- **UX-10**: Career-journey gradient banner — LINKRIGHT ASCII art flows Teal→Purple→Sage→Pink left-to-right, each color zone mapping to a product pillar (Resume→JobSearch→Interview→Social). Per-column linear RGB interpolation, identical technique to Gemini CLI.

## [0.5.8] — 2026-05-10

### Changed
- **UX-2**: Centralized `ui.py` — BMAD + Claude Code hybrid terminal UI primitives
- **UX-3**: ASCII art banner — LINKRIGHT block letters shown on bare `linkright` + `profile create` + setup
- **UX-4**: BMAD diamond bullets (`◆ ◇ ● ○`) + Claude Code numbered options throughout all prompts
- **UX-5**: Mode-specific accents — Teal (resume), Sage (interview), Pink (social), Purple (jobs)
- **UX-6**: Spacious step logs — `✨ start` → `● done` pattern, blank lines between steps
- **UX-7**: Success card redesign — aligned fields, gold labels, teal values, next-steps section
- **UX-8**: Removed all ★ stars; gold `✨` sparkle for step starts
- **UX-9**: questionary Style unified — LinkRight brand colors in all select/confirm/text prompts

## [0.5.7] - 2026-05-10

**Profile create: per-field contact UI, deep enrichment integration, stronger nugget prompts.**

Contact verification now uses a numbered review panel with per-field select-to-edit navigation
(mirrors Claude Code AskUserQuestion pattern — pick any field, edit it, back to review).
Deep enrichment (3 follow-up Q&A per achievement) is now optionally offered at the end of
`profile create` — no longer requires a separate `linkright profile enrich` command.
Resume parse prompt now enforces the SEPARATOR RULE (pipes only in headers, no em-dashes).
Nugget extraction prompt upgraded with SINGLE-SIGNAL RULE + 150–350 char target + stronger
anti-fabrication company grounding — expected nugget count increases from ~10 to 25–45.

### Added

- **UX-1** — Deep enrichment offered at end of `profile create` (after truth engine).
  Pick one achievement → answer 3 LLM-generated follow-up questions → new nuggets persisted.
  Skippable (Enter on "No") and runs non-blocking (Ctrl+C cancels without losing profile).
  Full enrichment still available standalone via `linkright profile enrich`. (#ux-1)

### Fixed / Improved

- **PC-5b** — Contact verification upgraded from "re-enter all" to per-field selection.
  Numbered review panel lists all 5 fields with current values. User selects which specific
  field to edit → single text prompt → back to review panel. LinkRight brand colours applied
  (primary teal `#0FBEAF`, gold field labels `#E5B80B`). (#pc-5b)
- **PROMPT-1** — `RESUME_PARSE_FALLBACK` now includes SEPARATOR RULE (Critical): all ### and
  education headers use pipe `|` separators; em-dashes and other separators are re-formatted.
  Matches the website `parse-resume` route which added this rule to prevent parsing failures
  on resumes that use em-dashes in company/role headers. (#prompt-1)
- **PROMPT-2** — `NUGGET_EXTRACT_MD` upgraded with three quality gates from the website's
  `career-narration` approach: (a) SINGLE-SIGNAL RULE — each nugget describes exactly one
  achievement or capability; (b) 150–350 char target — optimal embedding model window;
  (c) company grounding rule — company field must appear verbatim in input text, no
  placeholder names. Expected nugget count increases from ~10 to 25–45 for a dense resume.
  (#prompt-2)

## [0.5.6] - 2026-05-10

**`linkright profile create` UX polish — 7 bugs fixed.** Embedder choice from
`linkright setup` is now honoured at runtime. HuggingFace unauthenticated-request
warning no longer interleaves with interactive prompts. Model download is
eagerly completed before any questionary appears. Contact details now show a
review/re-enter confirmation step. Success message uses the correct `linkright
tailor` alias. Contact header no longer shows internal jargon. Nugget extraction
includes an anti-fabrication prompt guard and a runtime company-name validation.

### Fixed

- **PC-1** — `embedder_tier` from `~/.linkright/config.yaml` is now honoured by
  `_detect_tier()` in `embedder.py`. Previously the setup wizard saved the choice
  correctly but the embedder ignored config and always auto-detected. (#pc-1)
- **PC-2** — HuggingFace unauthenticated-request warning suppressed at embedder
  module load (`HF_HUB_VERBOSITY=error` + `warnings.filterwarnings`), preventing
  interleaving with interactive output during `profile create`. (#pc-2)
- **PC-4** — Embedding model is now eagerly loaded/downloaded in the
  `"Indexing achievements semantically..."` step (before contact verification
  and highlight review begin), eliminating the tqdm/questionary race condition
  on cache-hit runs where step_03 skips the embed call. (#pc-4)
- **PC-5** — Contact verification adds a confirmation step after all five fields
  are collected ("Looks good? / re-enter all fields"), letting users catch
  accidental Enter presses without per-field back-navigation. (#pc-5)
- **PC-6** — Success message at end of `profile create` now shows
  `linkright tailor` (was incorrectly `linkright resume tailor`). (#pc-6)
- **PC-7** — Contact verification header changed from
  `"📇 Contact Verification — Truth Engine Layer 1"` (internal jargon) to
  `"📇 Contact details — confirm before we store them"`. (#pc-7)
- **PC-9** — Nugget extraction prompt now includes explicit anti-fabrication
  instruction and removes the "SampleCo" few-shot example that the model was
  copying. Runtime validation after step_02 warns (`⚠ Possible fabrication
  detected`) when a nugget's company name is absent from the raw resume text. (#pc-9)

## [0.5.3] - 2026-05-09

**Key management UX + token counter.** `linkright keys add` now auto-detects
provider keys already in your shell env and offers to import them. Supports
`--bulk` (paste all keys at once), `--key` (non-interactive for scripts). New
`linkright keys import` scans your entire env for all known providers at once.
Token counts (input/output/total) now printed to stderr on every LLM call.

### Added

- **`linkright keys add --bulk`** — paste multiple keys (newline or
  comma-separated) in one shot; auto-assigns rotation slots. (#99)
- **`linkright keys add --key "<val>"`** — non-interactive / CI-friendly
  single-key injection. (#99)
- **`linkright keys add <provider>`** — now auto-detects matching keys in
  shell env (e.g. `CEREBRAS_API_KEYS=k1,k2,k3,k4`) and offers to import
  all at once before falling back to manual entry. (#99)
- **`linkright keys import`** — scan ALL providers at once; shows table of
  what was found, confirms before writing. `--dry-run` to preview only. (#99)
- **Token counter** — `tier_chat` prints `[tokens] intent  in=N | out=N |
  total=N  (provider)` to stderr on every call. Estimate before send, actuals
  after. Silently skips in agent mode (no dangling estimate). Token telemetry
  now fires on `LR_TIER_OVERRIDE` path too (was silent before). (#99)

### Fixed

- `_detect_env_keys` plural-var derivation now correctly handles `_TOKEN`
  suffix (Cloudflare) — was generating `CLOUDFLARE_API_TOKENYS`, now
  produces `CLOUDFLARE_API_TOKENS`. (#99)
- `_log_token_usage` guard changed to `all None` — previously silently
  dropped lines when only `total_tokens` was populated. (#99)

## [0.5.2] - 2026-05-09

**Bugfix** — `linkright profile create` no longer crashes with `NameError: name 'has_name' is not defined`. PR #90 (PII sweep) removed the name-check variable but left a stale f-string reference in `step_00_ingest_pdf`. Also fixes `unpdf` falling back to `pypdf` on every run by including the missing `unpdf_parity_test.mjs` in the wheel via `package-data`.

### Fixed

- `NameError: name 'has_name' is not defined` in `orchestrator.py:step_00_ingest_pdf` — removed stale f-string metric line. (#98)
- `unpdf_parity_test.mjs` not packaged in wheel → unpdf always fell back to pypdf — added `[tool.setuptools.package-data]` to `pyproject.toml`. (#98)

## [0.5.1] - 2026-05-09

**Bugfix** — `linkright profile create` no longer shows "already exists" when only empty scaffold directories exist from a prior failed run. The guard now checks `metadata.yaml` (same signal as `profile show`/`status`), so users can always `create` after a failed run without needing `--force`.

### Fixed

- `profile create` guard: `any(iterdir())` → `(profile_dir / "metadata.yaml").exists()` — eliminates contradictory "Profile already exists" vs "No profile found" messages on partial state. (#96)




## [0.5.0] - 2026-05-07

**No-flag default UX** — every flag-required command now prompts
interactively when its flag is omitted. Bare `linkright tailor`,
`linkright cl`, `linkright profile create`, `linkright jobs apply`,
`linkright interview prep` etc. all just work. Power users with flags
see no behavior change.

### Added

- **`src/linkright/prompts/`** — new shared module with 10 interactive
  helpers (`prompt_for_existing_path`, `prompt_for_jd_input`,
  `prompt_for_resume_source`, `prompt_for_id_from_list`, etc.). Path
  prompts handle macOS Finder drag-drop (escaped spaces), tilde
  expansion, surrounding quotes. Multi-line text via
  `prompt_for_paste_block`. Single source of truth for the
  recommended-marker and Ctrl+C contracts. (#93)
- **CI / scripted-usage safety** — every prompt helper detects
  `not sys.stdin.isatty()` and raises `click.UsageError` (exit 2)
  with the equivalent flag hint. Scripts that previously got "Missing
  option" now get a more useful error; behavior unchanged in spirit.
- **`linkright resume verify`** — RUN_ID positional now optional;
  bare command shows a picker over the 20 most-recent runs.
- **`linkright jobs show / apply / status`** — bare commands show a
  picker over today's top-20 jobs (uses the SAME endpoint as
  `_resolve_id` — keeps rank-int → UUID resolution consistent).
- **`linkright interview prep / mock / debrief`** — bare commands show
  a picker over the 20 most-recent interviews from Mongo, with
  graceful fallback to free-text ID prompt when Mongo is unavailable.

### Changed

- **16 commands** converted to "no-flag default" UX (Pillar 1: tailor,
  score, verify, cover-letter, profile create, profile rebuild;
  Pillar 2: jobs show, apply, status, import, evaluate, find-slug;
  Pillar 3: interview schedule, prep, mock, debrief).
- **Multi-line text input** (interview debrief notes) prompts for a
  file path first; press Enter at the path prompt to switch to
  multi-line paste mode (Esc + Enter to submit).
- **`linkright tldr`** cheat-sheet rewritten — every example shows
  the bare command first; flags demoted to "(optional)" footers.
  Headline at top: "Every command works WITHOUT flags."
- **Setup wizard `_pick`** moved from `setup_wizard.py` to
  `linkright.prompts.prompt_for_choice` (canonical implementation).
  setup_wizard re-exports under the legacy name; existing call sites
  unchanged.

### Excluded from this refactor

- `resume hypothesis-test`, `resume batch`, and all `content/*`
  commands keep flag-required behavior. These are scripting /
  experiment tools where interactive prompting is a UX downgrade.

## [0.4.2] - 2026-05-06

`linkright profile show` polish — three UX fixes from manual walkthrough.
First end-to-end PyPI publish via the auto-publish workflow shipped in 0.4.1
(0.4.1 itself was bumped in pyproject but never published to PyPI).

### Changed

- **`linkright profile show`** now groups your profile into resume-conventional
  sections (Professional Experience → Education → Skills → Projects → Awards)
  matching FlowCV's content taxonomy, instead of alphabetical company order
  that interleaved education between work entries. (#87)
- **Timeline visible per role** — each work role and education entry now
  shows its date range as a dim chip after the label, e.g.
  `Senior Associate Product Manager  (Jul 2024 – Present)`. Dates loaded
  lazily from `01_resume_parsed.json`; gracefully degrades to no-dates
  if the artifact is missing. (#87)
- **Current employer floats to top** — Professional Experience now puts
  any role with `end_date == "Present"` at the top of the section
  (universal resume convention "current job first"), regardless of
  start-date order. (#87)
- **`--full` flag** added to `linkright profile show` — disables the
  120-char bullet truncation when you need to read the full sentence.
  A tip-line surfaces this option whenever truncated bullets exist. (#87)
- **Empty-section hint** — sections that aren't yet populated (Languages,
  Certificates, Voluntary Work, etc.) appear as a single dim line at
  the bottom of the tree with a `linkright profile rebuild` hint, so
  users know what's missing without inline clutter. (#87)

### Fixed

- Multiple degrees from the same institution (e.g. IIT 5-year integrated
  programs) no longer silently overwrite each other in the date lookup;
  years now accumulate and render as `(2021 / 2019)`. (#87)
- Date sort no longer uses ASCII string comparison ("Nov 2024" >
  "Jan 2025" by ASCII), which produced wrong reverse-chronological
  order. New `_date_sort_key()` parses freeform date strings into
  `(year, month)` tuples for true chronological sort. (#87)

## [0.4.1] - 2026-05-06

CLI polish pass — 5 PRs of UX improvements with no behavioral regressions.
Plus the foundation for `pip install --upgrade linkright` to actually work
for the first time (PyPI auto-publish CI on tag push).

### Changed

- **`linkright` (no-args)** now shows the cheat-sheet content directly
  instead of the alphabetical command list. Industry convention (git,
  kubectl, docker, npm) — no-args shows curated content; `linkright
  --help` continues to show the alphabetical command list as escape
  valve for power users. (#79)
- **`linkright tailor`** ends with a structured success card showing
  PDF path + score + duration + 3-step next-action nudge, instead of
  `✓ Done — see <path>`. Cross-platform `open` suggestion (uses
  `xdg-open` on Linux, `start` on Windows). Path is shell-quoted so
  copy-paste works for `--run-id` values containing spaces. (#80)
- **`linkright profile show`** adds a P0/P1/P2/P3 priority legend at
  the top of the tree. Long bullet text truncates at word-boundary
  with ellipsis (no more mid-character cuts). Literal "none"
  company/role placeholders normalized to "Other / Independent" /
  "(role unspecified)". Empty companies hidden. (#81)
- **`linkright profile status`** drops the SHA256 hash from default
  output (was internal cache-invalidation detail). When portfolio
  field is blank, status output now shows `(set with: linkright
  contact)` inline. (#81)
- **`linkright doctor`** — pluralization fix (`1 issue above` instead
  of `1 issue(s) above`). Embedder failure line states "using Oracle
  fallback (slower, network-dependent). pip install fastembed for
  offline + 5x speed." when fastembed is missing AND
  `ORACLE_BACKEND_URL` is set — eliminates the
  anxiety-without-agency pattern on the failure. (#82)
- **Help-text cleanup** across `critique`, `fill`, `practice`,
  `improve`, `strategy-review`, `edit-contact`: drops "Per Satvik
  <date>" attributions, "Truth Engine Layer N" framing, internal
  artifact paths (e.g. `<run>/artifacts/15b_interview_prep.json`),
  and "magnitude tier 0.5" jargon. Reads as user-facing product copy
  now. STAR auto-expands inline as `STAR (Situation / Task / Action
  / Result)` so new users aren't lost on the acronym. (#83)
- **`linkright tailor --help`** docstring rewritten as user copy
  ("typically 2-4 minutes" + quickstart) instead of the "16-step
  pipeline" implementation-detail framing. (#79)

### Added

- **`linkright doctor --auto-fix`** flag — opt-in, confirm-each-step.
  Detects fixable failures (e.g., missing fastembed), prompts the user
  per-failure, runs `pip install <pkg>` via subprocess on `y`. Caveat
  documented in `--help`: runs in your CURRENT Python env; conda/pipx
  users should install manually. (#82)
- **PyPI auto-publish on tag push** — `.github/workflows/cli-publish.yml`
  watches for tags matching `v*`. On push, validates the tag version
  matches `pyproject.toml`, builds wheel + sdist, uploads to PyPI via
  the `PYPI_API_TOKEN` secret. After this 0.4.1 release lands on PyPI,
  every user can run `pip install --upgrade linkright`. Foundational
  for the v1 ship.

### Notes

> **Action required for repository owner (one-time, ~3 min):**
> 1. Create a PyPI API token at <https://pypi.org/manage/account/token/>
>    (scope: project = "linkright").
> 2. Add it to GitHub Actions secrets as `PYPI_API_TOKEN` at
>    <https://github.com/satvik-jain-iitd/linkright_production/settings/secrets/actions>.
> 3. After this PR merges, run `git tag v0.4.1 && git push --tags`
>    locally — the CI workflow auto-publishes 0.4.1 to PyPI.

## [0.4.0] - 2026-05-03

Pillar 2 + Pillar 3 push toward v1 ship. New `linkright watch` (Chrome-attached
passive job-page capture across 7 portals), Pillar 2 dual-read jobs feed,
optional resume brand-color design, and Story Bank for STAR-format career
narratives.

> **Note on prior versions**: 0.2.x (Pillar 2 v1 — auth + jobs CLI thin client)
> and 0.3.0 (cover letter sub-tool) were released without CHANGELOG entries.
> See PR history (#48, #49) for those changes.

> **⚠️ BREAKING for users upgrading from 0.3.0**: Default LLM mode changed
> from `agent` (subprocess to claude/opencode/gemini-cli) to `direct` (HTTP
> calls to Groq/Cerebras with BYOK keys). Run `linkright setup` after
> upgrading — the wizard will detect your old config and prompt to migrate.
> Direct mode is free on Groq's `llama-3.1-8b-instant` free tier
> (14,400 req/day). If the pipeline ever escalates to `llama-3.3-70b`, the
> daily cap drops to 1,000 req — but that's atypical for resume tailoring.

> **NOTICE — visual change for existing users**: default brand colors flipped
> from navy palette (`#1B2A4A` etc.) to pure `#000000`. If you previously ran
> `linkright resume tailor` and got navy section titles + bullet markers, the
> output is now genuinely B&W. Opt back into color via the new `linkright
> resume brand` subcommand.

### Added
- **`linkright watch`** — passive job-page capture via Chrome DevTools Protocol
  (Sprint D). Attaches to user's existing Chrome profile, listens for navigation
  to job pages, extracts JD + posts to `/api/captures` on the LinkRight backend.
  7 portals supported: LinkedIn, Naukri, Indeed, Wellfound, Greenhouse, Lever,
  Ashby. Subcommands: `watch` (foreground), `watch setup` (Chrome remote-debug
  setup), `watch install-service` / `watch uninstall-service` (background
  daemon), `watch status` (one-shot health
  check), `watch list` (recent captures from Oracle PG). Per-source path
  blocklist prevents accidental private-page captures.
- **Pillar 2 dual-read** — `linkright jobs find` now merges Supabase scored
  feed + Oracle PG captures. Captures surface in the same view alongside
  scored recommendations; user sees their just-captured Naukri/LinkedIn
  postings without waiting for the next ranking job.
- **Sprint B trigger on captures** — new captures trigger fire-and-forget
  slug auto-discovery on previously-unknown companies (FastAPI BackgroundTasks +
  asyncpg). Companies database grows organically as user browses; no manual
  curation required.
- **Optional brand-color design** — `linkright resume brand --run-id <id>
  --primary "#..." [--secondary] [--accent] [--cover-letter <path>]` re-renders
  a tailored resume + cover letter with company-branded metric bolds and
  section-divider gradient. Pure B&W default unchanged. Surgical CSS swap on
  the rendered HTML; auto-bolds metric tokens (`$X`, `X%`, `XK/M/B`, `Xx`,
  `X:Y`, time units, `+`) in cover letter prose.
- **Pillar 3 Story Bank** — new `career_stories` MongoDB collection +
  `linkright stories` CRUD CLI (list / add / edit / delete / search) with
  STAR-format fields, tags, JD-requirement linkages. `--from-nugget`
  pre-fills `result` from existing resume nuggets (Truth Engine compliant —
  no LLM fabrication, scaffold only). `linkright interview prep` reads
  the Story Bank, merging legacy `user_context` debriefs as ranked-lower
  fallback. Shipped in PR #62.
- **Sprint C Phase 1** — `/api/captures` POST endpoint backed by Oracle PG
  `job_discoveries` table; Tampermonkey userscript path for browser-extension
  capture (deprecated by `watch` but retained for reference).
- **Oracle Postgres bring-up** — `companies` schema, slug-discovery cache,
  enriched-jobs cache. 81-company seed (28 ATS-verified). Sprint B 3-tier slug
  auto-discovery code: Layer 1 (known-pattern) and Layer 2 (page-fetch) are
  fully wired in production; Layer 4 (self-heal validator) code is merged
  but its Oracle VPS cron / systemd schedule has not yet been deployed
  (see Known limitations).

### Changed
- `linkright resume tailor` default brand colors flipped from navy palette
  (`#1B2A4A`) to pure `#000000` — output is genuinely B&W unless user opts
  into branding via the new `brand` subcommand.
- 4-stop hard-edge section divider gradient → 3-stop smooth linear gradient.
- All 4 templates: section title color + bullet markers locked to black
  regardless of brand opt-in.
- Watchlist UX demoted from mandatory onboarding to optional power-feature
  (docs only — code unchanged).
- `linkright stories` retrieval merges `career_stories` + legacy
  `user_context.kind=story` rows; previous all-or-nothing precedence
  (which silently dropped debriefs after first story) replaced.

### Fixed
- `asyncio.run` guards in `_run_watch_default` + `status_cmd` — unguarded
  exceptions previously bubbled as raw Python tracebacks instead of one-line
  actionable error messages.
- Per-source `BLOCKED_PATH_PATTERNS_BY_SOURCE` dict (vs global blocklist) —
  ATS sources (greenhouse / lever / ashby) intentionally exempt from LinkedIn-
  private-page regex that would silently 403 captures whose tenant slug
  collides with private path names.
- `apply_brand_to_html` regex preserves `!important` and inline comments
  after hex values; previously silently no-op'd on those CSS qualifiers.
- `linkright stories edit` strips whitespace + validates non-empty title /
  action / result before save; previously could write corrupt documents
  via prompt-clear.
- `(user_id, title)` unique index on `career_stories` blocks duplicate-title
  ambiguity at insert time.

### Known limitations
- Manual QA pass before public release (see
  [`specs/manual-qa-plan-v1-2026-05-03.md`](../../specs/manual-qa-plan-v1-2026-05-03.md)).
- `linkright resume brand --auto` (admin DB lookup) deferred to a follow-up release.
- Tailor pipeline doesn't yet surface `career_stories` alongside nuggets
  in step_08 retrieval. Deferred to v0.5 — needs proper RCA evaluation
  on bullet-quality per memory `feedback_one_resume_at_a_time` before
  prompt-context wiring lands.
- **Layer 4 self-heal validator runs manually only**: code is merged
  (`linkright admin slug-discovery validate-all [--max N]`), but the
  Oracle VPS cron / systemd timer for nightly auto-runs has not been
  deployed. Run manually as needed; without it, slug staleness
  accumulates over time.
- **`linkright jobs import <csv>` requires backend deployment**: CSV
  validation works (`--dry-run` previews rows), but live import POSTs
  to a Supabase `/api/discoveries` endpoint that is not yet deployed.
  Calling the live import currently returns 405 Method Not Allowed.
  Deferred to a follow-up release.
- **Wizard prompts to migrate on each setup run while agent mode is configured**:
  existing 0.3.0 users will see a migration prompt every time they run
  `linkright setup` until they accept the switch (or manually edit
  `~/.linkright/config.yaml`). Declining preserves `default_llm_mode: agent`
  and `agent_backend`; you can keep declining indefinitely. `linkright setup
  --check` also warns when agent mode is detected so you don't forget.

## [0.1.0] - 2026-04-24

First agent-native release. Four-pillar CLI + MCP server, local-first data layer.

### Added
- Agent-native CLI with 4 pillars: `resume`, `jobsearch`, `interview`, `content`
- 16-step resume tailoring pipeline (ported iter-02 → iter-08 quality work)
- Per-session MCP server (FastMCP) exposing **8 resume tools**
- LLM cascade: **Groq → Gemini Flash Lite → Cerebras → OpenRouter** + Oracle `gemma3:1b` for local fallback
- MongoDB local data layer — **12 collections**, v2-ready schema
- A–F 10-dim scorecard + telemetry loop (`CONTINUOUS_RCA_LOG.md`)
- `.claude/skills/` auto-discovery (8 skills: tailor-resume, score-resume, batch-apply, profile-refresh, evaluate-jd, interview-prep, draft-posts, content-plan)
- Idempotent `linkright init` — bootstraps `~/.linkright/` + Mongo collections + vector indexes
- Ops commands: `init`, `mcp serve`, `profile import`
- Legacy v0.0 commands preserved: `optimize`, `validate`, `assisted`

### Known issues
- Pillar 1 orchestrator E2E untested (requires API keys + sample resume/JD)
- Scorers are heuristic — LLM-judged scoring deferred to v0.2
- Pillars 2–4 are thin slices, not iter-08 quality yet
- Vector search falls back to cosine-scan on local MongoDB CE (Atlas-only feature)
