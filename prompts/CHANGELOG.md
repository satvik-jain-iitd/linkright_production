# Prompt Version Changelog

## v3.0.0 (2025-04-05)
- Added Rule 32 (Anti-AI Writing) — banned vocabulary list + structural pattern detection
- Added Rule 33 (Application answers are human) — first person, conversational tone
- Added Phase 4.6 (AI Writing Audit) — vocabulary scan, structural patterns, read-aloud test
- Added Phase 12 (Application Form Assistance) — post-resume help for job applications
- Added character budget hints to Phase 4.2 (88-96 chars for bullets, 92-100 for edge-to-edge)
- Added validation gates: Phase 3.2 (page fit HARD GATE), Phase 5.4 (flag user after 3 failures), Phase 8.1.5 (pre-assembly checklist), Phase 8.3 (post-assembly validation)
- Fixed 6 bugs: bold regex, link nesting, section wrappers, spacing defaults, CSS standardization

## v2.1.0 (2025-03-31)
- Added Phase 1.5 (Narrative Draft & Experience Mapping)
- Added Phase 3.0 (Page Height Budget)
- Added Phase 3.5 (Bullet Group Strategy with Pyramid Principle)
- Added Phase 4.0 (Professional Summary)
- Added Phase 4.5 (Self-Review Loop)
- Added Brand Guideline Confirmation (Phase 2.3)
- Added metric color highlighting (`.li-content b`)
- Added file naming convention (`{folder-name}.html`)
- Increased `--ul-group-gap` to 3mm
- Rules 27-31 added

## v2.0.0 (2025-03-21)
- Initial v2 release
- 8 MCP tools implemented
- 11-phase pipeline with 26 hard rules
- XYZ bullet format enforcement
- Width optimization loop (measure -> suggest -> rewrite)
- BRS scoring model (5-factor weighted)
