# LinkRight E2E Test Suite

Playwright-based regression + smoke coverage for `sync.linkright.in`.

## Run

```bash
# Full suite (default: against production https://sync.linkright.in)
npm run test:e2e

# Visual debugger (recommended when iterating on a spec)
npm run test:e2e:ui

# Fast smoke subset — only the specs that don't start the resume pipeline
npm run test:e2e:smoke
```

### Point at a different environment

Override `baseURL` via env var. The three common targets:

```bash
# Vercel preview (post-push, before prod promotion)
PLAYWRIGHT_BASE_URL=https://sync-resume-engine-<hash>.vercel.app npm run test:e2e

# Local dev server (run `npm run dev` first in another terminal)
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e

# Staging — if separate environment is set up
PLAYWRIGHT_BASE_URL=https://staging.linkright.in npm run test:e2e
```

## Coverage map

| Spec | Finding ID | What it asserts |
|---|---|---|
| `auth.setup.ts` | — | Creates a fresh user, saves auth state to `.auth/user.json`. Runs once. |
| `auth.teardown.ts` | — | Deletes the test user after the suite finishes. |
| `onboarding.spec.ts` | journey baseline | Landing nav, pricing page, signup UI. |
| `dashboard.spec.ts` | journey baseline | `/dashboard`, `/dashboard/career`, `/dashboard/nuggets` load without errors. |
| `resume-builder.spec.ts` | journey baseline | Full wizard path (JD → customize → build → review). |
| `scout.spec.ts` | journey baseline | Scout watchlist add + discoveries. |
| `api-scout.spec.ts` | API | Scout API contracts. |
| `api-validation.spec.ts` | API | API input validation. |
| **`sidebar-nav.spec.ts`** | **F-17** | Sidebar shows only 4 real links; no dead Custom Apps / Settings / Admin. No 404s on click. |
| **`profile-token.spec.ts`** | **F-32** | `/dashboard/profile` page renders; generate-token → `LR-XXXX` visible; rotate produces a different value. |
| **`pdf-upload.spec.ts`** | **F-08** | API parses a fixture PDF (via `unpdf`) and returns structured fields. Rejects files >2 MB. |
| **`parse-guards.spec.ts`** | **F-06 + F-07** | LinkedIn hallucination rejected; email not fabricated; verbatim values preserved. |

## Mandatory workflow (captured in `bd memories`)

**Every build ships with spec coverage.** When adding a feature or fixing a bug:

1. Add the code change.
2. Add a matching `.spec.ts` in this folder (one file per behaviour cluster, name it after the surface — `sidebar-nav`, `profile-token`, etc).
3. Run `npm run test:e2e:smoke` locally before pushing.
4. CI (when wired) runs the full suite on every PR.

Reason: regressions are the fastest way to lose 10 paying users' trust. Catching them with tests costs 5 min; catching them with a bug report costs 5 hours.

## Test-suite philosophy

Four non-negotiable rules (audit doc: `specs/test-suite-audit-2026-04-18.md`).

1. **Test against where the product is going, not where it was.** A test that asserts the presence of a UI element about to be deleted is test debt. Check every failing test against the current-wave plan before patching it.
2. **When a feature is being sunset, skip, don't delete.** Wrap the legacy test body in `test.skip()` with a standardised comment:
   ```ts
   // SKIP-PENDING-WAVE-N (YYYY-MM-DD): <one-line reason>.
   // See specs/test-suite-audit-YYYY-MM-DD.md.
   test.skip('old-feature test name', async () => { ... });
   ```
   The skip is a breadcrumb — the body documents what we had, the comment says why we stopped, the audit doc says when to delete.
3. **Write new-feature specs BEFORE the feature ships.** TDD-lite. Even if every test is `test.skip()` with an assertion outline, it locks intent. See `onboarding-v2.spec.ts` and `voice-interview.spec.ts` for the pattern.
4. **Never soften an assertion just to make a red bar green.** Ask first: is the assertion still true for where the product is going? If yes, the code is the bug. If no, skip the test.

## Current legacy-skip inventory (delete when the named wave ships)

| File | Test | Deletes when |
|---|---|---|
| onboarding.spec.ts | step 2 — Save & Continue → TruthEngine | Wave 2 StepJobPreferences ships |
| onboarding.spec.ts | step 3 — session token in onboarding | Wave 2 (token moves to /profile, already covered by profile-token.spec.ts) |
| onboarding.spec.ts | step 3 — Interview Coach skill zip | Wave 2 + Wave 4 (replaced by voice-interview.spec.ts) |
| onboarding.spec.ts | skill uses pre-written dispatch code | Same as above |
| onboarding.spec.ts | step 3 — atom dispatch running count | Wave 2 |
| onboarding.spec.ts | step 4 — career data count | Wave 2 (summary screen replaced by StepJobListings) |
| onboarding.spec.ts | step 4 — "Create Your First Resume" / "Go to Dashboard" | Wave 2 (CTAs replaced by "Start Custom Application") |

## Fixtures

- `fixtures/resume.pdf` — a real resume used by PDF-upload tests.
- `fixtures/test-data.ts` — `freshEmail()`, `TEST_PASSWORD`, `RESUME_TEXT`, `TEST_JD`, `TEST_COMPANY_DOMAIN`.

Never fabricate input data in a spec. If you need new inputs, add them to `test-data.ts` and import.
