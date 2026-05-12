# Wave 8 — LinkRight Browser Extension (Architecture Spec)

**Reference:** Wireframe Opt v3 "Memory-OS" + JobRight Autofill public research (2026-04-18).

---

## JobRight — what we're copying (and what we're doing differently)

**Chrome Web Store listing:**
- Name: *Jobright Autofill – Instant Job Applications, Job Match, AI Tailor Resume*
- 200,000 users · 4.4★ · 4.7 MB · Manifest V3 · in-app purchases (freemium)
- Data declared: PII, user activity, website content
- Privacy: not sold, not for creditworthiness, not used outside core functionality

**Their 4 pillar features:**
1. **One-click autofill** — fills ATS forms, "apply 10× faster"
2. **Resume matching** — highlights missing keywords, ATS score
3. **AI resume builder** — tailored per job
4. **Smart job match + tracker** — AI-curated suggestions, application tracking

**Their positioning line:** *"Skip the hunt — land more interviews. Jobright Agent streamlines your entire job search — proactively matching roles, customizing your resume, and applying for you."*

**Direct competitors (from Chrome Web Store "Related"):**
- **Teal** (4.9★) — save jobs, contacts, companies, resumes
- **Simplify Copilot** (4.9★) — autofill + tracker + AI resumes
- **Jobalytics** (4.3★) — keyword analyzer

### LinkRight's differentiator

