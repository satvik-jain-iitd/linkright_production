# LinkRight UAT Bug Log

This file tracks issues found during end-to-end testing of the LinkRight CLI.

## Issues Table

| ID | Command | Component | Issue Description | Status |
|----|---------|-----------|-------------------|--------|
| 1 | `linkright doctor` | CLI / UX | `linkright doctor --auto-fix` is suggested even when no auto-fixable issues exist. | Open |
| 2 | Systemic | CLI / UX | Terminal output is cluttered with technical "noise" (stack traces, library reports, `[tokens]` labels). | Open |
| 3 | Systemic | CLI / UX | CLI output suggests flag-based commands (e.g. `--auto-fix`, `-j`, `--force`) to non-technical users. | Open |
| 4 | `linkright profile create` | Profile / Ingest | CLI claims to support `.md` files but fails with "invalid pdf header" error. | **Fixed (Cluster A)** |
| 5 | `linkright profile create` | Truth Engine | Name extraction includes greetings (e.g., "Dear Satvik Jain"). | Open |
| 6 | `linkright profile create` | Profile / Ingest | No validation to ensure the file is a resume (e.g., certificates create garbage profiles). | Open |
| 7 | `linkright profile show` | CLI / UX | Displays internal metadata (dir paths, embedder dimensions) in the header. | Open |
| 8 | `linkright profile show` | CLI / UX | Nuggets are truncated at 120 chars by default, hiding user's own data. | Open |
| 9 | `linkright profile create` | CLI / UX | Error messages suggest complex flags (`--force`) instead of interactive overwrite prompts. | Open |
| 10 | `linkright profile create` | CLI / UX | "Auto-detect folder" option adds unnecessary complexity to the ingestion menu. | Open |
| 11 | `linkright profile create` | CLI / UX | Missing "Paste Text" option for direct profile ingestion. | Open |
| 12 | Systemic | Profile / Ingest | No mechanism to chunk/partition long documents, risking context limit failures. | Open |
| 13 | Systemic | Truth Engine | Missing Regex-based pre-extraction for high-confidence fields (Email, Phone). | Open |
| 14 | Systemic | CLI / UI | Missing structural horizontal dividers to wrap role-based interactions (input vs response). | Open |
| 15 | Systemic | CLI / UI | Missing a brand character/icon (e.g., octopus/robot style) to anchor the prompt area. | Open |
| 16 | Systemic | CLI / UI | Lack of sticky footer with semantic coloring (Gold/Orange for Tier, Mint/Teal for Mode, Muted for Status). | Open |
| 17 | Systemic | CLI / UI | Menus don't support Tab/Shift-Tab for horizontal navigation between question categories. | Open |
| 18 | Systemic | CLI / UI | "Recommended" solutions use inconsistent emojis instead of parenthetical text labels. | Open |
| 19 | Systemic | CLI / UI | Missing "Type something" custom input entry in selection lists. | Open |
| 20 | Systemic | CLI / UI | Previous user inputs are not rendered with the high-contrast white bullet (`●`) pattern. | Open |
| 21 | Systemic | CLI / UI | Progress verbs (e.g. `Smooshing...`) lack the distinct coral/salmon color and subtle grayish telemetry. | Open |
| 22 | Systemic | CLI / UI | Secondary information (Tips) does not follow the L-shaped (`└`) muted-text branch pattern. | Open |
| 23 | Systemic | CLI / UI | Standardized Iconography: Must adopt BMAD Standard (◇ for input, ● for info, 🌟 for highlights, ✓ for success). | Open |
| 24 | Systemic | CLI / UI | Prompt character is inconsistent. Should use a bold, clean `❯` marker. | Open |
| 25 | Systemic | Profile / Logic | Nugget pool pollution: Static facts (Education, Degree) are stored as generic nuggets, risking retrieval noise. | Open |
| 26 | `linkright profile enrich` | Profile / Logic | Improper nugget ordering: New P0 nuggets appear at the bottom; list is not sorted by Priority (P0->P3). | Open |
| 27 | Systemic | Truth Engine | Entity extraction failure: Nuggets tagged as "unknown" or "none" even when the company/school is in the text. | Open |
| 28 | `linkright profile create` | Profile / Logic | Missing "Gap-Filling" loop: System should ask immediate follow-ups if key details (Role, Company, Dates) are missing. | Open |
| 29 | Systemic | CLI / UI | Vague Priority Legend: P0-P3 lack clear, quantified definitions based on metrics and impact depth. | Open |
| 30 | Systemic | CLI / UI | Use "Claude Code" pattern for sub-context: render secondary details (e.g., metadata, timestamps) in muted gray text. | Open |
| 31 | Systemic | Profile / Enrichment | Generation of vague/fluff metrics: System suggests meaningless phrases like "Increased business value by 100%". | Open |
| 32 | Systemic | Profile / Logic | Missing Nugget Audit/Cleanup Phase: No automated loop to re-analyze all nuggets for metric sharpness and reprioritize. | Open |
| 33 | `linkright tailor` | Tailor / UX | Silent JD Analysis: The system skips showing the JD interpretation (P0/P1/P2 requirements) to the user. | Open |
| 34 | `linkright tailor` | CLI / UX | Opaque Cache Info: "Profile cache hit" message provides no detail on what is being reused or how to inspect it. | Open |
| 35 | `linkright tailor` | Tailor / Logic | Contact Info Desync: `tailor` shows "blank" contact details even if the profile was recently updated via `linkright contact`. | Open |
| 36 | `linkright tailor` | CLI / UI | Pipeline Execution screen lacks visual hierarchy; telemetry (Run ID, Output) is cluttered and lacks muted styling. | Open |
| 37 | `linkright tailor` | Tailor / UX | Blocker: Verification step has no "Done/Continue" option after editing fields, trapping the user in an infinite loop. | **Fixed (Cluster A)** |
| 38 | `linkright tailor` | Tailor / UX | JD analysis happens too late in the pipeline (step 5); should happen immediately after JD input. | Open |
| 39 | `linkright tailor` | Tailor / UX | "Strategy Review" lacks layout insights: doesn't show height distribution, section utilization, or page-fit probability. | Open |
| 40 | Systemic | CLI / UX | Abort behavior is destructive: pressing "No" on a continue prompt kills the pipeline with an error instead of offering an edit/back path. | **Fixed (Cluster A)** |

