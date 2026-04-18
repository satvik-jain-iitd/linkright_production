# Broadcast → LinkedIn publishing via n8n

The LinkRight broadcast feature (drafts, schedules, tracks LinkedIn posts)
**intentionally does not publish directly**. All publishing goes through an
n8n workflow you run + own. This doc is the **full plan** — architecture,
token lifecycle, failure modes, scaling, runbook. Read once end-to-end
before importing anything.

---

## Part 0 — The key mental model (read first)

> **ONE workflow serves all users.** You never create a per-user
> workflow. The workflow is stateless; it queries our webhook, gets back
> a list of due posts across all users (each with that user's access
> token embedded), publishes each, reports back.

**What lives where:**

| Data | Where it lives | Why |
|---|---|---|
| User's LinkedIn OAuth token | Our Supabase DB (`user_integrations`) | Per-user secret, RLS-protected. n8n sees tokens only in the specific webhook response for due posts. |
| Scheduled posts | Our Supabase DB (`broadcast_posts`) | Source of truth. UI writes here; n8n reads here. |
| Workflow definition (JSON) | `repo/n8n/workflows/broadcast-publish.json` | Version-controlled. Import once into n8n; re-import on updates. |
| Cron schedule | Inside n8n | We control cadence (default every 5 min) via n8n, not via Vercel. |
| Webhook secret | Vercel env + n8n credentials | Shared secret between app and workflow. |

**What this means for multi-user onboarding:**

1. A brand-new user signs up → they click "Connect LinkedIn" in the
   LinkRight UI → our OAuth callback writes `user_integrations` → that's
   it. No n8n action required.
2. The existing n8n workflow will automatically pick them up the next
   time it polls — because the webhook now includes that user's rows.
3. You never touch the workflow when a new user joins. Scaling from 1 →
   1000 users is a config-free operation.

The whole system is intentionally designed so that you — the admin — only
touch n8n when:
- First-time setup
- Workflow updates (bug fixes, new features)
- Debugging a specific failure

---

## Part 1 — Environment setup (you have done some of this)

| Name | Status | Value | Where |
|---|---|---|---|
| `LINKEDIN_CLIENT_ID` | ✅ set | From LinkedIn Developer app | Vercel |
| `LINKEDIN_CLIENT_SECRET` | ✅ set | From LinkedIn Developer app | Vercel |
| `LINKEDIN_REDIRECT_URI` | ✅ set | `https://sync.linkright.in/api/broadcast/oauth/linkedin/callback` | Vercel |
| `BROADCAST_WEBHOOK_SECRET` | ❌ TODO | Generate with `openssl rand -hex 32` | Vercel + n8n |
| `N8N_BASE_URL` | ❌ TODO | `https://naten.linkright.in` (your Oracle deploy) | For documentation, not code |

LinkedIn app setup (if not already done):
- https://www.linkedin.com/developers/apps → your LinkRight Broadcast app
- Products → add "Sign In with LinkedIn using OpenID Connect" + "Share on LinkedIn"
- Auth tab → redirect URI must match `LINKEDIN_REDIRECT_URI` exactly
- Requested scopes: `openid profile email w_member_social`

---

## Part 2 — Architecture: full picture

```
┌────────────────────────────────────────────────────────────────────────┐
│                            LinkRight webapp                            │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────────┐ │
│ │ /broadcast/ │ │ /api/oauth/ │ │ /api/       │ │ /api/broadcast/    │ │
│ │  compose UI │ │  linkedin/* │ │  broadcast/ │ │  webhook (GET+POST)│ │
│ │             │ │             │ │  posts CRUD │ │                    │ │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────────┬──────────┘ │
│        │               │               │                  │            │
└────────┼───────────────┼───────────────┼──────────────────┼────────────┘
         │               │               │                  │
         │ writes        │ writes        │ writes           │ reads due / writes result
         ▼               ▼               ▼                  │
┌────────────────────────────────────────────────────────┐  │
│                   Supabase Postgres                    │  │
│                                                        │  │
│ user_integrations (per-user OAuth tokens)              │  │
│ broadcast_posts   (drafts / scheduled / posted)        │  │
│ user_notifications (post_sent / post_failed pings)     │  │
└────────────────────────────────────────────────────────┘  │
                                                            │
                                                            │ HTTPS + Bearer secret
                                                            ▼
                                 ┌──────────────────────────────────────────┐
                                 │       n8n @ naten.linkright.in           │
                                 │                                          │
                                 │  ┌──────────┐                            │
                                 │  │ Cron 5m  │─────────────────────┐      │
                                 │  └──────────┘                     │      │
                                 │  ┌──────────┐                     │      │
                                 │  │ Cron 6h  │───┐                 │      │
                                 │  └──────────┘   │                 │      │
                                 │                 ▼                 ▼      │
                                 │        ┌─────────────────┐ ┌───────────┐ │
                                 │        │ Engagement poll │ │ Publish   │ │
                                 │        │ workflow        │ │ workflow  │ │
                                 │        └────────┬────────┘ └─────┬─────┘ │
                                 │                 │                │       │
                                 │                 ▼                ▼       │
                                 │        LinkedIn socialActions    LinkedIn│
                                 │        + UGC reads               /ugcPosts│
                                 └──────────────────────────────────────────┘
```

