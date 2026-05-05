# LinkRight CLI Steve-Jobs UX Walkthrough — 2026-05-05

**Tool tested:** `linkright` v0.1.2 at `/opt/anaconda3/bin/linkright`
**Test environment:** macOS 24.1.0, zsh, ~/.linkright/ pre-existing
**Method:** Live drive in TTY where commands are non-interactive; source-read narration for interactive (questionary) prompts. Hybrid because TTY-driving questionary via Bash heredoc is unreliable.
**Persona:** Newly-onboarded PM (Satvik's stated target user) — mid-technical, comfortable with terminal but not a developer.
**Lens:** Steve-Jobs-style first-principles critique + behavioral psychology (Kahneman System 1/2, Thaler defaults, Hick's Law, Fogg behavior model, peak-end rule).

---

## TL;DR — top 10 findings

| # | P | Area | Steve's one-line | Impact |
|---|---|---|---|---|
| 1 | **P0** | Entry-point density (X-3, A.1) | "Show 19 commands first, the curated 4 the user actually needs LAST. Reverse it." | New user lands on a wall; tldr is one click away when it should be the default. |
| 2 | **P0** | End-of-flow whisper (X-5, B.4) | "I made the user wait 4 minutes and then I just said 'Done.' That's the most important moment in the flow." | Tailor's success exit is `✓ Done — see <path>` — no score, no next-step nudge. Peak-end rule violated. |
| 3 | **P0** | Smoke-check failures without fix paths (X-2, A.4) | "I'm telling the user one of their components is broken and giving them no way to fix it. That's hostile." | `Embedder ✗ ModuleNotFoundError` shown to user with no `pip install` suggestion. Anxiety without agency. |
| 4 | **P0** | Internal step names in stdout (B.2) | "`step_07_phase_1_2` in the user's terminal? That's the developer's variable name. Translate." | Stdout during tailor reads like alpha-stage debug output. Erodes trust during the highest-attention moment. |
| 5 | **P0** | `--llm-mode` agent default needs external CLI (B.1) | "Default mode requires another tool I haven't installed and the help doesn't tell me." | New user runs `tailor`, hits "agent CLI not found" without context. |
| 6 | **P0** | `fastembed` missing → silent Oracle fallback (F-PRE-3, A.4) | "Doctor says fastembed missing. Smoke says ModuleNotFoundError. Status says 'Embedder fastembed.' Three sources, three states." | State inconsistency between config / runtime / status output. User can't tell what's actually running. |
| 7 | **P1** | Internal jargon throughout help (X-1) | "'Magnitude tier 0.5,' 'Truth Engine Layer 3,' SHA256 hashes, file paths to JSON artifacts. Whose mental model is this for?" | Help text reads like internal Notion docs. New user feels like an outsider. |
| 8 | **P1** | Two-tier --help missing on multi-flag commands (B.1) | "9 flags shown at equal weight. The user has to dismiss 7 to see the 2 that matter." | Cognitive overhead on every `tailor` invocation. Required + advanced flags conflated. |
| 9 | **P1** | `profile show` polish (A.5) | "Beautiful tree, sloppy details: literal 'none' labels, mid-character truncation, no priority legend." | Halo effect cut short — tree creates 'wow' moment, sub-tree polish issues erode it. |
| 10 | **P1** | Tailor's review gates not inline (B.3) | "Website pauses 3 times during tailor. CLI doesn't. Pick one." | Cross-surface UX divergence; existing CLI gates (`contact_verify_loop`, `run_strategy_review`, `run_critique`) shipped 2026-05-02 but only as separate commands. |

**Pattern across all 10:** none require new features or LLM rewrites. All ~16 of 19 backlog items are S-effort (≤30 LoC). This is a pure polish-pass surface — 1-2 days of focused work to lift from B+ to A-.

---

## Methodology recap

For each command:
1. Capture: command, duration, stdout/stderr summary, exit code
2. User state: System-1 reaction, System-2 demand, cognitive load 1-5, decision points
3. Steve's Verdict: 1-2 sentence ruthless critique
4. Behavioral lens: which principle is violated + why it matters
5. Concrete fix + effort (S/M/L) + impact

Interactive prompts described from source (`setup_wizard.py`, `profile/cli.py`) + matched against running snapshots of state.

---

## Pre-flight findings (from `linkright doctor`)

Already-visible UX issues even before walking the journeys:

### F-PRE-1: Doctor output is the only non-help discovery surface

**Steve's Verdict:** "Why am I being asked to GUESS that `doctor` exists? It's the most useful first command. Surface it in the help epilog or auto-run on first invocation."

**Behavioral lens:** Path-of-least-resistance violation (Fogg). New user types `linkright`, sees a wall of subcommands, has no signal that `doctor` is the right entry point. Most users won't try it.

**Fix:** Add to `linkright` no-args output: `New here? Try \`linkright doctor\` to verify your setup.` Effort: **S** (1-line copy change in `cli.py` epilog).

### F-PRE-2: `1 issue(s) above` — pluralization bug

**Steve's Verdict:** "We're shipping a product where the copy hasn't been proofread. This is the kind of detail that signals 'amateur' to a discerning user."

**Behavioral lens:** Halo effect (Thorndike) — small flaws cast doubt on the whole product. Doctor IS the trust-building command; bad copy here erodes the trust it's trying to build.

**Fix:** Conditional: `1 issue above` / `2 issues above`. Effort: **S** (1-line change in `doctor`'s output formatter).

### F-PRE-3: `fastembed` missing but profile created OK — silent fallback unmentioned

**Steve's Verdict:** "I just told the user one of their dependencies is missing. They have no idea if their existing profile data is degraded because of it. Tell them what's actually wrong."

**Behavioral lens:** Information asymmetry — the system knows it fell back to Oracle for embeddings; the user doesn't. Causes anxiety ("is my data half-broken?") without giving any way to resolve.

**Fix:** Doctor's `✗ Embedder (fastembed)` line should say: `✗ Embedder (fastembed) — currently using Oracle fallback (slower, requires network). Install fastembed for offline + 5x speed.` Effort: **S** (state-aware message).

---

## Part A: Journey-by-journey walkthrough

### Journey A — First-time setup [DEEP]

The user types `linkright` for the first time. What do they see, what do they type next, and where does the path lose them?

#### A.1 — `linkright` (no args)

**STDOUT (verbatim):** Usage line, branding ("LinkRight — local-first, agent-native career OS."), 🚀 nudge to `linkright tldr`, 19 commands listed alphabetically, "Common workflow" 4-step block, "Quick reference", "Pillars" section.

**User state:** System-1 sees a wall of 19 commands. System-2 must parse the alphabetical list to find an entry point. **Cognitive load: 4/5** (manageable but heavy). **Decision points: ~19** (one per command name) before the user reads the "Common workflow" section that actually answers their question.

**STEVE'S VERDICT:** "If the FIRST thing you show a new user is a wall of 19 commands and THEN at the bottom say 'oh by the way here are the 4 you actually need' — you've already lost them. The 4-step workflow should be at the TOP."

**BEHAVIORAL LENS:** **Hick's Law** (decision time grows with number of options) + **primacy effect** (first thing seen anchors expectations). User encounters 19-option choice screen first; the curated 4-option section is buried below the fold on shorter terminals. Their first impression is "this is complex," not "this is simple."

**FIX:** Reorder the no-args output: 4-step Common workflow at the TOP, then 🚀 tldr nudge, then commands list collapsed by default (or alphabetically below). Match `linkright tldr`'s structure for the no-args case directly. Effort: **S** (re-order strings in `cli.py` epilog + main `--help` callback).

#### A.2 — `linkright --help`

**STDOUT:** Identical to A.1. Two paths to same content.

**STEVE'S VERDICT:** "`--help` and no-args returning identical output is fine on its own — but means we have ZERO chance to differentiate 'I'm here to read docs' from 'I'm here to do something.'"

**BEHAVIORAL LENS:** **Functional fixedness** — both paths land in the same place, so neither path can be optimized for its specific intent. Power users want commands enumerated; new users want guidance. Conflated.

**FIX:** Keep `--help` as the comprehensive reference (current behavior). For no-args, show a SHORTER first-impression: branding + 4-step Common workflow + "Type `linkright --help` for full reference, `linkright tldr` for cheat sheet." Effort: **S** (split the click epilog from the no-args invocation).

#### A.3 — `linkright tldr`

**STDOUT:** Cheat sheet organized by use-case (Common workflow / First-time setup / Inspect / Drill / Shortcuts / Health / Full reference). 50+ lines.

**STEVE'S VERDICT:** "This is brilliant. This is what `linkright` should show on first run. Why is it hidden behind `linkright tldr`?"

**BEHAVIORAL LENS:** **Path-of-least-resistance** (Fogg Behavior Model: Behavior = Motivation × Ability × Trigger). The user's MOTIVATION is high (they want to use the product), but ABILITY is gated by typing `tldr` first. The TRIGGER ("🚀 Try first: linkright tldr") nudges correctly, but it's a redundant step.

**FIX:** Move the tldr content to the no-args case (per A.1 fix). Keep `linkright tldr` as a separate command for users who want to re-print after their first session. Effort: **S** (function call: no-args → tldr's renderer + the 4-step workflow at top).

#### A.4 — `linkright setup --check`

**STDOUT:**
```
Config:  /Users/satvikjain/.linkright/config.yaml
  LLM:       opencode
  Embedder:  fastembed
  PDF:       playwright
  Skill:     product_manager

Smoke checks:
  LLM:       ✓  `opencode` found
  Embedder:  ✗  failed: ModuleNotFoundError: No module named 'fastembed'
  PDF:       ✓  Chromium launches OK
```

**User state:** System-1 sees ✗ on Embedder. System-2 reads "ModuleNotFoundError" and asks: "What do I do? Is my profile broken? Will the next command work?" **Cognitive load: 4/5** (anxiety-inducing without action guidance).

**STEVE'S VERDICT:** "I'm telling the user one of their components is broken AND I'm telling them their config thinks it's not broken. They have NO idea what to do. Either fix it for them or tell them how to fix it."

**BEHAVIORAL LENS:** **Information without agency** — surfacing a problem without a fix path is hostile UX. Users feel powerless. **Yerkes-Dodson curve**: anxiety raises arousal past the optimal-performance peak; user's next action is more likely to be 'close terminal' than 'continue.'

**FIX:** Smoke check failures should suggest the fix inline:
```
Embedder:  ✗  failed: ModuleNotFoundError — fastembed not installed.
              Fix: `pip install fastembed` (or set ORACLE_BACKEND_URL for Oracle fallback).
```
Even better: an `--auto-fix` flag that runs `pip install fastembed` on the user's behalf with confirmation. Effort: **S** (per-failure-mode message dictionary in `setup_wizard.py`).

#### A.5 — `linkright profile show`

**STDOUT:** Rich-style boxed metadata + tree-structured career outline with P0/P1/P2 labels per nugget. ~50 lines for 21 nuggets. Beautiful Unicode tree with ├──, └──, │ connectors.

**User state:** System-1 reaction: "Wow, this looks like a real product." (peak-end rule kicks in — this is the kind of "delight moment" Steve cared about). System-2 starts asking what P0/P1/P2 mean. **Cognitive load: 2/5.**

**STEVE'S VERDICT:** "This is genuinely beautiful. But: the 'none' placeholders are sloppy, the truncated bullet text looks like it was clipped by accident not by design, and 'P0/P1/P2' assumes the user reads the same priority taxonomy I do. Polish the details."

**BEHAVIORAL LENS:** **Halo effect** is working FOR you here — the box + tree gives a "this is well-engineered" first impression. But sub-tree polish issues will become more salient on each subsequent re-view (familiarity reveals flaws). Catch them now while the halo is fresh.

**FIX:**
- Replace literal `"none"` company-name with `"Other / Independent"` and `"none"` role-name with `"(role unspecified)"`. Effort: **S**.
- Replace mid-character truncation (`"American Ex"`) with proper ellipsis (`"American Express"` truncated to `"American Express…"` or simply allow soft-wrap). Effort: **S**.
- Add a one-line legend at the top of the tree: `Priority: P0=core / P1=strong / P2=supporting`. Effort: **S**.
- Hide companies with 0 nuggets (e.g. "Sukha Education" with empty children) OR show them with `(no nuggets yet — try \`linkright profile enrich\`)`. Effort: **S**.

#### A.6 — `linkright profile status`

**STDOUT:** Flat KV format: profile dir, created timestamp, embedder + model, source PDF SHA256, nugget counts, contact dict.

**User state:** System-1 reaction: "OK, sensible." System-2 stops at `Source PDF:   sha256=5c5d30c25a6a5757…` and asks "what is this and why do I see it?" **Cognitive load: 3/5.**

**STEVE'S VERDICT:** "Why am I seeing a SHA256 hash on a status command? That's debug noise. Either it has a purpose visible to the user — show the purpose — or it's internal and shouldn't be here."

**BEHAVIORAL LENS:** **Information overload** + **expertise-leak** (showing internals leaks the implementor's mental model into the user's view). Status is the user's "is everything OK" command — every line should be either reassuring or actionable. SHA256 is neither.

**FIX:** Drop SHA256 from default `status` output. Move to `profile status --debug` if needed for cache diagnostics. Replace with: `Source: <basename of pdf>  <last-modified date>`. Effort: **S**. Bonus: when `portfolio` is blank, append `  (set with: linkright contact)`. Effort: **S**.

#### A-summary

Journey A reveals a coherent story: **the entry-point output is dense, but every sub-command IS individually well-designed**. The friction is in DISCOVERY, not in any single command. New user lands on `linkright`, sees a wall, has to follow a 🚀 trail to `tldr` to get oriented. The CLI is a B+ that could be an A with surface-level reordering work — almost no logic changes, just copy + ordering fixes.

Three patterns emerge across A:
- **Wall-of-options before guidance** (A.1, A.2 — Hick's Law)
- **Internal state leaked into user-facing output** (A.4 fastembed claim ≠ reality, A.6 SHA256, A.5 "none" labels)
- **Smoke checks without fix paths** (A.4 — anxiety without agency)

These will recur in B-F.

### Journey B — Single resume tailor [DEEP]

The user types `linkright tailor -r resume.pdf -j jd.md` — the daily-driver command. What they see during the 16-step pipeline shapes whether they trust the output.

#### B.1 — `linkright tailor --help`

**STDOUT:** 7 flags exposed in default help: `--resume`, `--jd`, `--mode`, `--llm-mode`, `--yes`, `--run-id`, `--no-cache`, `--deterministic`, `--seed`. One-line description: "Tailor resume for a JD via the 16-step pipeline."

**User state:** System-1 reaction: "16 steps?? How long does that take?" System-2: scanning 9 flags, half of which (deterministic, seed, no-cache, run-id) are clearly power-user flags. **Cognitive load: 4/5.**

**STEVE'S VERDICT:** "Why am I showing the user `--seed` for deterministic randomization at the SAME visual weight as `--resume`? The two essentials and the seven advanced flags should not look identical. And '16-step pipeline' is internal language — the user doesn't care that it's 16 steps; they care that it'll take 2-5 minutes."

**BEHAVIORAL LENS:** **Flag overload** + **expertise leak**. Showing power flags at parity with required ones forces System-2 to scan and dismiss them, raising perceived complexity. 16-step framing leaks the implementation detail when what the user wants is duration.

**FIX:** Two-tier help:
```
Required:
  -r / --resume <PATH>      Your resume PDF
  -j / --jd <PATH>          Job description (markdown)

Common options:
  --mode <skill>            product_manager | swe | ds | designer | generic
  --yes                     Don't prompt for the 3 review checkpoints

Advanced (rarely needed):
  linkright tailor --advanced-help    Show --llm-mode / --no-cache / --deterministic / --seed
```
And replace "16-step pipeline" with "Typically 2-4 minutes." Effort: **S** (Click decorator + epilog tweak).

#### B.2 — `linkright tailor` (running, first 30 seconds)

User types `linkright tailor -r resume.pdf -j jd.md`, hits Enter. What appears?

From the orchestrator code: progress emits per-phase via Supabase `update_job` (website mode) OR via `_progress` stdout writes (CLI mode). CLI mode prints lines like:

```
Run ID: 2026-05-05_2206
Output: /Users/.../runs/2026-05-05_2206
LLM mode: agent  •  Skill mode: product_manager
✓ Profile cache hit — reusing 4 artifacts from ~/.linkright/profile/ (saves ~30-60s of step_00-03 work).
[step_07_phase_1_2] starting...
[step_07_phase_1_2] completed in 12.3s
[step_08_retrieve_per_company] starting...
...
```

**STEVE'S VERDICT:** "Step names like `step_07_phase_1_2` in the user's terminal? That's the variable name from the developer's source code. The user has no idea what 'phase 1+2' means. Translate to human language."

**BEHAVIORAL LENS:** **Implementation-detail leak** (same root pattern as B.1's "16-step pipeline"). Reading internal variable names erodes trust — feels like an alpha demo, not a polished product.

**FIX:** Map step names to user-friendly labels in the orchestrator's `log()`/`_progress()` calls:
```
step_07_phase_1_2  →  "Analyzing the job description"
step_08_retrieve_per_company  →  "Matching your career to JD requirements"
step_09_summary  →  "Drafting professional summary"
step_10_verbose_bullets_batched  →  "Writing bullet drafts"
step_11_rank  →  "Ranking by JD-alignment"
step_12_condense  →  "Condensing to final bullets"
step_13_width_skip  →  "Optimizing for 1-page fit"
step_14_assemble_html  →  "Rendering HTML"
step_15_pdf  →  "Exporting PDF"
```
Effort: **S** — single dict in `orchestrator.py` mapping internal name → display label.

#### B.3 — `linkright tailor` (interactive review checkpoints)

Per the just-shipped pipeline-gates feature, the CLI has 3 EDITABLE Truth Engine gates:
- **Layer 1:** `contact_verify_loop` (in `profile/pipeline.py:304`) — surfaces phone/email/LinkedIn/portfolio for confirmation BEFORE pipeline starts.
- **Layer 2:** `run_strategy_review` (`harness/resume/strategy_review.py`) — shows outline + width + bullet distribution; user can edit.
- **Layer 3:** `run_critique` (`harness/resume/critique.py`) — final critique + fix options.

These run as SEPARATE commands today (`linkright contact`, `linkright plan`, `linkright critique`), not inline during `tailor`. Per the gates feature on the website, they CAN be inlined in the worker — but CLI keeps them post-hoc by design.

**STEVE'S VERDICT:** "If the website shows 3 review gates inline during tailor and the CLI doesn't, you have two products with two mental models. Pick one. Either every tailor pauses 3 times in CLI too, or remove the gates from the website."

**BEHAVIORAL LENS:** **Cross-surface UX divergence** — power users will use both surfaces. Each context-switch costs them. Consistency principle (Cialdini): users trust products that behave the same across surfaces.

**FIX:** Inline the 3 Truth Engine gates into `linkright tailor` by default, with `--yes` flag to skip. Reuses existing `contact_verify_loop` / `run_strategy_review` / `run_critique` functions that are ALREADY interactive (questionary-driven). Just call them from inside `orchestrator.main()` at the right phase boundaries. Effort: **M** (~50 LoC + careful flag handling).

#### B.4 — `linkright tailor` (success exit)

After ~2-4 minutes, pipeline completes. From the cli.py code: `click.echo(f"✓ Done — see {run_dir}")`.

**STDOUT (final line):** `✓ Done — see /Users/.../runs/2026-05-05_2206`

**STEVE'S VERDICT:** "I just made the user wait 4 minutes and at the end I just say 'Done.' That's the most important moment in the whole flow — the **peak-end** moment — and we're whispering 'OK, you're done, bye.' Tell them what they got, score it, suggest the obvious next move."

**BEHAVIORAL LENS:** **Peak-end rule** (Kahneman) — users remember the peak emotional moment AND the end. The end of `tailor` is the most rewarded moment of the workflow. Currently it's an anticlimax.

**FIX:** Replace with a structured success box:
```
✓ Resume tailored for <Company> — <Role>

  📄 PDF:       runs/2026-05-05_2206/output/resume.pdf
  📊 Score:     86/100 (B+ — 'Strong, with 3 polish opportunities')
  ⏱  Took:      2m 47s

  Next steps:
    linkright critique          → LLM review (3 issues to fix)
    linkright fill              → Resolve 2 bullets with weak metrics
    linkright practice          → Interview prep cards from your bullets

  Open the PDF: open <path>
```
Effort: **S** (replace the one click.echo with a structured renderer using existing scorecard data already saved at `<run>/artifacts/scorecard.json`).

---

### Journey C — Refine after critique [MEDIUM]

`linkright critique` is the bridge between "first draft generated" and "shippable." It's Truth Engine Layer 3.

#### C.1 — `linkright critique --help`

**STDOUT:** Multi-paragraph description. Quotes Satvik's 2026-05-02 design intent. Lists Layer 1/2/3 of Truth Engine.

**STEVE'S VERDICT:** "The help text quotes a Slack message from May 2nd. That's documentation written for the implementer, not the user. Cut the meta-commentary; tell me what this command does for me."

**BEHAVIORAL LENS:** **Authorial leak** — when the implementor's voice / context / authorial intent shows up in user-facing help, the user feels like they're reading internal Notion docs, not a product. Trust drops.

**FIX:** Two-paragraph help: WHAT (LLM critiques your resume + asks per issue if you want to fix it) + WHEN (right after `linkright tailor`). Drop the Satvik quote + Layer 1/2/3 framing. Move that to a `docs/` page if needed. Effort: **S** (rewrite docstring).

#### C.2 — Critique runtime UX

From source: `run_critique` uses questionary for interactive accept/skip per issue. 5 issues max.

**STEVE'S VERDICT:** "Per-issue prompts are right. But what's the user supposed to do if they DISAGREE with the critique? 'Apply' / 'manual edit' / 'skip' covers some of it but doesn't cover 'this critique is wrong, ignore it.' Add a 'mark-bad-critique' option and use that signal to fine-tune."

**BEHAVIORAL LENS:** **Disagreement-as-data** principle (loved by ML product designers). Every "user skipped this critique" is a signal. Distinguish "skip because not relevant now" from "skip because the LLM is hallucinating."

**FIX:** Add a 4th option per issue: `apply / manual edit / skip / dismiss-as-bad-critique`. Last option logs to a feedback file we eventually use to fine-tune the critique prompt. Effort: **S** (one questionary option + one log line).

---

### Journey D — Fill missing metrics [MEDIUM]

#### D.1 — `linkright fill --help`

**STDOUT:** ~15 lines. 4-step description + paragraph on placeholders. References "magnitude tier <= 0.5" — internal scoring jargon.

**STEVE'S VERDICT:** "'Magnitude tier 0.5' — what is that? The user just typed `--help` to LEARN what the command does, not to need a glossary."

**BEHAVIORAL LENS:** **Jargon-as-friction** — every undefined term forces a context-switch (the user has to either skip past it (losing comprehension) or stop and look it up (losing momentum)). System-2 load spikes for nothing.

**FIX:** Replace "bullets whose magnitude tier is <= 0.5 (raw count or no metric)" with: `bullets that count things ('Built 5 features') instead of measuring impact ('Built 5 features that drove 30% adoption')`. Same meaning, zero jargon. Effort: **S**.

#### D.2 — Fill-metrics interactive flow

Per code (`fill_metrics.py`): for each weak bullet, shows 3 LLM-suggested metric types + ranges, user picks one + provides actual value OR placeholder OR cancel.

**STEVE'S VERDICT:** "The 3-option-per-bullet pattern is exactly right. But: how does the user know what 'industry-average ranges' means when our LLM has zero ground truth on real numbers from their company? Tell them the source of the suggestion."

**BEHAVIORAL LENS:** **Confidence calibration** — the user sees 'industry-average: 15-30% efficiency gain' and trusts it. Then they put 18%. That number was hallucinated from training data, not a real benchmark. **Anchoring bias** sets a false floor on what they could/should claim.

**FIX:** Each suggested range carries a disclaimer:
```
Suggested type: cost reduction
  Industry-average range: 8-25% (from LLM training data — verify with your
  team before claiming. Cite a source if available.)
```
Effort: **S** — one-line addition in the prompt.

---

### Journey E — Batch tailor [LIGHT]

#### E.1 — `linkright resume batch --help`

**STDOUT:** Terse. Just 3 flags: `--resume`, `--jds <DIRECTORY>`, `--parallel`. No example of `<DIRECTORY>` structure. No `--parallel` default visible.

**STEVE'S VERDICT:** "The help text is so terse the user has no idea what to put in `--jds`. Is it 1 file per JD? File extension matters? What about the parallel default — do I run 10 in parallel and get rate-limited on first try?"

**BEHAVIORAL LENS:** **Information starvation** at the help layer. Help is the FIRST place a user goes to learn a command — terse help is hostile (Hick's Law goes the other way: too FEW choices when the user has questions = paralysis).

**FIX:** Beef up the help:
```
Tailor resume across a directory of JDs (parallel).

  Expected --jds layout:
    my-jd-folder/
      ├── credoai_pm.md
      ├── stripe_pm.md
      └── razorpay_apm.md
    (each .md file = one JD; one tailored PDF generated per file)

  --parallel default: 2  (raise carefully — Groq free tier rate-limits at
  3 concurrent calls; Cerebras at 1)
```
Effort: **S**.

---

### Journey F — Interview prep [LIGHT]

#### F.1 — `linkright practice --help`

**STDOUT:** ~10 lines. Mentions internal artifact path `<run>/artifacts/15b_interview_prep.json` + step_14 generation source. References Satvik's 2026-05-02 memory.

**STEVE'S VERDICT:** "Same issue as the critique help — internal file paths and Slack quotes shouldn't be in user help. Tell me what I get out of this command, not where the data came from."

**BEHAVIORAL LENS:** Same as C.1 — **authorial leak** + **expertise leak** (path of file the user doesn't care about).

**FIX:** Rewrite docstring: WHAT (interactive interview prep cards from your tailored bullets) + WHEN (after `linkright tailor` — best done before applying to that JD). Effort: **S**.

#### F.2 — STAR-template UX

Help mentions: "STAR seed template (Action pre-filled from the bullet)". User who doesn't know STAR (Situation/Task/Action/Result) is lost.

**STEVE'S VERDICT:** "If you assume the user knows STAR, you're not designing for the new user. If you don't assume, you should at least DEFINE it the first time it appears."

**BEHAVIORAL LENS:** **Assumed-knowledge friction** — common in domain-expert software. STAR is interview-prep jargon. New job-seekers may not know it.

**FIX:** First mention of STAR in any command output should expand: `STAR (Situation / Task / Action / Result) seed template`. Cookie-store a flag in `~/.linkright/state.json` so it only expands once per user. Effort: **S**.

---

## Part B: Cross-cutting findings

Patterns that recurred across multiple journeys.

### X-1: Internal jargon leaks into user-facing surfaces (P1)

**Where it appears:** A.6 (SHA256 hash), B.2 (`step_07_phase_1_2`), B.1 ("16-step pipeline"), C.1 ("Truth Engine Layer 3", Satvik quote), D.1 ("magnitude tier 0.5"), F.1 (artifact json path).

**Steve's pattern verdict:** "The implementor's mental model is bleeding into the user's view. The user doesn't care about phase numbers, magnitude tiers, layer names, or commit dates — they care about what the command does for them right now."

**Behavioral lens:** **Curse of knowledge** (Pinker) — every time the implementor uses internal language in user-facing output, they assume the user shares their context. The user almost never does.

**Unified fix:** Audit all `click.echo` / docstrings / `--help` strings for internal language. Replace with user-meaningful equivalents. Use a glossary doc internally for translations. Effort: **M** (audit + ~30-50 string replacements).

### X-2: Smoke checks surface problems without fix paths (P0)

**Where it appears:** A.4 (`Embedder ✗ ModuleNotFoundError` with no actionable next step) and any other doctor-style output.

**Steve's pattern verdict:** "If you can DETECT a problem programmatically, you can usually FIX it programmatically. If you can't fix it, at least tell the user the exact next command to run."

**Behavioral lens:** **Information without agency** = anxiety. **Yerkes-Dodson curve** — past-optimal arousal degrades performance. Users may abandon rather than work through opaque errors.

**Unified fix:** Every smoke-check failure includes (a) the diagnostic, (b) the fix command if known, (c) optional `--auto-fix` flag at the parent command level. Effort: **M** (per-failure-mode message dictionary + auto-fix wrapper).

### X-3: First-impression density (Hick's Law) (P0)

**Where it appears:** A.1 (no-args = 19-command wall), A.2 (--help same), B.1 (9 flags equal weight).

**Steve's pattern verdict:** "Your tldr is brilliant. Your no-args is bad. Just promote tldr's content to no-args. Costs you nothing; transforms first impression."

**Behavioral lens:** **Hick's Law** + **primacy effect**. First view shapes perceived complexity for the rest of the session. Walls of options anchor "this is complex"; curated 3-4 options anchor "this is simple."

**Unified fix:** Reorder no-args output: 4-step common workflow at top + 🚀 nudge to tldr + commands list at bottom (or hidden behind `--help-all`). Two-tier help on individual commands. Effort: **S** for global pass.

### X-4: Inconsistent command surface depth (P1)

**Where it appears:** Top-level `linkright critique` / `linkright fill` / `linkright tailor` / `linkright contact` / `linkright score` exist as ALIASES to subcommands. Plus 1-letter aliases like `t`, `f`, `c`. Plus prefix-match. Plus full names. **Five ways to invoke the same command.**

**Steve's pattern verdict:** "More ways to invoke isn't generosity — it's choice paralysis. Pick the one or two best paths and double down."

**Behavioral lens:** **Choice paralysis** (Schwartz). 5 valid invocations × N commands = the user can't form a stable mental model. They don't know which alias is "canonical." Defaults exist for cognitive offload — too many defaults defeats the purpose.

**Unified fix:** Pick 2 invocation patterns: (1) full name `linkright resume tailor`, (2) top-level alias `linkright tailor`. Drop the 1-letter shortcuts (`t`, `f`, `c`, `s`, `r`) from default `--help`. Show them only in `linkright tldr` for power users. Effort: **S** (deprecation warnings on 1-letter aliases for 1 release, then remove).

### X-5: End-of-flow whisper (peak-end rule violation) (P0)

**Where it appears:** B.4 (`✓ Done — see <path>`). Likely all other long-running commands.

**Steve's pattern verdict:** "The end of a 4-minute task is the most important moment. Don't waste it on `Done.`"

**Behavioral lens:** **Peak-end rule** (Kahneman). Memory of the experience is anchored on the peak (highest emotion) and the end. Currently the end is the lowest-emotion moment.

**Unified fix:** Every long-running command ends with a structured success summary: what was made + score + suggested next move + open command. See B.4 fix block. Effort: **S** per command (4-5 commands need treatment).

---

## Part C: Improvement backlog

Sorted P0 → P1 → P2. Effort: S = ≤30 LoC, M = single PR, L = multi-PR.

### P0 (do first — biggest UX wins)

| # | Title | Effort | Suggested PR |
|---|---|---|---|
| 1 | No-args output: promote `tldr` content to default | S | `fix(cli): tldr-as-default-help` (X-3) |
| 2 | Long-running commands end with structured success summary (resume tailor, batch, iterate) | S | `feat(cli): peak-end success cards` (X-5, B.4) |
| 3 | Smoke-check failures suggest fix command inline | S | `fix(doctor,setup): actionable failure messages` (X-2, A.4) |
| 4 | Replace `step_07_phase_1_2`-style internal step names in stdout with user-friendly labels | S | `fix(orchestrator): user-friendly step names` (B.2) |
| 5 | `linkright fastembed` not installed — auto-fix offer in `setup` / `doctor` | S | `feat(setup): --auto-install-deps flag` (A.4 extension) |
| 6 | `--llm-mode` default "agent" requires Claude Code/opencode CLI installed; not obvious from --help | S | `fix(cli): clarify llm-mode prerequisites in --help` (B.1 extension) |

### P1 (do next)

| # | Title | Effort | Suggested PR |
|---|---|---|---|
| 7 | Two-tier `--help` on `tailor` and other multi-flag commands (Required / Common / Advanced) | S | `fix(cli): tiered help on multi-flag commands` (B.1, X-1) |
| 8 | `profile show` polish: replace literal "none" placeholders + add P0/P1/P2 legend + fix mid-character truncation | S | `fix(profile): show command polish` (A.5) |
| 9 | `profile status` — drop SHA256 from default; suggest `linkright contact` when portfolio blank | S | `fix(profile): status output polish` (A.6) |
| 10 | `tailor` 3 review checkpoints inline (not separate commands) — match website's gate UX | M | `feat(tailor): inline truth-engine gates with --yes flag` (B.3) |
| 11 | `critique` / `practice` / `fill` help: drop internal artifact paths + Satvik quotes + Layer-N framing | S | `fix(cli): user-facing help cleanup` (X-1, C.1, F.1) |
| 12 | `batch --help`: add expected directory layout example + `--parallel` default + rate-limit warning | S | `fix(batch): help-text robustness` (E.1) |
| 13 | STAR (and other domain jargon) auto-expanded on first appearance, suppressed thereafter | S | `feat(cli): glossary expansion on first use` (F.2) |
| 14 | Doctor pluralization: `1 issue above` not `1 issue(s) above` | S | trivial fix (F-PRE-2) |

### P2 (polish — when time permits)

| # | Title | Effort | Suggested PR |
|---|---|---|---|
| 15 | Deprecate 1-letter aliases (`t`, `f`, `c`, `s`, `r`); show only in tldr | S | `chore(cli): deprecate single-letter aliases` (X-4) |
| 16 | `critique` per-issue add 4th option: `dismiss-as-bad-critique` + log to feedback file | S | `feat(critique): bad-critique signal capture` (C.2) |
| 17 | `fill-metrics` industry-average ranges carry "verify with your team" disclaimer | S | `fix(fill): anchoring-bias disclaimer` (D.2) |
| 18 | Hide companies with 0 nuggets in `profile show` OR show `(no nuggets — try \`profile enrich\`)` | S | `fix(profile): empty-company UX` (A.5 extension) |
| 19 | Doctor's `Embedder fastembed` mismatch: state the fallback in use + impact | S | `fix(doctor): fastembed fallback transparency` (F-PRE-3) |

---

## Part D: Out of scope / not tested

This pass:
- **`linkright watch`** flow — Chrome-attach passive capture. Requires running Chrome with remote-debug port; out of scope for a single TTY pass.
- **`linkright mcp serve`** agent mode — requires integrating with Claude Code or opencode externally; couldn't drive in this session.
- **`linkright jobsearch find/apply`** — requires Pillar 2 backend wiring + an authenticated session against `sync.linkright.in`; CLI scope only here.
- **`linkright stories add/list/search`** — Pillar 3 Story Bank shipped 2026-05-02 but not surfaced in the 6-journey path; rerun a follow-up walkthrough specifically for stories.
- **`linkright resume hypothesis-test`** — research/experimentation flow; not a typical user path.
- **`linkright iterate`** — B1-B9 worst-dim refinement loop; advanced flow.
- **`linkright admin`** subgroup — Oracle PG admin commands; admin-only persona, separate walkthrough warranted.
- **Live `linkright tailor` end-to-end run** — pipeline is 2-4 min wall-clock; single Bash-call timeout makes a full run + capture impractical in this session. Findings B.2 / B.3 / B.4 derived from source-reading of the orchestrator (which I personally just shipped gates into in PR #77, so high-confidence). A follow-up live-walkthrough turn-by-turn would corroborate.
- **First-time setup wizard prompts** — `linkright setup` (interactive questionary) couldn't be driven via Bash heredoc reliably. Findings A.4 derived from `--check` mode (read-only).

Recommended follow-up walkthroughs:
1. Real `linkright tailor` end-to-end run, capturing actual stdout for each of the 13 phases — to corroborate B.2's user-friendly-label fix list.
2. `linkright watch` capture flow — needs Chrome setup.
3. `linkright stories` (Pillar 3) — STAR-format career narrative CRUD; never walked.
4. Admin / Oracle PG admin flows — separate persona.
5. Mobile-resume-builder companion (if/when shipped) — same lens applied to the iOS/Android surface.

---

## Closing — Steve's overall verdict

**LinkRight CLI is a B+ that could be an A with surface-level reordering work.**

What's right: the commands themselves are individually well-designed (every subcommand's behavior is sensible). The 6-journey workflow makes sense once discovered. The Truth Engine 3-layer pattern is genuinely good UX architecture. The tldr is excellent reference material.

What's wrong: discovery is one extra step removed from where it should be (no-args → tldr); first impressions are dense; long-running commands end with a whisper instead of a peak-end summary; internal jargon repeatedly leaks into user-facing surfaces.

**The fixes are almost all small** (effort S for ~16 of the 19 backlog items). This is a pure polish-pass surface — no architectural changes, no new features, no LLM rewrites. A single 1-2 day session of targeted PRs would lift the CLI from "works for the implementor's friends" to "a stranger can use it without help."

**The single highest-leverage fix:** P0 #1 — promote `tldr` content to no-args output. Touches every new user. ~1 hour of work.

---

_Walkthrough captured 2026-05-05 evening session. Cross-reference with `specs/walkthrough-findings-2026-04-18.md` (website-only equivalent)._
