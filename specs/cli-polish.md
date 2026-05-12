# LinkRight CLI Polish — UX Walkthrough + Ship Plan

> Authorized spec. Last updated: 2026-05-08. Merges: cli-steve-jobs-walkthrough-2026-05-05.md + cli-polish-plan-2026-05-05.md.
> Tool tested: `linkright` v0.1.2. Persona: newly-onboarded PM (mid-technical, comfortable with terminal, not a developer).
> Lens: Steve-Jobs-style first-principles critique + behavioral psychology (Kahneman, Hick's Law, peak-end rule, Fogg Behavior Model).

---

## Locked Decisions (2026-05-05)

| # | Decision | Answer | Implication |
|---|---|---|---|
| 1 | Sequencing | Theme-batched (6 PRs) | Each PR ~80–150 LoC, one surface; reviewer attacks one area at a time |
| 2 | `linkright` no-args | Replace with tldr content | Alphabetical list moves to `linkright --help` (escape valve) |
| 3 | Inline review gates in tailor | Status quo + better end-of-flow nudge | CLI stays power-tools surface; nudge handles 80% of discoverability |
| 4 | Alias deprecation | Hide from `--help`, keep working + listed in tldr | No break for power users; clean default surface |
| 5 | `--auto-fix` flag | Confirm-each opt-in | Convenience without auto-mutation; aligns with Unix tradition |
| 6 | State files (glossary cookie + bad-critique log) | Neither in v1 | Always inline-expand jargon; defer bad-critique to v1.1 |

---

## 19-Item UX Backlog (Walkhrough Findings)

### TL;DR — Top 10 Findings

| # | P | Area | Steve's one-line | Impact |
|---|---|---|---|---|
| 1 | P0 | Entry-point density | "Show 19 commands first, the curated 4 last. Reverse it." | New user lands on a wall; tldr is one click away when it should be the default. |
| 2 | P0 | End-of-flow whisper | "I made the user wait 4 minutes and then I just said 'Done.' That's the most important moment in the flow." | Success exit is `✓ Done — see <path>` — no score, no next-step nudge. Peak-end rule violated. |
| 3 | P0 | Smoke-check failures without fix paths | "I'm telling the user one of their components is broken and giving them no way to fix it. That's hostile." | `Embedder ✗ ModuleNotFoundError` shown with no `pip install` suggestion. Anxiety without agency. |
| 4 | P0 | Internal step names in stdout | "`step_07_phase_1_2` in the user's terminal? That's the developer's variable name. Translate." | Stdout during tailor reads like alpha-stage debug output. Erodes trust during highest-attention moment. |
| 5 | P0 | `--llm-mode` agent default needs external CLI | "Default mode requires another tool I haven't installed and the help doesn't tell me." | New user runs `tailor`, hits "agent CLI not found" without context. |
| 6 | P0 | fastembed missing → silent Oracle fallback | "Doctor says fastembed missing. Three sources, three states." | State inconsistency between config / runtime / status output. |
| 7 | P1 | Internal jargon throughout help | "'Magnitude tier 0.5,' 'Truth Engine Layer 3,' SHA256 hashes. Whose mental model is this for?" | Help text reads like internal Notion docs. New user feels like an outsider. |
| 8 | P1 | Two-tier `--help` missing on multi-flag commands | "9 flags shown at equal weight. The user has to dismiss 7 to see the 2 that matter." | Cognitive overhead on every `tailor` invocation. |
| 9 | P1 | `profile show` polish | "Beautiful tree, sloppy details: literal 'none' labels, mid-character truncation, no priority legend." | Halo effect cut short. |
| 10 | P1 | Tailor's review gates not inline | "Website pauses 3 times during tailor. CLI doesn't. Pick one." | Cross-surface UX divergence. |

**Pattern across all 10:** none require new features or LLM rewrites. All ~16 of 19 backlog items are S-effort (≤30 LoC). Pure polish-pass surface.

---

### P0 Backlog

| # | Title | Effort | PR |
|---|---|---|---|
| 1 | No-args output: promote `tldr` content to default | S | PR1 |
| 2 | Long-running commands end with structured success summary (tailor, batch, iterate) | S | PR2 |
| 3 | Smoke-check failures suggest fix command inline | S | PR4 |
| 4 | Replace `step_07_phase_1_2`-style internal step names in stdout with user-friendly labels | S | PR5 |
| 5 | fastembed not installed — auto-fix offer in `setup` / `doctor` | S | PR4 |
| 6 | `--llm-mode` default "agent" requires external CLI; not obvious from `--help` | S | PR6 |

### P1 Backlog

| # | Title | Effort | PR |
|---|---|---|---|
| 7 | Two-tier `--help` on `tailor` and other multi-flag commands | S | PR1 |
| 8 | `profile show` polish: replace literal "none" + P0/P1/P2 legend + fix mid-character truncation | S | PR3 |
| 9 | `profile status` — drop SHA256 from default; suggest `linkright contact` when portfolio blank | S | PR3 |
| 10 | `tailor` 3 review checkpoints inline (match website's gate UX) | M | Decision 3: reframed to better end-of-flow nudge via PR2 |
| 11 | `critique` / `practice` / `fill` help: drop internal artifact paths + dated quotes | S | PR6 |
| 12 | `batch --help`: add expected dir layout + `--parallel` default + rate-limit warning | S | PR6 |
| 13 | STAR auto-expanded on first appearance | S | PR6 |
| 14 | Doctor pluralization: `1 issue above` not `1 issue(s) above` | S | PR4 |

### P2 Backlog (deferred post-v1)

| # | Title |
|---|---|
| 15 | Deprecate 1-letter aliases (`t`, `f`, `c`, `s`, `r`); show only in tldr |
| 16 | `critique` per-issue: 4th option `dismiss-as-bad-critique` + log to feedback file |
| 17 | `fill-metrics` industry-average ranges carry "verify with your team" disclaimer |
| 18 | Hide companies with 0 nuggets in `profile show` OR show `(no nuggets — try profile enrich)` |
| 19 | Doctor's `Embedder fastembed` mismatch: state the fallback in use + impact |

---

## Diagnostic Evidence (per finding)

### F-PRE-1: Doctor not the default entry point
Doctor is the most useful first command but the user has to guess it exists. **Fix (PR1):** Add to `linkright` no-args epilog: "New here? Try `linkright doctor` to verify your setup." Effort: S.

### F-PRE-2: `1 issue(s) above` — pluralization bug
Halo effect violation — bad copy on the trust-building command. **Fix (PR4):** Conditional `issue` / `issues`. Effort: S.

### F-PRE-3: fastembed missing but profile created OK — silent fallback
System knows it fell back to Oracle; user doesn't. Causes anxiety ("is my data half-broken?"). **Fix (PR4):** Doctor's fastembed ✗ line shows: "Currently using Oracle fallback (slower, requires network). Fix: `pip install fastembed`."

### A.1: `linkright` no-args = 19-command wall
Hick's Law + primacy effect. 19-option choice screen first; curated 4-step section buried. **Fix (PR1):** 4-step common workflow at TOP; `--help` keeps alphabetical list as escape valve.

### A.2: `linkright --help` identical to no-args
Two paths to same content. **Fix (PR1):** No-args = cheat sheet. `--help` = comprehensive reference. Differentiated.

### A.4: `setup --check` smoke failures without fix paths
`Embedder ✗ ModuleNotFoundError` — diagnostic only, no next step. Anxiety without agency (Yerkes-Dodson). **Fix (PR4):** Per-failure-mode message dict + inline fix command + `--auto-fix` flag.

### A.5: `profile show` polish
Beautiful tree with sloppy details: literal "none" labels, `at American Ex` mid-character truncation, no P0/P1/P2 legend. Halo effect working FOR you here — sub-tree issues erode it on repeated views. **Fix (PR3).**

### A.6: `profile status` SHA256 hash
SHA256 is debug noise to the user — neither reassuring nor actionable. **Fix (PR3):** Move to `--debug` flag; replace with `<basename of pdf> <last-modified date>`.

### B.1: `tailor --help` flag overload (9 flags equal weight)
Required + advanced flags visually identical. "16-step pipeline" leaks implementation detail. **Fix (PR1):** Two-tier help: Required / Common / Advanced (behind `--advanced-help`). Replace "16-step pipeline" with "Typically 2–4 minutes."

### B.2: Internal step names in stdout (`step_07_phase_1_2`)
Developer variable names in user's terminal erodes trust — feels like alpha demo. **Fix (PR5):**
```python
STEP_LABELS = {
    "step_07_phase_1_2":              "Analyzing the job description",
    "step_08_retrieve_per_company":   "Matching your career to JD requirements",
    "step_09_summary":                "Drafting professional summary",
    "step_10_verbose_bullets_batched":"Writing bullet drafts",
    "step_11_rank":                   "Ranking by JD-alignment",
    "step_12_condense":               "Condensing to final bullets",
    "step_13_width_skip":             "Optimizing for 1-page fit",
    "step_14_assemble_html":          "Rendering HTML",
    "step_15_pdf":                    "Exporting PDF",
}
```

### B.4: Tailor success exit = whisper ("✓ Done — see <path>")
Peak-end rule (Kahneman) — users remember the end. Currently the end is the lowest-emotion moment of a 4-minute wait. **Fix (PR2):** Structured success card:
```
✓ Resume tailored for <Company> — <Role>

  📄 PDF:       runs/.../output/resume.pdf
  📊 Score:     86/100 (B+ — 'Strong, with 3 polish opportunities')
  ⏱  Took:      2m 47s

  Next steps:
    linkright critique          → LLM review (3 issues to fix)
    linkright fill              → Resolve 2 bullets with weak metrics
    linkright practice          → Interview prep cards from your bullets
```

### C.1: `critique --help` authorial leak
Quotes Satvik 2026-05-02 + "Truth Engine Layer 3" framing. Help reads as internal Notion doc. **Fix (PR6):** Rewrite: WHAT (LLM critiques your resume + lets you accept/skip per issue) + WHEN (right after `linkright tailor`).

### D.1: `fill --help` jargon ("magnitude tier 0.5")
Undefined term forces context-switch. **Fix (PR6):** Replace with "bullets that count things ('Built 5 features') instead of measuring impact ('Built 5 features that drove 30% adoption')."

### E.1: `batch --help` too terse
3-flag listing with no directory layout example, no `--parallel` default, no rate-limit note. **Fix (PR6):** Add example layout + `--parallel` default (2) + "Groq free tier rate-limits at 3 concurrent calls."

### F.1: `practice --help` internal artifact path
References `<run>/artifacts/15b_interview_prep.json` — expertise leak. **Fix (PR6):** Rewrite: WHAT (interactive interview-prep cards from your tailored bullets) + WHEN (after `tailor`, before applying).

---

## 6 PRs (Sequenced by Impact)

### PR1 — Entry-point + tiered `--help`
**Branch:** `fix/cli-entry-point-and-tiered-help` | **Effort:** M (~120–150 LoC) | **Day:** 1

**What ships:** highest-leverage UX win — every new user benefits.

**Subtraction:**
- No-args: remove alphabetical-first command listing
- Tailor: remove 1-letter aliases from default `--help` chip; remove power-user flags from default view

**Addition:**
- No-args: tldr content as new output (use-case organized: Common workflow / First-time / Inspect / Drill / Health)
- `--help`: keeps alphabetical list as escape valve
- `tailor --help`: tiered `Required / Common / Advanced` sections; `--advanced-help` shows full surface
- Replace "16-step pipeline" with "Typically 2–4 minutes"

**Files:** `src/linkright/cli.py` (epilog + AliasedGroup), `src/linkright/resume/cli.py` (tailor decorators)

**Test plan:**
- [ ] `linkright` no-args matches `linkright tldr` content shape
- [ ] `linkright --help` shows alphabetical command list
- [ ] `linkright tailor --help` shows only Required + Common (5 flags); `--advanced-help` shows all 9
- [ ] 1-letter aliases still WORK at runtime — just not visible in default help
- [ ] `linkright tldr` still shows aliases

---

### PR2 — Peak-end success summaries
**Branch:** `feat/cli-success-cards` | **Effort:** M (~80–100 LoC) | **Day:** 1

**What ships:** end of every long-running command becomes the highest-emotion moment.

**Subtraction:** Remove bare `click.echo(f"✓ Done — see {run_dir}")` ending.

**Addition:** Structured success card at end of `tailor` (see B.4 block above). Same pattern for `batch` (per-JD card) and `iterate`. Reuses existing data from `<run>/artifacts/scorecard.json`.

**Files:** `src/linkright/resume/cli.py` — `tailor` final echo, `batch_cmd` end-of-loop, `iterate_cmd`

**Test plan:**
- [ ] `tailor` end output includes PDF path + score + duration + 3-step nudge
- [ ] Score matches `scorecard.json.score`
- [ ] If scorecard.json missing, graceful fallback (path + duration, no score line)
- [ ] `--yes` mode still emits success card

---

### PR3 — `profile show` / `profile status` polish
**Branch:** `fix/profile-display-polish` | **Effort:** S (~50–80 LoC) | **Day:** 0.5

**What ships:** halo-effect-preserving polish on the most-viewed inspection commands.

**Subtraction:**
- Remove: literal "none" labels in tree
- Remove: SHA256 line from default `profile status`
- Remove: empty-company nodes from default tree (or add explanatory placeholder)

**Addition:**
- "Other / Independent" for orphan-nugget company; "(role unspecified)" for missing role
- P0/P1/P2 legend at top of tree (`Priority: P0=core / P1=strong / P2=supporting`)
- Ellipsis-aware truncation (whole-word + `…`) instead of mid-character cut
- When portfolio blank: append `(set with: linkright contact)` to status output
- SHA256 moves to `profile status --debug`

**Files:** `src/linkright/profile/cli.py` — `show_cmd` (tree renderer) + `status_cmd` (KV renderer)

**Test plan:**
- [ ] No literal "none" in `profile show` output
- [ ] Long bullet text shows whole-word truncation with `…`
- [ ] SHA256 absent from default `profile status`; present with `--debug`
- [ ] Portfolio blank → shows `linkright contact` hint inline

---

### PR4 — `doctor` + `setup --check` actionable failures + `--auto-fix`
**Branch:** `feat/doctor-actionable-fixes` | **Effort:** M (~80–120 LoC) | **Day:** 1.5

**What ships:** every smoke-check failure includes (a) diagnostic, (b) suggested fix command, (c) optional `--auto-fix` confirm-each.

**Subtraction:**
- Remove: `1 issue(s)` pluralization
- Remove: bare `ModuleNotFoundError` without next-step from setup output

**Addition:**
- Per-failure-mode message dict in `setup_wizard.py`: `failure → (diagnostic, fix_command)`
- fastembed line in doctor: "Currently using Oracle fallback (slower, requires network). Fix: `pip install fastembed` (5x speed, offline)."
- `linkright doctor --auto-fix`: prompts per fixable failure; runs `pip install` on `y`; skips on `N`
- `--auto-fix` caveat in help: "Runs `pip install` in current Python env. If using conda or pipx, run the install command yourself."

**Files:** `src/linkright/cli.py` (doctor_cmd), `src/linkright/setup_wizard.py` (failure dict + --auto-fix plumbing)

**Test plan:**
- [ ] `doctor` with fastembed missing → shows fallback + fix command inline
- [ ] `doctor --auto-fix` with fastembed missing → asks confirm; `y` runs install; `n` exits cleanly
- [ ] `doctor` with 0 issues → `0 issues` (correct pluralization)
- [ ] `doctor` with 2 failures → `2 issues` (not `2 issue(s)`)

---

### PR5 — Internal step names → user-friendly labels
**Branch:** `fix/user-friendly-step-names` | **Effort:** S (~30–50 LoC) | **Day:** 1

**What ships:** ends `step_07_phase_1_2`-style developer-jargon leak into user-facing stdout. Cross-surface — aligns CLI + website labels.

**Subtraction:** Remove raw `step_NN_*` names from any user-visible output.

**Addition:** Shared `STEP_LABELS` dict (see B.2 block). Every `_progress()` / `log()` call wraps through `STEP_LABELS.get(internal, internal)`. Website's `PHASE_LABELS` in `StepBuild.tsx` updated to match.

**Files:**
- `src/linkright/resume/orchestrator.py` — add STEP_LABELS dict + wrap `log()` calls
- `worker/app/pipeline/orchestrator.py` — same dict
- `repo/website/src/app/resume/new/steps/StepBuild.tsx` — `PHASE_LABELS` updated

**Test plan:**
- [ ] `linkright tailor` stdout shows "Analyzing the job description" instead of `step_07_phase_1_2`
- [ ] All 10 internal names translated; new steps default to raw name (graceful fallback)
- [ ] Website `StepBuild.tsx` shows same 10 labels
- [ ] No regression on existing tests that assert on phase strings

---

### PR6 — Help-text copy cleanup (omnibus jargon pass)
**Branch:** `docs/cli-help-text-cleanup` | **Effort:** S (~50–100 LoC) | **Day:** 0.5

**What ships:** every command's `--help` reads as user-facing copy, not internal Notion docs.

**Subtraction:**
- All "Truth Engine Layer N" framing from user-facing help (keep in internal docs/comments)
- Satvik dated quotes from help docstrings
- Internal artifact paths from help text (e.g., `<run>/artifacts/15b_interview_prep.json`)
- Jargon ("magnitude tier", "raw count or no metric")

**Addition:**
- `critique --help` rewrite: WHAT (LLM critiques + accept/skip per issue) + WHEN (right after `tailor`)
- `fill-metrics --help` rewrite: plain language (see D.1 fix)
- `practice --help` rewrite: WHAT (interactive interview-prep cards from your tailored bullets) + WHEN
- `batch --help`: expected `--jds` directory layout + `--parallel` default (2) + rate-limit note
- STAR auto-expands: `STAR (Situation / Task / Action / Result)` on every appearance
- BRS expands: `BRS (Bullet Relevance Score)` on first appearance per command
- WCAG expands: `WCAG (Web Content Accessibility Guidelines)` in brand-related output

**Files:** `resume/cli.py`, `profile/cli.py`, `jobsearch/cli.py`, `watch/cli.py`, `stories/cli.py` — docstrings

**Test plan:**
- [ ] `grep -r "Truth Engine Layer" src/linkright/**/*.py` matches only internal comments, not click docstrings
- [ ] No `--help` output references `2026-05-02` or dated authorial context
- [ ] No `--help` output references internal artifact paths
- [ ] `linkright batch --help` shows expected `--jds` dir layout
- [ ] `linkright fill --help` reads as plain language
- [ ] First mention of STAR / BRS / WCAG in user-facing output expands inline

---

## Sequencing & Timeline

| # | PR | Days | Why this order |
|---|---|---|---|
| 1 | PR1 — entry-point + tiered --help | 1 | Highest impact; every new user benefits |
| 2 | PR2 — peak-end success cards | 1 | High satisfaction lift; solves Decision 3's nudge |
| 3 | PR3 — profile show/status polish | 0.5 | Pure polish, low risk, fast |
| 4 | PR4 — doctor + --auto-fix | 1.5 | Most code (new flag plumbing) |
| 5 | PR5 — step name translation (cross-surface) | 1 | Coordinate with website deploy |
| 6 | PR6 — help-text omnibus cleanup | 0.5 | Can ship in parallel with any of the above |

**Total: 5.5 days** focused execution. With reviewer cycles: **7–9 calendar days**.

---

## Deferred to v1.1 (out of scope)

| Walkthrough item | Why deferred |
|---|---|
| #10 (inline review gates in tailor) | Decision 3 → reframed to better end-of-flow nudge; gates deferred |
| #13 (STAR cookie state file) | Decision 6 → inline-expand always; no state file |
| #16 (bad-critique signal capture) | Decision 6 → defer until consent-flow UX exists |
| All P2 items (#15–#19) | Below P1 quality bar; revisit after v1 ships |

---

## Cross-Cutting Patterns

**X-1: Internal jargon leaks into user-facing surfaces (P1)**
Where: A.6 SHA256, B.2 step names, B.1 "16-step pipeline", C.1 Layer 3 framing, D.1 magnitude tier, F.1 artifact JSON path. Root cause: curse of knowledge (Pinker) — implementor assumes user shares their context.

**X-2: Smoke checks surface problems without fix paths (P0)**
Where: A.4 fastembed. Every smoke-check failure needs (a) diagnostic + (b) fix command + (c) optional `--auto-fix`.

**X-3: First-impression density — Hick's Law (P0)**
Where: A.1 (19-command wall), B.1 (9 equal-weight flags). Fix: promote tldr to no-args default; two-tier help on individual commands.

**X-4: Inconsistent command surface depth (P1)**
Where: 5 ways to invoke the same command (full name, alias, 1-letter, prefix-match, top-level). Pick 2 canonical paths; hide the rest from default `--help`.

**X-5: End-of-flow whisper — peak-end rule (P0)**
Where: B.4 tailor success exit. Every long-running command needs a structured success card at the end.

---

## End-of-Sprint Sanity Checklist

After all 6 PRs merged:
- [ ] `linkright` no-args on fresh shell → cheat sheet, not command wall
- [ ] `linkright tailor -r ... -j ...` on testing1 profile → success card at end with score + 3-step nudge
- [ ] `linkright doctor` → correct pluralization; failures suggest fix; `--auto-fix` works in confirm-each mode
- [ ] `linkright profile show` → no literal "none", proper truncation, P0/P1/P2 legend visible
- [ ] No `step_NN_*` strings appear in user-facing stdout during a tailor run
- [ ] `grep -r "Truth Engine Layer" src/linkright/` returns matches only in internal comments

---

## Live QA Session — 2026-05-10 (New User Flow)

> Full end-to-end manual test on fresh pipx install. Persona: new user, zero prior state.

### Install (`curl -fsSL https://install.linkright.in | bash`)

| # | Sev | Finding |
|---|---|---|
| I-1 | ⚠️ P1 | Python version mismatch: installer detected `3.13.1` (pyenv) in Step 2 but pipx used `3.14.3`. User confused about which Python runs LinkRight. |
| I-2 | ⚠️ P1 | `done! ✨ 🌟 ✨` — pipx raw emoji output bleeds into installer's clean output mid-flow. Looks unprofessional. |
| I-3 | ⚠️ P1 | GROQ key step uses raw shell command (`echo "..." >> ~/.env`). Non-tech users scared. Should say "run `linkright keys add groq <key>`" instead. |
| I-4 | 🟢 P2 | macOS users shown `source ~/.bashrc` — macOS default shell is zsh, not bash. Should show `source ~/.zshrc` first. |

### Setup wizard (`linkright setup`)

| # | Sev | Finding |
|---|---|---|
| S-1 | ⚠️ P1 | `"powers the 16-step resume pipeline"` — internal jargon. Replace with `"Typically 2–4 minutes"` (per polish spec B.1). |
| S-2 | 🟢 P2 | 4th choice label `"API keys"` confusing — Groq is also an API key. Rename to `"Additional LLM keys"`. |
| S-3 | ❌ P0 | Step numbering broken: header says `"4 quick choices"`, steps show `1/4 → 2/4 → 3/4 → 5/5`. Jump to `5/5` on API Keys step is wrong. |
| S-4 | ⚠️ P1 | After `"Verifying key with a live Groq call…"` — no ✓/✗ result shown. User doesn't know if key is valid. |
| S-5 | 🟢 P2 | Internal name inconsistency: "Picks so far" shows `sentence_transformers` (underscore); wizard shows `sentence-transformers` (hyphen). |
| S-6 | ❌ P0 | After Groq key entry + interactive keys flow, wizard loops back to asking for Groq key again. Infinite loop bug. |
| S-7 | ⚠️ P1 | Step 1 asks Groq key separately, then Step 5 asks for API keys again (all providers). Redundant + confusing. Consolidate into ONE keys step: ask all providers together (Groq first, rest optional). Remove the dedicated Groq-only step. |
| S-8 | ⚠️ P1 | Embedder question shows only the selected option — other choices not visible. User didn't see how many options were available. |
| S-9 | ❌ P0 | `pip install sentence-transformers` (~700MB) shows frozen `⬇ pip install sentence-transformers …` with zero progress. No ETA, no size, no spinner update. User thinks it's stuck. Show live pip output or progress bar with estimated time. |
| S-10 | 🟢 P2 | `Groq API key: ✓  Groq API key valid ✓` — double ✓ redundant. Should be: `Groq API key: ✓ valid`. |
| S-11 | ❌ P0 | `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN…` — HuggingFace warning bleeds raw into user output during smoke test. New user confused/scared. Suppress or translate: "Embedder loaded (anonymous mode — sufficient for LinkRight)". |
| S-12 | ⚠️ P1 | Success next-steps show `linkright resume tailor -r path/to/resume.pdf` — but canonical top-level alias is `linkright tailor`. Inconsistent. Use `linkright tailor` everywhere in user-facing output. |
| S-13 | ⚠️ P1 | Success next-steps show `-r path/to/resume.pdf` even after recommending `profile create` (which makes `-r` optional). Contradicts the profile caching benefit just described. |
| S-14 | ⚠️ P1 | User chose "Agent mode only" but no check that `claude` (or Cursor) is actually on PATH. If not installed, next `tailor` run will fail silently. Should warn: "Agent mode requires Claude Code or Cursor CLI — run `which claude` to verify." |

### Doctor (`linkright doctor`)

| # | Sev | Finding |
|---|---|---|
| D-1 | ❌ P0 | `✓ Embedder (fastembed)` shown even when user configured `sentence-transformers` in setup. Doctor hardcodes fastembed check instead of reading `config.yaml` to validate the *configured* embedder. |
| D-2 | ⚠️ P1 | `1 key(s) across 1 provider(s)` — `(s)` pluralization bug still present in keys line (polish spec F-PRE-2 only partially fixed — "1 issue above." is correct but keys line is not). |
| D-3 | 🟢 P2 | `run \`linkright profile create -r resume.pdf\`` — placeholder path `resume.pdf` is unhelpful. Should be `linkright profile create` (prompts for path) or a real example like `~/Documents/resume.pdf`. |

### Profile Create (`linkright profile create`)

| # | Sev | Finding |
|---|---|---|
| PC-1 | ❌ P0 | Setup wizard embedder choice not persisted to `config.yaml` — user selected `sentence-transformers` but profile create used `fastembed` (dim=384). `config.yaml` shows `embedder_tier: fastembed` unchanged after setup. |
| PC-2 | ❌ P0 | HuggingFace warning appears again during profile create (not just setup smoke-test): `Warning: You are sending unauthenticated requests to the HF Hub...` — S-11 fix was only in setup_wizard.py; profile pipeline also needs suppression. |
| PC-3 | ~~by design~~ | Token telemetry `[tokens]` lines visible during profile create — intentional, user wants to see input/output token counts. Do not suppress. |
| PC-4 | ⚠️ P1 | Download progress bar (`Fetching 5 files: 100%...`) runs in a parallel thread and interleaves output with questionary prompts mid-answer. User sees `Download complete: 67.2MB` mid-highlight-review. Serialize: complete download before starting questionary. |
| PC-5 | ⚠️ P1 | No back navigation in questionary flows — user accidentally pressed Enter on LinkedIn URL, skipped it, no way to go back. Need: either `(b) back` option per question, or a review+edit pass at the end. |
| PC-6 | ⚠️ P1 | `"Next: linkright resume tailor -j jd.md"` in profile create success message — still says `linkright resume tailor` not `linkright tailor`. PR #102 fixed setup_wizard.py but profile/cli.py missed. |
| PC-7 | ⚠️ P1 | `"📇 Contact Verification — Truth Engine Layer 1"` — internal jargon in user-facing header. Replace with `"📇 Contact Verification — confirm your details before we store them"`. |
| PC-8 | 🟢 P2 | `D?` prefix on LinkedIn URL question — display glitch in questionary rendering. Should just show `?`. |
| PC-9 | ❌ P0 | Highlight 4 appears fabricated: `"Shipped DesignerAI self-serve onboarding at SampleCo, eliminating 12 manual setup steps."` — "SampleCo" is not a real company in Satvik's resume. LLM hallucination in step_02_extract_nuggets. Fabrication guard missed this. |

### Feature Requests (profile flow)

| # | Priority | Request |
|---|---|---|
| FR-1 | P1 | LangFuse integration for CLI LLM calls — website tracks prompts/responses in LangFuse; CLI does not. Add tracing to `step_01`, `step_02`, `step_03` LLM calls in profile pipeline. |
| FR-2 | P1 | Rich back-navigation in questionary flows (contact verify + highlights) — Claude Code's AskUserQuestion-style UI as inspiration. User should be able to go back to previous question. |

### Keys (`linkright keys`)

| # | Sev | Finding |
|---|---|---|
| K-1 | ⚠️ P1 | On reinstall, `linkright keys import` only scans shell env vars — does not migrate from existing `~/.linkright/.env`. User must re-add all keys manually. No migration path shown. |
| K-2 | ❌ P0 | No duplicate key detection — same key added twice (once in setup, once via `keys add`) with no warning. System silently stores two slots with identical values. Should detect duplicate and warn: "This key is already saved as GROQ_API_KEY." |
| K-3 | ⚠️ P1 | `linkright keys import` doesn't tell user which file to manually edit if they want to add keys directly. Should say: "Or manually edit `~/.linkright/.env` — one key per line, format: `GROQ_API_KEY=gsk_...`" |
| K-4 | 🟢 P2 | `1 key(s) saved` and `2 key(s) across 1 provider(s)` — `(s)` pluralization bug present throughout keys command output. |
| K-5 | ❌ P0 | Naming convention inconsistent across providers: Groq uses `GROQ_API_KEY_1` (suffix from slot 1), but Cerebras/SambaNova use `CEREBRAS_API_KEY` (no suffix) for primary then `_1`, `_2`. All providers should use one convention: either always suffix (`_1`, `_2`…) or always no-suffix for primary. |
| K-6 | ❌ P0 | No duplicate key detection — same key added across multiple invocations fills separate slots silently. Should hash-compare and warn: "This key is already saved as GROQ_API_KEY." |
| K-7 | ❌ P0 | No live API validity check on key addition — any string accepted without a test call. Should ping provider API at `keys add` time and show ✓/✗ immediately. Catches typos, wrong-provider pastes, expired keys instantly. |
| K-8 | ~~deferred~~ | Terminal security not a concern per product decision. Covered by K-7 (live validity ping catches wrong pastes). |
| K-9 | ⚠️ P1 | `⭐` star shown on Groq + Cerebras but not SambaNova in `keys list` — no legend explaining what star means. User assumes SambaNova is inferior. Add legend or tooltip. |
| K-10 | ⚠️ P1 | `keys list` silently shows duplicate keys (GROQ_API_KEY + GROQ_API_KEY_1 identical; CEREBRAS_API_KEY_1 + CEREBRAS_API_KEY_4 identical) with no warning. Should flag: `⚠️ 2 duplicate keys detected — run \`linkright keys remove\` to deduplicate.` |
| K-11 | ⚠️ P1 | `linkright keys remove` with no args errors with "Missing argument 'PROVIDER'" but doesn't show correct usage inline. User must guess format or run `--help`. Should show: `Usage: linkright keys remove groq` with available providers listed. |
| K-12 | ❌ P0 | `linkright keys add` exits after completing one provider — user must re-run command for every provider. Should loop: after finishing a provider, ask "Add keys for another provider? (Y/n)" and show remaining unconfigured providers. Adding 6 providers = 6 separate command invocations right now. |

---

## Verification Per PR

Each PR ships with:
1. `adversarial-reviewer` dispatch as final merge gate (per CLAUDE.md PR merge gate rule)
2. py_compile / ts compile green on touched files
3. Vercel CI green for any PR touching website (PR5 only)
4. Test-plan checkboxes filled pre-merge
5. Commit author = `satvik-jain-iitd <satvik.jain@iitdalumni.com>` (Vercel auth requirement)
