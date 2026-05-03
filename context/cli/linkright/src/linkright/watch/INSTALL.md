# `linkright watch` — Install & First Capture

Sprint D: passive job-page capture from your real Chrome via Chrome DevTools Protocol. **Zero browser extension. Zero Tampermonkey. Zero email. Zero WhatsApp.** The CLI is the only tool.

## What it does

While Chrome is running with `--remote-debugging-port=9222`, `linkright watch` listens for navigations to job-listing pages on supported portals and silently captures each job into your LinkRight database. You browse jobs normally; LinkRight remembers them.

**Supported portals**:

| Portal | Detected URL pattern |
|---|---|
| Naukri | `naukri.com/job-listings-*`, `naukri.com/jobs/*` |
| LinkedIn | `linkedin.com/jobs/view/<id>`, `linkedin.com/jobs/{collections,search}/?currentJobId=<id>` |
| Indeed | `indeed.com/viewjob?jk=<key>`, `indeed.com/m/viewjob` |
| Wellfound | `wellfound.com/jobs/<id>-<slug>` |
| Greenhouse boards | `boards.greenhouse.io/<tenant>/jobs/<id>`, `job-boards.greenhouse.io/...` |
| Lever boards | `jobs.lever.co/<tenant>/<uuid>` |
| Ashby boards | `jobs.ashbyhq.com/<tenant>/<uuid>` |

URLs outside these patterns are silently ignored — no extraction, no POST. Server-side `worker/app/captures/privacy.py` enforces the same allowlist as a defense-in-depth check; private paths (`/messaging/`, `/in/`, `/profile/`, `/inbox/`, `/account/` etc.) are blocked by URL-path regex even when the host is allowed.

## One-time setup (~60 sec)

```bash
# 1. Install LinkRight (if not already)
pip install --upgrade linkright

# 2. Set your capture key (one-time, into ~/.linkright/.env)
echo 'LINKRIGHT_CAPTURE_KEY=lrcap_xxxxxxxxxxx' >> ~/.linkright/.env
chmod 600 ~/.linkright/.env

# 3. Bootstrap the shell alias (auto-detects your Chrome + shell config)
linkright watch setup

# 4. Reload your shell config
source ~/.zshrc        # or ~/.bashrc / ~/.bash_profile / config.fish
```

After step 3 you'll see something like:
```
✓ found Chrome: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
✓ shell config: /Users/you/.zshrc
✓ added alias to /Users/you/.zshrc

Next steps:
  1. Reload your shell:    source /Users/you/.zshrc
  2. Quit Chrome completely (cmd-Q on Mac), then start it via the alias:
       chrome
  3. Verify Chrome is in CDP mode:    curl http://localhost:9222/json/version
  4. Start the listener:    linkright watch
```

## First-run

```bash
# Quit Chrome completely (cmd-Q on Mac)
# Then re-open it via the alias:
chrome

# In another terminal, verify everything is wired up:
linkright watch status
# Expected:
#   ✓ capture key:   set (len=49)
#   ✓ endpoint:      https://sync-resume-engine.onrender.com/api/captures
#   ✓ chrome CDP:    reachable at localhost:9222
#   ✓ worker health: ... → 200

# Start the listener in foreground:
linkright watch
# (Ctrl-C to stop)
```

Now browse any supported job page in your Chrome (see Supported Portals table above). You'll see lines like:

```
14:32:17 → naukri — https://www.naukri.com/job-listings-senior-product-manager-amazon-12345
14:32:19   ✓ Amazon — 201 dedup=new
```

## Run as a background daemon (optional)

```bash
linkright watch install-service
# Mac:   installs ~/Library/LaunchAgents/in.linkright.watch.plist + loads it
# Linux: installs ~/.config/systemd/user/linkright-watch.service + enables it

# Check it's running:
launchctl list | grep linkright             # Mac
systemctl --user status linkright-watch     # Linux

# Logs:
tail -f ~/.linkright/watch.log
tail -f ~/.linkright/watch.err.log

# To remove later:
linkright watch uninstall-service
```

## Privacy

All capture happens in **your own Chrome session, on your own laptop**. The CLI never reads:
- Cookies, passwords, or session tokens
- Tabs you're viewing on non-job sites
- Bookmarks, history, downloads, autofill

`linkright watch` only attaches to the Chrome DevTools localhost endpoint (which Chrome itself exposes when started with `--remote-debugging-port=9222`) and only fires on URLs that match a job-listing pattern. Server-side privacy filter additionally blocks `/messages`, `/inbox`, `/notifications`, `/profile`, `/myaccount`, `/recruit` paths and content with markers like `Inbox:`, `Your offer:`, `Reply to recruiter`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `chrome CDP not reachable` | Chrome isn't started with the flag | `chrome` (via the alias), THEN `linkright watch status` |
| `LINKRIGHT_CAPTURE_KEY not set` | Step 2 skipped | `echo 'LINKRIGHT_CAPTURE_KEY=...' >> ~/.linkright/.env` |
| `worker health unreachable` | Render free-plan cold start | Wait 30-60 sec, retry. First request wakes the dyno. |
| Captures fire but `dedup=updated` every time | Same job_url already captured | Expected — refresh updates the row. Browse a NEW job to see `dedup=new`. |
| `Insufficient data (no_title_or_company)` | DOM selectors stale (portal redesigned) | File an issue with the URL — selector cascade needs an update |
| `linkright watch status` shows ✓ everything but no captures | Chrome isn't actually in CDP mode | `curl http://localhost:9222/json/version` should return JSON. If 404 or ECONNREFUSED, restart Chrome via `chrome` (the alias) |
| Multiple Chrome instances confusion (corp + personal) | Each Chrome instance needs its own port | Use `linkright watch --port 9223` to attach to a second instance |

## Verify captures landed in Oracle PG

```bash
set -a && source ~/.linkright/.env.oracle && set +a && unset SUPABASE_URL SUPABASE_SERVICE_KEY
python3 -c "
import asyncio, asyncpg, os
async def main():
    pool = await asyncpg.create_pool(os.environ['ORACLE_PG_URL'], min_size=1, max_size=1)
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT title, company_name, source_type, captured_at FROM job_discoveries ORDER BY captured_at DESC LIMIT 10')
        for r in rows: print(dict(r))
    await pool.close()
asyncio.run(main())
"
```

## Limitations (Phase 1)

- **Chrome / Chromium-derivative browsers only** (Brave, Edge, Arc, Vivaldi work; Firefox + Safari don't — see Phase 2 roadmap).
- **No mobile browsing** (CLI doesn't run on iOS/Android).
- **Some corporate laptops block `--remote-debugging-port`** (Mobile Device Management policies). Watchlist scraper is the fallback path for those users.
- **DOM selectors target Naukri's 2026 layout** — other portals fall back to JSON-LD which is more stable. Per-portal selector tuning needed if Naukri redesigns.

## How it composes with the rest of LinkRight

```
linkright watch                         (Sprint D — this doc)
       ↓ POST
sync-resume-engine.onrender.com/api/captures    (Sprint C Phase 1 — already shipped)
       ↓ persist
Oracle PG: companies + job_discoveries  (Sprint B + C — already shipped)
       ↑ read
linkright jobsearch find                (Pillar 2 v1 — already shipped)
```

`linkright watch` is purely a NEW input channel — backend is unchanged from Sprint C Phase 1. The Tampermonkey userscript at `userscripts/naukri-capture.user.js` remains as a fallback/redundancy for power-users; Phase 2 will deprecate it once `linkright watch` is in production for a couple weeks.
