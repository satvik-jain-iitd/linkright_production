# LinkRight Naukri Capture — Install & First-Run

Sprint C Phase 1 userscript. Runs in your real Chrome/Firefox/Safari, captures Naukri job pages you actively browse, POSTs to LinkRight worker (`sync-resume-engine.onrender.com/api/captures`) which persists to Oracle PG.

**No automation, no scraping at scale, no headless cron.** Fires only when YOU open a job page in your real authenticated session. Same legal posture as a browser bookmark.

---

## One-time setup (~5 min)

### 1. Install Tampermonkey

| Browser | Link |
|---|---|
| Chrome | <https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo> |
| Firefox | <https://addons.mozilla.org/en-US/firefox/addon/tampermonkey/> |
| Safari | <https://apps.apple.com/app/tampermonkey/id1482490089> |
| Edge | <https://microsoftedge.microsoft.com/addons/detail/iikmkjmpaadaobahmlepeloendndfphd> |

### 2. Install the userscript

Open this URL in the browser where you installed Tampermonkey:

<https://raw.githubusercontent.com/satvik-jain-iitd/linkright_production/main/userscripts/naukri-capture.user.js>

Tampermonkey should auto-detect the `.user.js` extension and show an **Install** prompt. Click **Install**. (Tampermonkey will auto-update from this URL whenever a new version is pushed to main.)

### 3. Set your capture key

- Click the Tampermonkey icon in your browser toolbar
- Hover over the entry **"LinkRight Naukri Capture"**
- Click the menu item **"LinkRight: Set capture key"**
- Paste the value of `LINKRIGHT_CAPTURE_KEY` from `~/.linkright/.env`:
  ```bash
  grep '^LINKRIGHT_CAPTURE_KEY=' ~/.linkright/.env
  ```
- Click OK

### 4. Verify it works

- Visit any Naukri job page, e.g. `https://www.naukri.com/job-listings-...-12345`
- Open DevTools → Console (F12 or ⌥⌘I)
- (Optional) Enable verbose logging: Tampermonkey menu → **"LinkRight: Toggle debug logging"** → reload page
- You should see one of:
  - `[LinkRight] POST https://sync-resume-engine.onrender.com/api/captures …` (debug only)
  - `[LinkRight] OK { dedup_status: 'new', ... }` (debug only)
- Check Oracle PG — the row should be there:
  ```bash
  set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
  python3 -c "
  import asyncio, asyncpg, os
  async def main():
      pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
      async with pool.acquire() as conn:
          rows = await conn.fetch(\"SELECT title, company_name, captured_at FROM job_discoveries ORDER BY captured_at DESC LIMIT 5\")
          for r in rows: print(dict(r))
      await pool.close()
  asyncio.run(main())
  "
  ```

---

## Privacy

The userscript NEVER captures from these paths (server-side filter independently agrees):

- `/messages`, `/inbox`, `/notifications`, `/connections`
- `/profile`, `/myaccount`, `/m/profile`
- `/recruit` (Naukri recruiter dashboard)

It also never captures content with markers like:
`Inbox:`, `Your offer:`, `Your CTC:`, `Reply to recruiter`, `Personal message:`

If you ever land on one of those, the userscript bails before sending anything.

---

## Tampermonkey menu commands

Click the Tampermonkey icon → "LinkRight Naukri Capture" submenu:

| Command | Effect |
|---|---|
| **LinkRight: Set capture key** | Update the per-tenant secret |
| **LinkRight: Set endpoint URL (advanced)** | Override worker URL (default: `sync-resume-engine.onrender.com`) |
| **LinkRight: Toggle capture ON/OFF** | Pause without uninstalling |
| **LinkRight: Toggle debug logging** | Verbose console messages |
| **LinkRight: Toggle desktop notifications** | OS-level pop-up on each successful capture |

---

## How it captures

1. **JSON-LD primary** — Naukri job pages embed `application/ld+json` `JobPosting` schema. Userscript reads that first (most stable, structured fields).
2. **DOM fallback** — If JSON-LD missing, scrapes via CSS selectors targeting Naukri's 2026 layout. If Naukri refactors HTML, only the selectors need updating.
3. **2-second settle delay** — waits for SPA-style late renders (e.g. JD text loaded via XHR) before reading.
4. **SPA navigation detection** — Naukri uses pushState for between-job navigation; a MutationObserver detects URL changes and re-captures.

---

## Troubleshooting

| Symptom (in DevTools console) | Likely cause | Fix |
|---|---|---|
| Nothing logged at all | Userscript disabled, or @match URL didn't match | Tampermonkey menu → toggle ON; verify URL starts with `https://www.naukri.com/job-listings-` |
| `[LinkRight] No capture key set` | Forgot step 3 | Tampermonkey menu → "Set capture key" |
| `[LinkRight] capture HTTP 401` | Wrong key | Re-set capture key from `~/.linkright/.env` |
| `[LinkRight] capture HTTP 403` | Privacy filter blocked it (server-side) | Verify URL path; if you think it's wrong, file an issue |
| `[LinkRight] capture HTTP 429` | Rate limit (1 req/sec) | You're browsing faster than 1 page/sec — slow down |
| `[LinkRight] capture HTTP 500` | Worker crashed (rare) | Check Render logs |
| `[LinkRight] capture HTTP 503` | Worker doesn't have `LINKRIGHT_CAPTURE_KEY` set | Check Render env vars |
| `[LinkRight] network error` | Worker offline / DNS issue | `curl https://sync-resume-engine.onrender.com/health` |
| `Insufficient data (no title or company)` | DOM selectors stale (Naukri changed layout) | File an issue, or update the selector list inline |
| Capture shows `dedup_status: 'updated'` | This URL was captured before — refresh updates the row | Expected; not an error |

---

## Updating

Tampermonkey checks the @match URL daily and prompts to install new versions automatically. To force an update:

- Tampermonkey dashboard → Installed Userscripts → LinkRight Naukri Capture → ⋮ → "Check for updates"

---

## Uninstalling

- Tampermonkey dashboard → Installed Userscripts → LinkRight Naukri Capture → trash icon

This stops captures immediately. Existing rows in Oracle PG are not removed (you can manually `DELETE FROM job_discoveries WHERE source_type = 'capture_naukri'` if you want a clean slate).