**Two workflows, both stateless, both driven by our webhook:**

1. **Publish workflow** — cron every 5 min. Picks up due scheduled posts
   and publishes them.
2. **Engagement workflow** — cron every 6 h. Picks up posts without
   engagement data and fetches likes/comments from LinkedIn.

---

## Part 3 — User onboarding flow (OAuth)

This is already built + deployed. Documented here for completeness.

```
User                  LinkRight web                  LinkedIn                     Supabase
 │                         │                             │                            │
 │  click Connect LinkedIn │                             │                            │
 │───────────────────────▶│                             │                            │
 │                         │  302 to LinkedIn OAuth     │                            │
 │◀───────────────────────│                             │                            │
 │                         │                             │                            │
 │  authorize w_member_social                            │                            │
 │──────────────────────────────────────────────────────▶│                            │
 │                         │                             │                            │
 │  redirect ?code=xyz     │                             │                            │
 │──────────────────────▶│                              │                            │
 │                         │  exchange code for token   │                            │
 │                         │────────────────────────────▶│                            │
 │                         │◀────────────────────────────│                            │
 │                         │  { access_token, refresh, expires_in }                   │
 │                         │                             │                            │
 │                         │  upsert user_integrations                                │
 │                         │─────────────────────────────────────────────────────────▶│
 │                         │                                                          │
 │  302 to /dashboard/broadcast?linkedin=connected                                    │
 │◀─────────────────────── │                                                          │
```

Notes:
- Token lifetime: LinkedIn access tokens last **60 days**.
- Refresh token returned: varies by app type. Most LinkedIn OIDC apps get
  a ~365-day refresh token.
- User can revoke anytime at linkedin.com/psettings/permissions.

---

## Part 4 — Token lifecycle (critical for multi-user)

This is the part that breaks if you ignore it. Tokens expire. When they
do, the user's scheduled posts start silently failing.

### 4a. Storage (done)

`user_integrations` row per (user_id, provider="linkedin"):

```sql
access_token    text           -- encrypted at rest via Supabase column encryption later
refresh_token   text
expires_at      timestamptz
status          text           -- 'connected' | 'revoked' | 'expired'
```

### 4b. Refresh flow (TODO — needs a new Vercel cron)

Create `/api/cron/refresh-linkedin-tokens` endpoint:

- Runs daily at 3:00 AM IST via Vercel Cron (`vercel.json` already has
  cron config — add one more entry).
- Queries: `user_integrations WHERE provider='linkedin' AND status='connected' AND expires_at < now() + interval '7 days'`
- For each: POST `https://www.linkedin.com/oauth/v2/accessToken`
  with `grant_type=refresh_token`, `refresh_token`, `client_id`,
  `client_secret`.
- Success → update access_token + expires_at + refresh_token (if
  returned) in DB.
- Failure → mark status='expired', insert a user_notifications row
  saying "LinkedIn connection expired — reconnect to keep scheduling".

**Implementation priority:** medium. Not needed until a user hits 60
days of active use — no blocker for the first 30 days.

### 4c. Expiry handling at publish time

The webhook already handles this:

- `GET /api/broadcast/webhook` reads `user_integrations.access_token` +
  `expires_at` for each due post's user.
- If `expires_at < now()` OR `status != 'connected'`, the `linkedin`
  field in the webhook response is `null`.
- n8n sees `linkedin: null` → calls callback with
  `status: "failed", failed_reason: "linkedin_not_connected"`.
- Our webhook writes a `post_failed` notification → bell icon pings the
  user to reconnect.

### 4d. Revocation (user-initiated)

When the user clicks "Disconnect" in `/dashboard/profile`:

