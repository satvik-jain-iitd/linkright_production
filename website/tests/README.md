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

## Fixtures

- `fixtures/resume.pdf` — a real resume used by PDF-upload tests.
- `fixtures/test-data.ts` — `freshEmail()`, `TEST_PASSWORD`, `RESUME_TEXT`, `TEST_JD`, `TEST_COMPANY_DOMAIN`.

Never fabricate input data in a spec. If you need new inputs, add them to `test-data.ts` and import.
