# LinkRight Browser Extension — v0.1 (scaffold)

Plain-JS Manifest V3 extension. No build step needed — load unpacked in Chrome during development.

## What's here (v0.1)

| File | Purpose |
|---|---|
| `manifest.json` | Manifest V3, minimum permissions, host_permissions for 7 ATS + LinkRight backend |
| `background/service-worker.js` | JWT storage (30-day TTL), message router, API proxy |
| `content/content.js` | Detects job page on LinkedIn / Greenhouse / Lever / Ashby / Workable / Workday / Amazon Jobs; injects overlay (Shadow DOM for style isolation) |
| `content/overlay.css` | Stub (overlay styles live inside Shadow DOM inside content.js) |
| `popup/popup.html` + `popup.js` | Browser-action popup — Connect / status / shortcuts to dashboard |
| `popup/connected.html` | Post-OAuth landing that forwards `?token=` to the service worker, then auto-closes |

## Overlay states (state machine in `content.js:renderBody`)

1. `not-connected` — shows Connect CTA, opens `/extension/connect` on the LinkRight domain.
2. `analyzing` — "Analyzing <company>…" spinner + 5-10s ETA, mirrors JobRight's behaviour.
3. `ready` — match score, gap count, memory-atoms-used, "⚡ Generate apply-pack" CTA + insider connections if any.
4. `generating` — building apply-pack (5 artefacts), ~60s.
5. `apply-pack-ready` — opens in LinkRight + (TBD) autofill button.
6. `error` — human-readable message.

## Backend API the extension expects (implement next)

All under `repo/website/src/app/api/extension/*`. Auth via `Authorization: Bearer <30-day-JWT>`.

| Endpoint | Purpose |
|---|---|
| `POST /api/extension/connect` | Issues a 30-day extension-scoped JWT after user-consent page at `/extension/connect` |
| `GET /api/extension/me` | Returns `{ name, email, atoms, streak }` — shown in popup |
| `POST /api/extension/parse-job` | Accepts `{ source, title, company, jd, url }` from content script. Returns `{ job_id, match_score, gaps[], atoms_used, atoms_total, insiders[] }` |
| `POST /api/extension/apply-pack?job_id=...` | Triggers existing resume pipeline + cover letter + DM + email + portfolio. Returns `{ resume_id, cover_letter_id, dm, recruiter_email }` |

Rate limit: 100 req/min/user per existing `lib/rate-limit.ts`.

## Load unpacked (dev)

```
1. chrome://extensions/
2. Toggle "Developer mode" (top-right)
3. "Load unpacked" → select repo/extension/
4. Extension icon appears in the toolbar.
5. Click icon → popup → "Connect account"
6. Opens sync.linkright.in/extension/connect → authorise → token flows back via
   popup/connected.html → chrome.storage.local
7. Visit a supported job page (LinkedIn, Amazon Jobs, etc) → overlay appears
```

## Icons — TODO

`assets/icon-16.png`, `assets/icon-48.png`, `assets/icon-128.png` need to be generated from the design-system logo (`specs/design-artifacts/D-Design-System/LinkRight Design System.zip/assets/linkright-logo-dark-clean.png`). Until they exist, Chrome will show a default puzzle-piece icon — extension still functional.

Quick generation (once ffmpeg / ImageMagick installed):
```
magick "linkright-logo-dark-clean.png" -resize 128x128 extension/assets/icon-128.png
magick "linkright-logo-dark-clean.png" -resize 48x48  extension/assets/icon-48.png
magick "linkright-logo-dark-clean.png" -resize 16x16  extension/assets/icon-16.png
```

## Roadmap (v0.2+)

- **v0.2** Autofill — form field detection + mapping per ATS. Progressive confidence scoring.
- **v0.3** Insider-connection warm intros — click flow → LinkedIn DM draft reusing apply-pack copy.
- **v0.4** Firefox port — same manifest works.
- **v0.5** Chrome Web Store submission.

## Design system

Overlay colors/spacing/pills align with `specs/design-artifacts/D-Design-System/LinkRight Design System.zip/colors_and_type.css`:
- Primary teal `#0FBEAF` (brand), coral `#FF5733` (CTAs), slate text `#1A202C`, border `#E2E8F0`.
- Pills: `rounded-full`. Card: `rounded-2xl` (16px). Shadow on coral CTA only.
- Inter font family.

All inline in `content.js` inside Shadow DOM so host-page CSS can't break us.