1. Frontend calls a new endpoint (TODO): `POST /api/broadcast/oauth/linkedin/disconnect`
2. Endpoint POSTs to LinkedIn's revoke URL:
   `POST https://www.linkedin.com/oauth/v2/revoke?client_id=...&client_secret=...&token=...`
3. Updates `user_integrations.status='revoked'`.
4. Any queued posts for that user in n8n's next poll will fail with
   `linkedin_not_connected` until reconnect.

---

## Part 5 — Publish workflow (n8n — import this)

### 5a. Nodes

```
┌─────────────┐   ┌──────────────┐   ┌────────────────┐
│ Cron 5 min  │──▶│ HTTP GET     │──▶│ Split in batches │
└─────────────┘   │ /webhook     │   │ (per post)       │
                  └──────────────┘   └───────┬──────────┘
                                             │
                                             ▼
                                   ┌──────────────────┐
                                   │ IF linkedin set  │
                                   └──┬───────────┬───┘
                                  yes │           │ no
                                      ▼           ▼
                          ┌──────────────────┐   ┌──────────────────┐
                          │ HTTP POST        │   │ HTTP POST        │
                          │ LinkedIn ugcPosts│   │ callback         │
                          │                  │   │ failed=not_      │
                          │                  │   │  connected       │
                          └────────┬─────────┘   └──────────────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │ HTTP POST        │
                          │ callback         │
                          │ posted | failed  │
                          └──────────────────┘
```

### 5b. GET "due posts" node

- Method: `GET`
- URL: `https://sync.linkright.in/api/broadcast/webhook`
- Header: `Authorization: Bearer {{ $env.BROADCAST_WEBHOOK_SECRET }}`

Response shape:

```json
{
  "due": [
    {
      "post_id": "uuid",
      "user_id": "uuid",
      "content": "40% of our users were dropping off...",
      "scheduled_at": "2026-04-19T09:30:00Z",
      "linkedin": {
        "access_token": "AQV...",
        "author_urn": "urn:li:person:ABC123",
        "expires_at": "2026-05-19T09:30:00Z"
      }
    },
    { "...more posts..." }
  ]
}
```

The response lists posts **across all users** — that's how one workflow
handles many users. Each post's `linkedin.access_token` is that user's
token.

### 5c. LinkedIn POST node (per post)

- Method: `POST`
- URL: `https://api.linkedin.com/v2/ugcPosts`
- Headers:
  - `Authorization: Bearer {{ $json.linkedin.access_token }}`
  - `X-Restli-Protocol-Version: 2.0.0`
  - `Content-Type: application/json`
- Body:

```json
{
  "author": "{{ $json.linkedin.author_urn }}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": { "text": "{{ $json.content }}" },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

Success response header `x-restli-id` contains the LinkedIn post URN.

### 5d. Callback POST node (always fires)

- Method: `POST`
- URL: `https://sync.linkright.in/api/broadcast/webhook`
- Header: `Authorization: Bearer {{ $env.BROADCAST_WEBHOOK_SECRET }}`

On success:

```json
{
  "post_id": "{{ $json.post_id }}",
  "status": "posted",
  "linkedin_post_id": "{{ $node['LinkedIn POST'].headers['x-restli-id'] }}",
  "posted_at": "{{ $now.toISO() }}"
}
```

On failure (HTTP 4xx/5xx from LinkedIn OR linkedin=null):

```json
{
  "post_id": "{{ $json.post_id }}",
  "status": "failed",
  "failed_reason": "{{ $json.linkedin ? $node['LinkedIn POST'].json.message : 'linkedin_not_connected' }}"
}
```

---

## Part 6 — Engagement workflow (second n8n workflow)

Fetches likes/comments for posts published in the last 14 days.

### 6a. Nodes

```
Cron 6h  →  HTTP GET /api/broadcast/engagement-queue
         →  Split in batches (per post)
         →  LinkedIn socialActions GET
         →  Callback HTTP POST
```

### 6b. Engagement-queue endpoint (TODO)

Add `GET /api/broadcast/engagement-queue`:

- Auth: Bearer webhook secret (same as publish webhook)
- Query: posts where `status='posted'`, `linkedin_post_id IS NOT NULL`,
  `posted_at > now() - interval '14 days'`, and either no
  `engagement_json` OR `engagement_json.updated_at < now() - interval '6 hours'`
- Returns: `{ queue: [{post_id, linkedin_post_id, linkedin: {access_token}}] }`

### 6c. LinkedIn socialActions call

