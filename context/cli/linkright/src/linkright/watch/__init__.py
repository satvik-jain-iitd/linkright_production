"""Sprint D — CLI-native passive job-page capture via Chrome DevTools Protocol.

`linkright watch` attaches to a running Chrome (started with
`--remote-debugging-port=9222`), listens for navigations to job-listing pages,
extracts job data via JSON-LD + DOM, and POSTs to the LinkRight worker's
`/api/captures` endpoint.

Mental model: zero browser extension, zero Tampermonkey, zero email/WhatsApp.
The CLI is the only tool. Chrome is the user's normal browser, unchanged.

Public surface:
- `linkright watch`                — start the listener (foreground)
- `linkright watch setup`          — write shell alias + detect Chrome
- `linkright watch --install-service` — install launchd/systemd background daemon

All captures land in the SAME Oracle PG `job_discoveries` table as Sprint C
Phase 1 (Tampermonkey path) — backend is untouched, this is purely a new
input channel.
"""
