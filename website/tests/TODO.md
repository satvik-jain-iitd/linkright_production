# E2E Test TODO

Items deferred from the perf-and-coverage sprint (plan: `~/.claude/plans/okay-look-at-the-sunny-walrus.md`). Do these in a dedicated session when their external dependencies are ready.

## Blocked on external setup

### LinkedIn OAuth E2E flow (~3-4 hrs)
Need a dedicated LinkedIn test app + redirect URL whitelisted for `localhost:3000` and Vercel preview domains. Then:
- Hit `/api/broadcast/oauth/start` → follow redirect to LinkedIn consent → mock-accept → land on `/api/broadcast/oauth/callback` → assert `user_integrations` row created with `provider=linkedin, status=connected`
- POST a draft → publish via `/api/broadcast/posts/[id]/publish` (or whatever the publish endpoint is) → poll for `status=posted` → verify `linkedin_post_urn` populated
- Disconnect via `/api/integrations/linkedin/disconnect` → assert row marked `status=disconnected`

Why blocked: LinkedIn requires a real client_id/secret and approved redirect URIs. Cannot mock at network layer without intercepting OAuth state CSRF token.

### Voice interview / Whisper transcription unskip (~2 hrs)
Currently `tests/voice-interview.spec.ts` has 8 `test.skip()` calls waiting on Wave 4 backend. Per the spec's header comment, unskip when:
1. `POST /api/diary` accepts `audio_url` (✅ already does — see daily-memory.spec.ts)
2. `POST /api/diary/transcribe` exists and proxies Groq distil-whisper
3. `<DailyDiary>` component on dashboard + onboarding has the "Tap to speak" button

Why blocked: `/api/diary/transcribe` not yet implemented. Once landed, just flip `test.skip` → `test` in voice-interview.spec.ts.

## Useful but lower-priority

### Onboarding v2 spec body (~1 hr)
`tests/onboarding-v2.spec.ts` exists but is empty (0 tests). Should mirror `tests/onboarding.spec.ts` (314 lines) against the v2 design system once Wave 2 visual changes are stable.

### Journey-full assertion upgrade (~2 hrs)
`tests/journey-full.spec.ts` is currently a visual-screenshots-only smoke. Upgrade to functional: at each step, assert the underlying API state changed (e.g. after profile creation, GET `/api/profile` returns expected shape; after first job match, GET `/api/discoveries` returns ≥1 item).

### Coverage matrix doc (~30 min)
Generate a per-pillar coverage matrix from `npx playwright test --list` and check into `tests/COVERAGE.md`. Useful for spotting drift before it bites.

## Done in this sprint

- ✅ Resume tailoring quality assertions (`real-world-personalize.spec.ts` test 3 + new test 4 PDF smoke) — commit `8763450`
- ✅ Cover letter contract spec (`cover-letter.spec.ts`) — commit `8763450`
- ✅ Apply + Kanban workflow (`scout.spec.ts` Block 3) — commit `8763450`
- ✅ Daily memory text-mode (`daily-memory.spec.ts`)
- ✅ Broadcast posts + engagement-queue contract (`broadcast-engagement.spec.ts`)
- ✅ Mock data samples consolidated to `tests/fixtures/samples/` — commit `90017a6` + `080c2cb`