- Method: `GET`
- URL: `https://api.linkedin.com/rest/socialActions/{{ encodeURIComponent $json.linkedin_post_id }}`
- Headers:
  - `Authorization: Bearer {{ $json.linkedin.access_token }}`
  - `LinkedIn-Version: 202401`
  - `X-Restli-Protocol-Version: 2.0.0`

### 6d. Callback to our webhook (existing POST)

```json
{
  "post_id": "{{ $json.post_id }}",
  "status": "posted",  // unchanged; engagement-only update
  "engagement_json": {
    "likes": "{{ $json.likesSummary.totalLikes }}",
    "comments": "{{ $json.commentsSummary.aggregatedTotalComments }}",
    "shares": 0,
    "impressions": 0
  }
}
```

**Note on impressions:** requires LinkedIn Marketing Developer Platform
access (paid, approval-gated). Defer until needed — likes + comments are
the meaningful signal.

---

## Part 7 — Failure modes + recovery

| Failure | What user sees | Recovery |
|---|---|---|
| Token expired | "LinkedIn connection expired — reconnect" notification; scheduled posts pile up in `status=scheduled` | User clicks Reconnect → OAuth flow → next n8n poll picks up the backlog |
| User revoked | Same as expired | Same. LinkedIn returns 401, webhook callback writes failed_reason. |
| LinkedIn 429 rate limit | One post `status=failed`, `failed_reason` mentions rate limit | n8n should retry with exponential backoff (3 attempts). Only then write `status=failed`. |
| LinkedIn 5xx outage | Multiple posts `status=failed` | Build a retry queue endpoint (TODO — Part 11). For now: user can delete + reschedule. |
| Network from n8n → LinkedIn | n8n workflow errors | n8n has built-in retry; won't mark post `failed` until retries exhaust. |
| Network from n8n → our webhook | Callback never arrives → post stuck in `status=scheduled` | n8n's own retry; if all 3 fail we rely on the next 5-min poll re-pulling the same due post. Idempotency (Part 8). |
| n8n instance down | All queued posts stop publishing | Uptime monitoring (Part 10). Posts simply wait in DB with `status=scheduled`. |
| Our webhook down (Vercel outage) | n8n polls fail | Post stays queued in DB. When Vercel recovers, next n8n poll picks up. No data loss. |

---

## Part 8 — Idempotency (prevent duplicate posts)

**The risk:** n8n publishes, LinkedIn succeeds, but the callback fails
to reach us. On the next poll, the same post is still `status=scheduled`
and gets published again → duplicate on LinkedIn.

**Mitigation A — webhook side:**

`GET /api/broadcast/webhook` should set a short-lived "claim" on each
due post so it's not returned to a parallel poll. Implementation:

- Add a column `claimed_at timestamptz` + `claim_token uuid` to
  `broadcast_posts` (migration TODO).
- `GET` endpoint: within a transaction, SELECT due posts where
  `claimed_at IS NULL OR claimed_at < now() - interval '10 minutes'`,
  UPDATE claim fields to `now()` + new uuid. Return only the claimed
  rows.
- `POST` callback: verify claim_token matches before changing status.

**Mitigation B — n8n side:**

Use LinkedIn's idempotency hint: include an `X-RestLi-Method: CREATE`
header + a client-generated `X-Idempotency-Key: {{ $json.post_id }}`.
LinkedIn deduplicates if the key is reused within ~10 minutes.

**Mitigation C — belt-and-braces:**

Even with A + B, add a final check before the publish node: query our
webhook `GET /api/broadcast/posts/{id}` — if `status !== 'scheduled'`
(e.g. already `posted`), skip.

Initial rollout: start with A + C (safe), add B later.

---

## Part 9 — Rate limiting

**LinkedIn limits (free tier):**
- Per user: ~25 posts/day soft, 150/day hard. Exceeds → 429 + daily cap message.
- Per app: ~500 ugcPosts/day across all users. This is the real
  bottleneck once we cross ~30 daily-posting users.
- Per IP: ~100 req/min burst.

**Our throttles:**

1. `GET /api/broadcast/webhook` caps response at 20 posts per poll. At
   5-min cron = 240 posts/hour theoretical ceiling.
2. When we approach LinkedIn app-wide limit, add a per-user daily cap
   in our webhook: exclude a user whose
   `COUNT(broadcast_posts WHERE status='posted' AND posted_at > today_start)` ≥ 3.
