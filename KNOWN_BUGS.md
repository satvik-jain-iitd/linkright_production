# Known Bugs & Fixes — Resume Customization Pipeline

## Bug 1: assemble_html Double-Nested Contact Links
- **Symptom:** Contact links rendered as `<a><a>...</a></a>` (double-wrapped)
- **Root Cause:** Pre-linked `<a href="mailto:...">` tags in header contacts were re-wrapped by assemble_html's automatic link injection logic
- **Fix:** Bypassed assemble_html for header section; wrote HTML directly with pre-formatted contacts
- **Status:** Workaround (assemble_html link detection not patched)
- **Resume:** crypto-exchange_sr-pm-aml

## Bug 2: assemble_html Missing Section Wrappers
- **Symptom:** Assembled HTML sections lost their `<div class="section">` wrapper divs, breaking spacing
- **Root Cause:** Section injection logic in assemble_html stripped outer container divs during template injection
- **Fix:** Bypassed assemble_html; wrote full HTML directly with proper section wrappers
- **Status:** Workaround (assemble_html not patched)
- **Resume:** crypto-exchange_sr-pm-aml

## Bug 3: 14px Page Overflow After 6-Section Assembly
- **Symptom:** Resume overflowed by ~14px (~3.7mm) after assembling all 6 sections
- **Root Cause:** Template defaults (`--section-spacing: 4mm`, `--entry-spacing: 3.5mm`) too generous for 6 sections with 15+ bullets
- **Fix:** Reduced `--section-spacing: 4mm → 3.5mm` and `--entry-spacing: 3.5mm → 3mm` in the resume CSS
- **Status:** Fixed
- **Resume:** crypto-exchange_sr-pm-aml

## Bug 4: Sukha Education Bullet Overflow (110.5%)
- **Symptom:** Sukha Education bullet measured at 110.5% width on first draft
- **Root Cause:** Initial bullet text included too many details ("Google Workspace, Slack, and Salesforce implementation across 50+ volunteers, saving Rs. 60,000/yr via 12-week tech rollout")
- **Fix:** Trimmed through 2 rounds of measure-rewrite: removed "Google Workspace", shortened phrasing → 99.3%
- **Status:** Fixed
- **Resume:** crypto-exchange_sr-pm-aml

## Bug 5: Scholastic Line Below 95% (94.4%)
- **Symptom:** Scholastic achievements edge-to-edge line measured at 94.4%, below the 95% floor (Rule 17)
- **Root Cause:** Text slightly too short for edge-to-edge justified rendering
- **Fix:** Expanded by adding "School" before "Rank 1" → "CBSE School Rank 1" → 97.8%
- **Status:** Fixed
- **Resume:** crypto-exchange_sr-pm-aml

## Bug 6: Preview Server Serving Wrong Directory
- **Symptom:** `preview_start` served files from wrong directory; `python3 -m http.server --directory` flag was ignored
- **Root Cause:** The Claude Preview MCP tool reuses existing server instances and may not respect the `--directory` argument when a server with the same name was previously started from a different path
- **Fix:** Injected HTML directly into the page using `preview_eval` with `document.documentElement.innerHTML`
- **Status:** Workaround (preview tool limitation)
- **Resume:** highlevel_pm-workflows

## Bug 7: All Bullets Overflow on First Draft (Systemic)
- **Symptom:** Every bullet in every resume measures 105-130% width on first draft attempt
- **Root Cause:** LLM consistently writes bullets that are longer than the 101.4 character-unit budget. The XYZ format + natural language verbosity produces ~120-140 CU text before measurement.
- **Fix:** Expected behavior — requires 4-6 rounds of the measure → trim → remeasure loop per bullet. The pipeline's Phase 5 (Width Optimization) handles this systematically.
- **Status:** Systemic / By Design
- **Resume:** Both