JobRight is **autofill-first** — fast applications. LinkRight is **memory-first** — the artefact you send improves over time because the memory layer learns from your outcomes. We copy the extension UX shell and autofill mechanic; we differentiate by showing the **memory layer score** ("this resume pulls from 14 of your 33 memory atoms") and the **Oracle interview feedback loop** (a failed answer becomes tomorrow's drill).

---

## Extension architecture (Manifest V3)

### File layout

```
repo/extension/
├── manifest.json                 // v3, minimum permissions
├── background/
│   └── service-worker.ts          // message router, JWT storage, keep-alive
├── content/
│   ├── content.ts                 // entry; detects job context; injects overlay
│   ├── overlay.tsx                // floating card (React mounted in Shadow DOM)
│   ├── autofill.ts                // field detection + mapping
│   └── detectors/
│       ├── linkedin.ts            // https://www.linkedin.com/jobs/view/*
│       ├── greenhouse.ts          // *.greenhouse.io, boards.greenhouse.io
│       ├── lever.ts               // jobs.lever.co/*
│       ├── ashby.ts               // *.ashbyhq.com
│       ├── workable.ts            // *.workable.com
│       └── workday.ts             // *.myworkdayjobs.com
├── popup/
│   ├── popup.html
│   └── popup.tsx                  // browser action popup
├── options/
│   ├── options.html
│   └── options.tsx                // settings / connect account
├── lib/
│   ├── api.ts                     // fetch wrappers to /api/extension/*
│   ├── storage.ts                 // chrome.storage.local JWT + prefs
│   └── messaging.ts               // typed bg ↔ content messages
├── assets/                        // icons (16/32/48/128)
└── build/                         // bundled output (Chrome + Firefox)
```

### Minimum permissions manifest

```json
{
  "manifest_version": 3,
  "name": "LinkRight — Apply with Memory",
  "version": "0.1.0",
  "description": "Tailored resume, cover letter, LinkedIn DM, recruiter email — all from your memory layer. One click on any job page.",
  "action": { "default_popup": "popup/popup.html" },
  "background": { "service_worker": "background/service-worker.js" },
  "permissions": ["activeTab", "storage", "scripting"],
  "host_permissions": [
    "https://sync.linkright.in/*",
    "https://*.linkedin.com/jobs/*",
    "https://boards.greenhouse.io/*",
    "https://*.greenhouse.io/*",
    "https://jobs.lever.co/*",
    "https://*.ashbyhq.com/*",
    "https://*.workable.com/*",
    "https://*.myworkdayjobs.com/*"
  ],
  "content_scripts": [
    {
      "matches": [
        "https://www.linkedin.com/jobs/view/*",
        "https://boards.greenhouse.io/*/jobs/*",
        "https://*.greenhouse.io/*/jobs/*",
        "https://jobs.lever.co/*/*",
        "https://*.ashbyhq.com/*",
        "https://*.workable.com/*/jobs/*",
        "https://*.myworkdayjobs.com/*"
      ],
      "js": ["content/content.js"],
      "run_at": "document_idle"
    }
  ],
  "icons": { "16": "assets/icon-16.png", "48": "assets/icon-48.png", "128": "assets/icon-128.png" }
}
```

**Privacy:** exactly mirrors JobRight's declared data handling (PII for profile fill, user activity for tracking applications, website content for JD extraction). Not sold. Not transferred.

### Auth flow (Connect Account)

1. User installs extension → popup shows "Connect to LinkRight" button.
2. Click opens `https://sync.linkright.in/extension/connect?return=chrome-extension://<id>/callback`.
3. If logged-in session exists, user approves → server issues a **30-day extension JWT** (separate from the main session cookie; extension-scoped claims).
4. Server redirects back with `?token=<jwt>&user=<email>`.
5. Extension stores JWT in `chrome.storage.local`. No password ever enters the extension.
6. Rotate via popup "Re-authenticate" button.

### Job-page detection (content script)

```
URL match → run detector → extract {company, title, jd_text, job_id}
          → POST /api/extension/parse-job (caches JD server-side)
          → inject overlay (bottom-right floating button, design-system teal)
```

Detector stub per ATS:
```ts
// detectors/greenhouse.ts
export const detectGreenhouse = (): JobContext | null => {
  const title = document.querySelector('.app-title')?.textContent;
  const company = document.querySelector('.company-name')?.textContent;
  const jd = document.querySelector('#content')?.innerText;
  if (!title || !company || !jd) return null;
  return { source: 'greenhouse', title, company, jd, url: location.href };
};
```

### Overlay UX (on every job page)

```
┌──────────────────────────────────────┐
│ LinkRight · Apply with memory        │  ← teal brand strip
│ ─────────────────────────────────    │
│ 🎯 Match 72% · 3 gaps flagged        │  ← match score (not fake 100%)
│                                      │
│ Draws from 14 of your 33 memory atoms│  ← transparency vs JobRight
│                                      │
│ [⚡ Generate apply-pack]              │  ← primary CTA (coral pill)
│                                      │
│ 👥 2 friends of yours at Credo AI    │  ← peer signal (if available)
│   Request warm intro →               │
└──────────────────────────────────────┘
```

### Autofill (click after apply-pack generated)

Maps user profile fields + generated resume bullets to form inputs:
- Name, email, phone, LinkedIn → profile
- Resume upload → generated PDF
- Free-text "Why this role?" → auto-fills from generated cover letter first para
- "Current employer" / "Years of experience" → structured from nuggets

Field detection: progressive heuristics (label text, `name` attr, `placeholder`, ARIA labels), not hardcoded per site. Confidence score per field; low-confidence = highlighted for user to confirm, not auto-filled.

---

## Backend API to add (`repo/website/src/app/api/extension/*`)

| Endpoint | Purpose |
|---|---|
| `POST /api/extension/connect` | issue 30-day JWT after user-consent page |
| `GET /api/extension/me` | return profile summary (name, email, streak, memory-atom count) |
| `POST /api/extension/parse-job` | accept content-script job payload; upsert to `job_scans` |
| `POST /api/extension/apply-pack?job_id=...` | trigger existing resume pipeline + cover + DM + email; return asset URLs |
| `GET /api/extension/insiders?company=...` | peer graph lookup (Wave 8 sub-feature — stub first) |
| `GET /api/extension/profile-map` | return flat field-map for autofill (name/email/phone/linkedin/skills/education) |

All routes gated by `Authorization: Bearer <extension-jwt>`. Rate limit: 100 req/min/user.

---

## Build + ship sequence (3 weeks)

### Week 1 — Scaffold + Connect flow
- `npm create vite@latest extension -- --template react-ts` inside `repo/extension/`
- Add CRXJS Vite plugin for Manifest V3 bundling.
- Write `manifest.json` + service worker + popup + connect page `/extension/connect` on Next.js side.
- API: `POST /api/extension/connect` + `GET /api/extension/me`.
- Load unpacked in Chrome, verify connect + popup works.

### Week 2 — Content overlay + apply-pack
- Implement detectors/greenhouse + linkedin + lever (3 covers most ATS).
- Overlay React component (mount in Shadow DOM to isolate styles).
- API: `POST /api/extension/parse-job`, `POST /api/extension/apply-pack`.
- Apply-pack reuses existing `/api/resume/start` worker pipeline — no new LLM work.

### Week 3 — Autofill + Chrome Web Store submit
- Autofill heuristics + per-site field-map cache.
- API: `GET /api/extension/profile-map`.
- Chrome Web Store developer account ($5 one-time), screenshots, privacy policy link, submit.
- Review typically takes 3-7 days.

**Firefox add-on:** same manifest works; submit to addons.mozilla.org in parallel (faster review, 1-2 days).

---

## What Satvik owns (external actions)

1. **Chrome Web Store developer account** — $5 one-time payment. Use `klickbae8yt@gmail.com`.
2. **Firefox add-ons account** — free.
3. **Privacy policy** — copy/adapt JobRight's structure: *"We only collect what's necessary to help you apply faster — and never sell your data. Everything is encrypted, secured, and fully under your control."* Publish at `https://sync.linkright.in/legal/extension-privacy`.
4. **Extension icon / logo asset** — from the design system (`LinkRight Design System.zip/assets/linkright-logo-*.png`). Render 16 / 48 / 128 px versions.
5. **(Optional research — if you want feature parity):** screen-record yourself using JobRight's extension on the Amazon careers page. Send me the video; I'll enumerate every micro-interaction and mirror them. I can't do this live myself without access to your Chrome + JobRight account.

---

## What I explicitly cannot do (and why)

- **Sign into JobRight with your Google credentials.** That's authenticating as you. Violates my "never take destructive/shared-state actions without explicit per-action authorization" rule. Separately: automated login against a third-party SaaS from a throwaway Chromium is likely against their ToS.
- **Control the JobRight extension already installed in your Chrome.** `agent-browser` runs its own Chromium with a clean profile. It cannot access extensions in your personal Chrome install.
- **Scrape JobRight's authenticated pages (dashboard, job-match views).** Requires login. Not worth the ToS/ethics risk.

**Public data only** (landing, AI Agent page, Chrome Web Store listing) is fine — that's what I used for this spec.

---

## UX patterns observed in JobRight extension (from Satvik's 6:20 screen recording)

### Four visible panel states (copy these state machine)

1. **Home / onboarding state** (on jobright.ai itself):
   - Floating panel top-right on every page.
   - Header: brand + close arrow.
   - "Quick-Start Checklist" card listing 2 setup steps (Account, Profile) each with [GO] button.
   - Primary CTA "Start Applying" — disabled until checklist is complete.

2. **Collapsed state** (on non-job pages like amazon.jobs home):
   - Small floating bird icon on right edge only. One X to dismiss.
   - Non-intrusive — doesn't grab attention when nothing to do.

3. **Active / job-detected state** (on amazon.jobs/en/jobs/<id>/…):
   - Full right sidebar expands.
   - "Analyzing New Job…" with animated dots for 5-10s.
   - Helper: *"Takes about 5-10 seconds, you can stay on this page or go to External Job to view the results later."* — sets expectation + offers escape.
   - Once analyzed: shows "+ Add This Job In One Click" + big "Autofill" CTA + credits counter + "Your Autofill Information" expandable + resume file preview ("Satvik-Jain-Resume").
   - "Completion: 0%" progress bar that fills as user fills the form.

4. **Autofill-not-supported state** (on unknown ATS like passport.amazon.jobs login page):
   - Header: "Autofill Not Supported" + "Submit Request" link.
   - Still offers "+ Add This Job In One Click" + "See your match score and tailor your resume".
   - Bottom link: "Find More Jobs on Jobright" — pull back to main product.
   - **Community loop:** submit-request crowdsources coverage for missing ATS.

### Autofill-active behavior (seen on Amazon application multi-step form)

- **Left sidebar of the application itself** shows every section with a green checkmark per completed section (not the extension — the actual Amazon form's own nav). Extension just triggers form fill + user watches checkmarks appear.
- **Extension's sidebar on the right** shows:
  - "Autofill" button + credits remaining + "Get Unlimited" link.
  - "Your Autofill Information" (expandable) + "Upload Resume" with current file.
  - **"N out of N required fields filled — 100%"** progress bar per page.
  - **List of required fields with ✓** as each is filled (transparency — user sees what got filled vs not).
  - "Continue To The Next Page" bottom CTA — once page is 100%, user clicks to advance; extension then fills next page.

### Insider connections — how it's surfaced (on JobRight dashboard job view)

Three column grid:
1. **Beyond Your Network** — 2nd/3rd-degree LinkedIn connections at the company. Each card: avatar + name + title + email-button + LinkedIn-button.
2. **From Your Previous Company** — people who overlapped at a past employer (trusted intros).
3. **From Your School** — alumni connections from user's education.
- Per card: "Find More Connections" CTA (explore more).
- Big reminder banner: *"Get 3x more responses when you reach out via email instead of LinkedIn."* — nudges toward higher-conversion channel.
- Separate "2 email credits available today" quota hint — monetization for outreach volume.

### Tagging + fit signals (in job detail)

- Tag chips across top: domain keywords (Artificial Intelligence, Logistics, E-Commerce, Retail, Delivery, Foundational AI).
- Green "H1B Sponsor Likely" pill — immigration-relevant signal for Indian / international users.
- Right rail "AI Tools" card stack:
  - Customize Your Resume — "Maximize your interview chances"
  - Build Cover Letter — "Make your application stand out"
  - Analyze How Well You Fit — "Understand your strength & weakness"
- Top-right "APPLY WITH AUTOFILL" primary CTA (green).

### Monetization surfaces observed

- **Top banner**: *"Your Special offer ends in 57m 11s. Last chance to unlock extra 53% off"* — **countdown urgency on the dashboard top strip** (always visible).
- **Credits counter** on extension ("4 Credits Left | Get Unlimited") — freemium throttle.
- **Email credits** separately ("2 email credits available today") — separate currency for outreach.
- **"Upgrade to Turbo: Get Hired Faster! 53% Off"** floating banner inside the extension itself.
- **"Upgrade to Turbo: Get Hired Faster"** pill top-right of dashboard — same CTA everywhere.

### LinkRight differences (what we explicitly do differently)

- **No countdown-urgency pressure tactics.** Feels slimy. Our pricing is steady at ₹499/mo Pro, no fake timers.
- **No separate "email credits."** LinkRight Pro = unlimited outreach; Free = 3 resumes/mo cap.
- **Match score NOT hidden behind signup wall.** Show 80% match with 3 real gaps upfront on the extension overlay. Gain trust by being honest.
- **Memory layer transparency:** extension shows *"this apply-pack draws from 14 of your 33 memory atoms"* — JobRight doesn't have this; it's our moat.

---

## Verification (end of Wave 8)

- Install extension locally → popup shows "Connect to LinkRight" → click → flow completes.
- Open `https://www.linkedin.com/jobs/view/<id>` → overlay appears bottom-right with match score.
- Click "Generate apply-pack" → wait 60-90s → all 5 artefacts visible.
- Click "Autofill" on the LinkedIn Easy Apply form → 70%+ of fields pre-populate (low-confidence ones flagged).
- Repeat on a Greenhouse job → same flow works.
- Chrome Web Store submission passes review.
- Firefox add-on approved.
