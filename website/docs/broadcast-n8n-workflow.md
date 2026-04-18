# Broadcast → LinkedIn publishing via n8n

The LinkRight broadcast feature (drafts, schedules, tracks LinkedIn posts)
**intentionally does not publish directly**. All publishing goes through an
n8n workflow you run + own. This doc tells you how to wire it up.

Once wired:
- User clicks "Schedule" in `/dashboard/broadcast/compose`
- Post lands in `broadcast_posts` with `status=scheduled`, `scheduled_at=...`
- n8n cron (every 5 min) polls our webhook, pulls due posts
- n8n calls LinkedIn API using the user's stored OAuth token
- n8n posts back success/failure to our webhook
- User sees "Posted" chip + engagement in `/dashboard/broadcast/schedule`

---

## 1. Required env vars (Vercel)

Set in the Vercel project settings, then redeploy.

| Name | Value | Used by |
|---|---|---|
| `LINKEDIN_CLIENT_ID` | From your LinkedIn Developer app | `/api/broadcast/oauth/linkedin/start` |
| `LINKEDIN_CLIENT_SECRET` | From your LinkedIn Developer app | `/api/broadcast/oauth/linkedin/callback` |
| `LINKEDIN_REDIRECT_URI` | `https://sync.linkright.in/api/broadcast/oauth/linkedin/callback` | Both |
| `BROADCAST_WEBHOOK_SECRET` | Long random string — generate with `openssl rand -hex 32` | `/api/broadcast/webhook` (both GET + POST) |

LinkedIn app setup: https://www.linkedin.com/developers/apps → create
"LinkRight Broadcast" → Products tab → add "Sign In with LinkedIn using
OpenID Connect" + "Share on LinkedIn". Auth tab → add the redirect URI
exactly as set in Vercel.

Scopes requested by `/start`: `openid profile email w_member_social` —
the last one is what lets us post on the user's behalf.

## 2. n8n workflow

The workflow has two parts — **Poll** (every 5 min) and **Callback**
(fires after each post attempt). Both hit the same webhook route:

- `GET  https://sync.linkright.in/api/broadcast/webhook` — list due posts
- `POST https://sync.linkright.in/api/broadcast/webhook` — report outcome

### Node layout (import into n8n)

```
┌──────────────┐   ┌─────────────┐   ┌──────────────────┐
│ Cron / 5 min │──▶│ HTTP GET    │──▶│ Split by item    │
└──────────────┘   │ /webhook    │   │ (item per post)  │
                   └─────────────┘   └─────────┬────────┘
                                               │
                                               ▼
                                     ┌──────────────────┐
                                     │ IF linkedin.     │
                                     │ access_token set │
                                     └──┬────────────┬──┘
                                        │ yes        │ no
                                        ▼            ▼
                          ┌────────────────────┐   ┌────────────────────┐
                          │ HTTP POST to       │   │ HTTP POST callback │
                          │ LinkedIn /ugcPosts │   │ { status: failed,  │
                          │  (see below)       │   │  failed_reason:    │
                          └────────┬───────────┘   │  "not_connected" } │
                                   │               └────────────────────┘
                                   ▼
                          ┌────────────────────┐
                          │ HTTP POST callback │
                          │ (success/failure)  │
                          └────────────────────┘
```

### GET node (pull due posts)

- Method: `GET`
- URL: `https://sync.linkright.in/api/broadcast/webhook`
- Auth header: `Authorization: Bearer {{ $env.BROADCAST_WEBHOOK_SECRET }}`

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
    }
  ]
}
```

If `linkedin` is `null`, the user hasn't connected LinkedIn — POST callback
with `status: "failed", failed_reason: "linkedin_not_connected"`.

### LinkedIn POST node

- Method: `POST`
- URL: `https://api.linkedin.com/v2/ugcPosts`
- Auth header: `Authorization: Bearer {{ $json.linkedin.access_token }}`
- Also set: `X-Restli-Protocol-Version: 2.0.0`
- Body (JSON):

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

Success response includes an `id` header (`X-RestLi-Id`) — that's the
`linkedin_post_id`.

### Callback POST node (after LinkedIn POST)

- Method: `POST`
- URL: `https://sync.linkright.in/api/broadcast/webhook`
- Auth header: `Authorization: Bearer {{ $env.BROADCAST_WEBHOOK_SECRET }}`
- Body (JSON):

On success:
```json
{
  "post_id": "{{ $json.post_id }}",
  "status": "posted",
  "linkedin_post_id": "{{ $node['LinkedIn POST'].headers['x-restli-id'] }}",
  "posted_at": "{{ $now.toISO() }}"
}
```

On failure:
```json
{
  "post_id": "{{ $json.post_id }}",
  "status": "failed",
  "failed_reason": "{{ $node['LinkedIn POST'].json.message }}"
}
```

## 3. Engagement poll (optional, later)

Every 6h, for `status=posted` rows with `linkedin_post_id`:

- `GET https://api.linkedin.com/rest/socialActions/{linkedin_post_id}`
- Collect `likesSummary.totalLikes`, `commentsSummary.aggregatedTotalComments`
- POST back: `{ post_id, engagement_json: { likes, comments, shares: 0, impressions: 0 } }`

Impressions require LinkedIn Marketing API access — defer unless needed.

## 4. Testing

1. Seed a test post:
   ```bash
   curl -X POST https://sync.linkright.in/api/broadcast/posts \
     -H "Cookie: <your session cookie>" \
     -H "Content-Type: application/json" \
     -d '{"content":"Test","status":"scheduled","scheduled_at":"2026-04-18T00:00:00Z"}'
   ```
2. Hit the webhook manually:
   ```bash
   curl https://sync.linkright.in/api/broadcast/webhook \
     -H "Authorization: Bearer $BROADCAST_WEBHOOK_SECRET"
   ```
   Should return your seeded post in `due[]`.
3. Manually callback:
   ```bash
   curl -X POST https://sync.linkright.in/api/broadcast/webhook \
     -H "Authorization: Bearer $BROADCAST_WEBHOOK_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"post_id":"...","status":"posted","linkedin_post_id":"test-urn"}'
   ```
4. Refresh `/dashboard/broadcast/schedule` — post should be in the
   "Posted" tab, and the bell icon should show a "Your post went live"
   notification.

## 5. Rate limiting + failure handling

LinkedIn's API limits publishing to ~25 posts / user / day. The webhook
returns up to 20 due posts per poll; if your throughput exceeds this,
shorten the cron interval instead of raising the limit.

For transient failures (5xx, rate limit), n8n should retry with
exponential backoff up to 3 attempts. Only report `status: failed` after
final retry. Our webhook writes a `post_failed` notification so the user
knows.

## 6. Revoking connection

The user's "Disconnect LinkedIn" button (coming on profile page) should:

1. POST `DELETE https://api.linkedin.com/v2/userinfo` with the token —
   LinkedIn revokes.
2. Update `user_integrations.status = 'revoked'` in our DB.

Any queued posts for that user will then fail with
`failed_reason: "linkedin_not_connected"` until they reconnect.
