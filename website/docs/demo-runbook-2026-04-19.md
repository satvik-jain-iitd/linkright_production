# Demo runbook — 2026-04-19

Quick reference for the 50-user demo. Covers: what's live, what's fragile,
what to do if something breaks mid-demo.

---

## What's live + verified

| Surface | Status | Verified by |
|---|---|---|
| Landing (/) | ✅ | quality-e2e spec + WebFetch |
| Pricing (/pricing) | ✅ | quality-e2e spec |
| Auth (/auth) | ✅ | auth.setup runs each time |
| Onboarding upload (/onboarding) | ✅ | test user completes parse |
| Profile highlights (/onboarding/profile) | ✅ | quality-e2e spec |
| Preferences (/onboarding/preferences) | ✅ | quality-e2e spec |
| Find roles (/onboarding/find) | ✅ | route loads |
| Resume builder (/resume/new) | ✅ | pipeline works e2e |
| Cover letter (/dashboard/cover-letters) | ✅ | API + UI wired |
| Outreach (/dashboard/outreach?resume_job=…) | ✅ | route loads |
| Dashboard (/dashboard) | ✅ | v2 layout |
| Applications kanban (/dashboard/applications) | ✅ | 6 columns, outcome modal |
| Interview prep hub (/dashboard/interview-prep) | ✅ | 8 drill cards with Soon pill |
| Broadcast connect (/dashboard/broadcast/connect) | ✅ | OAuth flow works |
| Broadcast insights + compose + schedule | ✅ | UI wired; publishing via n8n |
| Profile settings (/dashboard/profile) | ✅ | bulk upload works, disconnect works |
| Notifications drawer | ✅ | bell icon in AppNav |

## Recent wins (last 24 h)

- Hybrid regex+LLM parser — cheaper + less hallucination-prone
- Cover letter one-click from resume review
- LinkedIn DM + recruiter email generators
- Outcome capture on kanban drag (rejected / offer / interview / ghosted)
- Broadcast OAuth + idempotency + token refresh + engagement queue
- Left sidebar removed (was conflicting with top nav)
- 5-tab top nav (Dashboard gold, Profile purple, Applications teal, Interview sage, Broadcast pink)
- Streak mechanic deleted (engagement-farming pattern that contradicted honesty positioning)
- Profile highlights monochrome (was a 4-colour salad)

## Known flaky spots (retry usually fixes)

| Thing | Symptom | Why | Mitigation |
|---|---|---|---|
| parse-resume under burst | 429 response | Groq free tier = 30 req/min | parseResumeWithRetry helper does 4 attempts with 1.5s → 8s backoff. User sees one 20s spinner worst case. |
| Resume generation | 60-90s pipeline | Worker on Render, Gemini + Groq calls | User sees streaming progress, phase indicator, heartbeat. Per-phase 60s timeout kills zombies. |
| Broadcast publishing | n8n dependent | Our webhook is ready; n8n workflow + `BROADCAST_WEBHOOK_SECRET` still to wire | See `broadcast-n8n-workflow.md`. Before demo, run one test post via n8n to confirm. |

---

## Critical pre-demo checklist

- [ ] Vercel deploy is on commit `>= 794f5d7` (`git log --oneline -1 on main`). If older: redeploy from Vercel dashboard.
- [ ] Supabase migrations 030 + 031 + 032 applied.
- [ ] Env vars set in Vercel:
  - `LINKEDIN_CLIENT_ID` ✅
  - `LINKEDIN_CLIENT_SECRET` ✅
  - `LINKEDIN_REDIRECT_URI` ✅
  - `BROADCAST_WEBHOOK_SECRET` — generate with `openssl rand -hex 32` if not set
- [ ] Render worker healthy (visit `/healthz` on worker URL — expect 200 + JSON)
- [ ] One manual smoke-signup: fresh email, upload a resume, see highlights, click Continue, reach find-roles
- [ ] One manual resume build: pick a role, wait 60-90s, download the PDF

---

## Demo flow (suggested 5-minute walkthrough)

1. **Land** — `sync.linkright.in` → show the single headline + 4 proof tiles
2. **Sign up** — `/auth?mode=signup`, Google or email. 15 seconds.
3. **Upload** — `/onboarding` → paste resume text or upload PDF. Point out the two-panel outline + first-person narration.
4. **Profile** — land on `/onboarding/profile` → 12–24 highlight cards. Click one → show follow-up modal. Close, click "Add highlight" → show the editor.
5. **Preferences** — `/onboarding/preferences` → target roles, location, cities, company stage, comp. Click "Find roles".
6. **Find roles** — `/onboarding/find` → spotlighted #1 match + ranked list. Click "Start custom application".
7. **Build** — `/resume/new?job_id=…` → watch layout plan, live writing (60-90s), review with 4-checks panel.
8. **Bolt-ons** — click "Cover letter" → see generation; click "DM + email" → generate both.
9. **Dashboard** — `/dashboard` → show matches + profile card + diary widget
10. **Applications** — `/dashboard/applications` → drag a card to "Interview" → show outcome modal
11. **Broadcast** — `/dashboard/broadcast` → show insights → compose → LinkedIn preview. If n8n ready, schedule one.

## If something breaks

| Symptom | Fast fix |
|---|---|
| Parse-resume times out | Retry once. If still fails, paste a shorter resume (truncate at 4000 chars). |
| Resume build stuck at 58% | Known bug from before. Redeploy Render worker from dashboard; cancel the stuck job; retry with the same JD. |
| Dashboard shows "Welcome to LinkRight" instead of greeting | User has no nuggets yet. Route correctly redirects to /onboarding. Expected. |
| /onboarding/find shows "No matches yet" | Scout hasn't populated user_daily_top_20. Run cron `/api/cron/recompute-top-20` manually via Vercel dashboard → Jobs. |
| LinkedIn connect errors | `LINKEDIN_REDIRECT_URI` must exactly match the one in LinkedIn app settings. |
| Broadcast post stays `scheduled` | n8n workflow not running. Check `/api/broadcast/webhook` with the Bearer secret returns an expected shape. |
| 500 error on /api/nuggets POST | check constraint drift. Check Supabase logs. Current safe values: `primary_layer='A'`, `section_type='work_experience'`. |

---

## Running the test suite yourself

```bash
cd repo/website
PLAYWRIGHT_BASE_URL=https://sync.linkright.in npx playwright test tests/quality-e2e.spec.ts --workers=1
```

Takes ~3 minutes. 17 passing, up to 2 flaky (rate-limit retries).

To debug a specific failure:

```bash
PLAYWRIGHT_BASE_URL=https://sync.linkright.in \
  npx playwright test tests/quality-e2e.spec.ts -g "<test name>" \
  --reporter=list --workers=1 --retries=0
```

Artefacts (screenshots, videos, error-context.md) land in `test-results/`.

## 50-user cap reasoning

- Supabase Pro tier handles 100s of concurrent connections; not a bottleneck.
- Groq free tier caps at 30 req/min. Parse-resume is the only fast-burst LLM surface; at 50 signups/min, 20 get 429s but retry logic catches them within 20s. Acceptable for a demo; upgrade to Groq Dev tier before going past 100 daily users.
- Render worker runs one resume at a time per instance. For 50 simultaneous resume builds, queue depth would spike. Mitigation: users don't all build simultaneously during a demo — they progress through onboarding at their own pace (spread the load). If simultaneous build becomes a real pattern: scale Render to 2 instances (`$12/mo`).
- Jina embeddings: 1M requests/month free tier. Nowhere close.

---

_Generated 2026-04-18. Last verified commit: `794f5d7` / `3c1551f`._