3. At ~500 users actively scheduling: apply for LinkedIn Partner Program
   to lift app-wide ceiling. Plan horizon: mid-2026.

---

## Part 10 — Monitoring + observability

**Our side (already partially exists):**

- Every webhook call logs to Sentry (add if missing).
- `broadcast_posts.status + failed_reason` is the source of truth for
  delivery health.
- Admin dashboard (TODO — Part 12) shows:
  - Posts queued (status='scheduled')
  - Posts posted today
  - Failures in last 24 h with reasons
  - Users with expired/revoked tokens (needing re-connect nudges)

**n8n side:**

- Workflow execution log — every poll + publish. n8n shows this in its
  Executions tab.
- Failed execution alerts → email/Slack via n8n's alert nodes.
- Uptime monitoring on `naten.linkright.in` → use UptimeRobot free tier,
  ping `/healthz`, alert if down > 5 min.

**Log retention:**

n8n self-hosted keeps ~7 days by default. Enough for debugging;
long-term delivery audit lives in our DB (`broadcast_posts` never gets
deleted).

---

## Part 11 — TODOs to complete multi-user production setup

Ranked by priority. Each is a small piece of work.

**P0 — required before public beta:**

1. **`BROADCAST_WEBHOOK_SECRET`** — generate, add to Vercel + n8n. 5 min.
2. **Import publish workflow** into n8n. 15 min.
3. **Test end-to-end** with your own LinkedIn (Part 14).

**P1 — required before 10 paying users:**

4. **Idempotency migration** — add `claimed_at` + `claim_token` columns
   to `broadcast_posts`; update webhook GET to claim + POST to verify.
5. **Disconnect endpoint** — `POST /api/broadcast/oauth/linkedin/disconnect`;
   wire the button in `/dashboard/profile`.
6. **Token refresh cron** — `/api/cron/refresh-linkedin-tokens`,
   register in `vercel.json`, run daily 3 AM IST.
7. **Import engagement workflow** — second n8n workflow + `/api/broadcast/engagement-queue` endpoint.

**P2 — before scaling to 100 users:**

8. **Admin dashboard** — `/admin/broadcast` with queue depth, failure
   rate, token expiry counts.
9. **Per-user daily cap** — refuse to mark >3 posts/day as due for one
   user so LinkedIn's per-user limit doesn't burn the app-wide pool.
10. **Retry queue** — for `status=failed` posts, a manual retry button
    in `/dashboard/broadcast/schedule` that resets `status=scheduled`
    with a fresh `scheduled_at=now()+15min`.

**P3 — scale:**

11. **Sentry instrumentation** across webhook, OAuth, broadcast.
12. **LinkedIn Partner Program application** — required at ~500 active users.

---

## Part 12 — Workflow version control

Each n8n workflow gets a JSON export stored in repo:

```
repo/
  n8n/
    workflows/
      broadcast-publish.json
      broadcast-engagement.json
    README.md          -- points at this file
```

Process:
1. Edit workflow in n8n UI → test → save
2. n8n → Settings → Download workflow as JSON
3. Commit to `repo/n8n/workflows/`
4. On workflow updates: import the new JSON into n8n (replaces old)

This way, the workflow definition lives in git alongside the code that
depends on it. PRs can review changes.

---

## Part 13 — Alternative: Vercel Cron (if n8n goes down often)

If naten.linkright.in is unreliable or you want to drop the external
dependency entirely:

1. Create `/api/cron/broadcast-publish` (server-side of the n8n
   workflow — pulls due posts, publishes via LinkedIn API, updates DB).
2. Register in `vercel.json`:
   ```json
   { "crons": [{ "path": "/api/cron/broadcast-publish", "schedule": "*/5 * * * *" }] }
   ```
3. Free Vercel plan limit: 2 crons. Pro plan: 100. You have some crons
   already; check `vercel.json` before adding.
4. Function timeout: 60s hobby / 300s pro. At 20 posts/poll = 3s each =
   60s worst case. OK on Pro, risky on hobby.

**Trade-off:** simpler ops (one codebase, one deploy), but Vercel
functions pay-per-invocation adds up past 100k/month. n8n self-hosted is
capex-zero once the Oracle VM is paid for.

**Recommendation:** stick with n8n. Fall back to Vercel Cron only if
naten.linkright.in suffers more than one outage per month.

---

## Part 14 — Testing + rollout

### Local smoke test (no n8n yet)