---

## Cluster Tracker

- **Cluster A (Critical Blockers)** — #4, #37, #40 — **FIXED** in `fix/uat-cluster-a-critical-blockers` branch. Minimal non-destructive fixes; full edit-and-retry menu deferred to Cluster C.
- **Cluster B (Profile/UX Quick Wins)** — #1, #2, #5, #6, #7, #8, #9, #11, #13 — Pending
- **Cluster C (Tailor UX Redesign)** — #33, #34, #35, #36, #38, #39 — Pending (includes inline edit menu replacing Cluster A restart hint)
- **Cluster D (Profile Logic)** — #25, #26, #27, #28, #31, #32 — Pending
- **Cluster E (UI Design System)** — #14, #15, #16, #17, #18, #19, #20, #21, #22, #23, #24, #29, #30 — Pending (separate sprint; design pass first)
- **Cluster F (Misc Systemic)** — #3, #10, #12 — Pending

---

## Detailed Analysis

### 37. Tailor / UX: Contact Verification Blocker (Infinite Loop)
**Description:** In the `linkright tailor` workflow, after the user finishes editing individual contact fields (Email, Phone, etc.), there is no clear "Submit" or "Done" button to move to the next phase of the pipeline. The user is trapped in the edit menu.
**Root Cause:** The exit option in `step_01b_verify_contact_details` was labeled `"s — skip all (keep as-is)"`, which users mistook for "discard my edits" rather than "I'm done editing". The option worked, but its wording was unrecognisable as a confirmation action.
**Fix (Cluster A):** Renamed to `"✓  All correct — save & continue"`, placed at the top of the choice list, with a checkmark for visual prominence. Underlying `value="s"` preserved so the existing exit logic at `orchestrator.py:1042` is untouched. Input() fallback similarly relabeled.

### 38. Tailor / UX: Sub-optimal Step Sequencing
**Description:** JD analysis currently occurs at Step 5 of the pipeline. This is too late, as the user wants to see the system's interpretation of the job immediately after providing the input.
**Expected Behavior:** Move JD Analysis (Step 5) to Step 1 or 2, immediately following JD input. This also provides "processing time" for background tasks like embedding.

### 39. Tailor / UX: Shallow Strategy Insights
**Description:** The "Strategy Review" panel only shows company inclusion and bullet counts. It lacks critical "Layout Intelligence" that users need to trust the 1-page fit.
**Expected Behavior:** Redesign the Strategy Review to include:
1.  **Vertical Space Distribution:** Estimated % of page height per section (Experience, Education, etc.).
2.  **Fit Probability:** System's confidence in achieving a 1-page layout without dropping sections.
3.  **Section Economics:** How many lines each section is projected to hold.

### 40. Systemic: Destructive "No" Path
**Description:** Whenever the system asks "Continue to next phase? [Y/n]", selecting "n" triggers a `pipeline error aborted` and ends the process entirely.
**Root Cause:** `click.confirm(..., abort=True)` raises `click.Abort` on "No", which Click handles as a hard error with non-zero exit + traceback.
**Fix (Cluster A — minimal):** Changed to `abort=False` at both gate sites (`_see_and_continue` and `_strategy_review_gate`), with a clean `sys.exit(0)` plus a restart hint when "No" is selected. Pipeline now pauses cleanly instead of self-destructing.
**Fix (Cluster C — full):** Replace the restart hint with an inline edit-and-retry menu offering: Edit JD, Edit Strategy, Change Model, Back to previous step. Tracked separately.