```bash
# 1. Generate + store webhook secret
openssl rand -hex 32                 # paste into Vercel BROADCAST_WEBHOOK_SECRET, redeploy

# 2. Connect your LinkedIn via the UI (/dashboard/broadcast/connect)

# 3. Seed a scheduled post (current user session required):
curl -X POST https://sync.linkright.in/api/broadcast/posts \
  -H "Cookie: <your sb-access-token cookie>" \
  -H "Content-Type: application/json" \
  -d '{"content":"Test post from backend","status":"scheduled","scheduled_at":"2020-01-01T00:00:00Z"}'

# 4. Pull due posts as if n8n:
curl https://sync.linkright.in/api/broadcast/webhook \
  -H "Authorization: Bearer $BROADCAST_WEBHOOK_SECRET"
# Expected: your post in due[], with linkedin: { access_token: ... }

# 5. Simulate publish success:
curl -X POST https://sync.linkright.in/api/broadcast/webhook \
  -H "Authorization: Bearer $BROADCAST_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"post_id":"<from step 4>","status":"posted","linkedin_post_id":"urn:test","posted_at":"2026-04-18T12:00:00Z"}'

# 6. Refresh /dashboard/broadcast/schedule → should be in Posted tab + bell
#    should show "Your post went live".
```

### n8n smoke test (after import)

1. In n8n, open the publish workflow → click "Execute Workflow" once
   (ad-hoc trigger).
2. Watch the execution log — each node should turn green.
3. Check `/dashboard/broadcast/schedule` in the LinkRight app — your
   test post should have moved to Posted tab.

### Production rollout

- Week 1: enable the publish workflow cron at 15 min cadence (slower
  = easier to debug). Monitor closely.
- Week 2: if healthy, tighten cron to 5 min.
- Week 3: enable engagement workflow at 12h cadence.
- Week 4+: tighten engagement to 6h, enable admin dashboard.

---

## Part 15 — Runbook (when things go wrong)

### Symptom: user says "I scheduled a post 30 min ago, still not posted"

1. Check n8n executions tab — is the workflow running? When did it last
   execute?
   - If last execution > 10 min ago → n8n cron/instance issue. Go to 2.
   - If last execution recent + successful → check the post.
2. In Supabase, `SELECT * FROM broadcast_posts WHERE id = '<id>'`.
   - `status='scheduled'` → why wasn't it due? Check `scheduled_at`.
   - `status='failed'` → check `failed_reason`.
   - `status='posted'` → it DID post; user may not have refreshed.
3. If `failed_reason='linkedin_not_connected'`:
   - `SELECT * FROM user_integrations WHERE user_id=...` — check status +
     expires_at.
   - Nudge the user to reconnect; once they do, manually flip the post
     `status='scheduled'` again.

### Symptom: n8n instance down

1. SSH to Oracle server → `docker ps` or `systemctl status n8n`.
2. Restart: `docker restart n8n` or `systemctl restart n8n`.
3. Check `https://naten.linkright.in/healthz` returns 200.
4. Verify the workflow is still enabled (n8n UI → Workflows → active
   toggle).

### Symptom: a large batch failed with the same reason

Almost always a LinkedIn outage or our app's rate limit. Check
https://status.linkedin.com. Posts are automatically retried on next
poll once LinkedIn recovers — no manual action needed unless posts are
older than their `scheduled_at + 2 hours` (users may want to reschedule
so they don't post at weird times).

### Symptom: app-wide rate limit hit

`failed_reason` contains "rate limit" across multiple users at once.
Mitigation:

1. Temporarily increase n8n cron to 30 min to slow the drain.
2. Check per-user counts in `broadcast_posts` last 24h; if one user is
   hammering (>10 posts/day), throttle them in the webhook GET
   response.
3. Long-term: apply for LinkedIn Partner Program.

---

## Part 16 — Summary — "how does n8n scale when new users join"

**TL;DR:** You don't scale n8n. It already scales.

| Users | What changes in n8n? |
|---|---|
| 1 → 10 | Nothing. Same workflow, same cron. |
| 10 → 100 | Nothing on n8n. Add idempotency + disconnect endpoint (P1 above). |
| 100 → 500 | Maybe bump the cron to 3 min. Add per-user daily cap. Apply for LinkedIn Partner Program. |
| 500+ | Partner Program approved → app-wide limit lifts. n8n still one workflow, one instance. |

The **only** per-user step is: user clicks "Connect LinkedIn". Our
OAuth flow stores the token. n8n automatically sees them on the next
poll. No workflow creation, no config change, no redeploy.

This is by design.
