# DOC 20 — Browser Automation & Extension Architecture

## 1. Purpose

This document defines the browser extension architecture, JD capture pipeline, opportunity overlay system, autofill assistance model, extension-to-runtime communication protocol, and privacy boundaries for Linkright's browser layer.

It specifies:

- extension philosophy
- JD capture pipeline
- opportunity overlay system
- autofill assistance model
- LinkedIn intelligence surface
- Ask-AI panel
- privacy boundaries
- extension-to-runtime protocol
- deferred capabilities
- non-goals

This document defines the canonical browser automation and extension architecture reference for Linkright.

---

## 2. Extension Philosophy

The browser extension is a copilot, not an autopilot.

The extension's role is:

```text
Sensor layer.
Render layer.
Not reasoning layer.
```

Core intelligence — retrieval, scoring, generation, validation — lives in the runtime (DOC 08). The extension captures context and surfaces runtime output. It does not contain its own intelligence. It does not make decisions independently.

This separation is non-negotiable. Duplicating reasoning logic in the extension creates fragmented behavior, harder debugging, and trust degradation when the extension and runtime produce conflicting outputs.

The extension should:
- detect relevant page context
- send structured signals to the runtime
- surface runtime responses in context
- request explicit user confirmation before any action

The extension should not:
- run independent LLM calls
- make autonomous decisions about opportunities
- modify page content without user confirmation
- operate in background tabs the user is not actively viewing

---

## 3. JD Capture Pipeline

When the user visits a job posting, the extension activates a structured capture flow.

```text
User visits job posting
→ Extension detects JD content (title, company, requirements, nice-to-haves)
→ Presents structured preview to user
→ User confirms capture
→ Extension sends structured payload to runtime
→ Runtime creates opportunity in lifecycle
→ Runtime returns initial fit signal
→ Extension surfaces: "Opportunity added — 78% estimated fit"
```

Extraction fields:
- job title
- company name
- seniority signals
- hard requirements
- nice-to-haves
- location / remote status
- compensation if stated
- application deadline if stated

The capture preview is always shown before data is sent to the runtime. The user sees what was extracted and can correct it before confirmation. Silent mass-capture is deferred to Phase 2 and requires explicit activation.

---

## 4. Opportunity Overlay

On job listing pages where an opportunity exists in the pipeline, the extension surfaces a lightweight overlay.

Overlay contents:

```text
You are a 78% match

  Signal gaps (top 3):
  · "Platform PM" — not evidenced in current resume
  · "API product experience" — partial match
  · "Stakeholder alignment" — present, could be stronger

  [Add to pipeline]   [View full analysis]
```

Design rules:
- Overlay is non-blocking. It does not cover the job description.
- "Add to pipeline" is one click. It triggers the capture flow described in section 3.
- "View full analysis" opens a side panel with the runtime's full fit breakdown.
- No auto-apply. No auto-queue. Every pipeline action requires user initiation.

The overlay should appear only when:
- the page is a recognized job listing
- the extension detects a matching opportunity in the user's pipeline, or
- the user explicitly triggers capture mode

---

## 5. Autofill Assistance

On application forms, the extension provides field-level suggestions backed by the user's profile.

Behavior:

```text
Field detected: "Years of product management experience"
  Suggested value: 4
  Source: Profile (AmEx 2019–2022 + Sprinklr 2022–present)

  [Insert]   [Edit]   [Skip]
```

Rules:
- Each field suggestion is presented individually. No bulk-fill.
- User confirms each field before insertion. The extension never writes to a field without explicit confirmation.
- Source is always shown so the user knows where the value comes from.
- The extension never auto-submits forms. Submit is always a user action.

Field types the extension may assist with:
- name, email, phone
- years of experience (role-specific or total)
- cover letter text (retrieved from runtime)
- short-answer competency questions (runtime-generated, user-confirmed)
- location / work authorization

---

## 6. LinkedIn Intelligence

On LinkedIn profiles of potential connections or target-company employees, the extension surfaces a lightweight intelligence card.

Example:

```text
Priya Mehta — PM Lead, Stripe

  This person is at a company in your active pipeline.
  Add to relationship graph?

  [Add contact]   [Dismiss]
```

On LinkedIn job postings, full opportunity overlay behavior applies (section 4).

The extension avoids:
- scraping profile data without user-triggered action
- building shadow profiles of connections
- analyzing connections the user is not actively viewing

---

## 7. Ask-AI Panel

A floating Ask-AI panel is available on any page via keyboard shortcut or extension icon.

```text
┌────────────────────────────────────────────┐
│  Ask Linkright                             │
│                                            │
│  Is this company a good fit for my         │
│  archetype?                                │
│                                            │
│  [Send]                                    │
└────────────────────────────────────────────┘
```

The panel uses:
- current page context (company name, role title if detectable)
- the user's canonical profile and archetype from the runtime
- the user's active opportunity pipeline

The panel does not:
- store conversation history beyond the current session
- run inference locally
- answer questions without profile context

All reasoning happens in the runtime. The panel is a lightweight query interface over the runtime's retrieval and intelligence stack.

---

## 8. Privacy Boundaries

The extension reads page content only when the user triggers an action. There is no passive background monitoring.

Rules:

- **No background tab surveillance.** The extension does not read content from tabs the user is not actively interacting with.
- **No passive monitoring.** The extension does not continuously scan the user's browsing activity.
- **User-triggered reads only.** JD capture, overlay rendering, and Ask-AI panel queries are all initiated by explicit user actions or extension activation.
- **Local runtime only.** JD content, page context, and profile data are sent only to the local runtime via localhost. No content is routed to third-party servers as part of the extension-to-runtime channel.
- **Minimal permissions.** The extension requests only the permissions required for active-tab reading and localhost communication.

---

## 9. Extension-to-Runtime Protocol

The extension communicates with the runtime over a local HTTP channel.

```text
Extension → localhost:{port} → Linkright runtime
```

Protocol rules:

- **Local only.** All extension-to-runtime communication stays on localhost. No cloud routing.
- **Structured requests.** The extension sends typed, structured payloads. It does not send raw DOM strings.
- **Structured responses.** The runtime returns typed, structured responses. The extension renders them; it does not interpret them.
- **Authentication.** The local channel uses a session token to prevent cross-origin injection.
- **Timeout handling.** If the runtime is not running, the extension surfaces a clear state: "Linkright runtime not running — start with: linkright serve"

Request types:
- `jd.capture` — send extracted JD fields for opportunity creation
- `opportunity.score` — request fit score for a detected JD
- `profile.query` — ask a question against the profile and pipeline
- `autofill.suggest` — request a suggested value for a given form field

---

## 10. Deferred Capabilities

The following are explicitly deferred to Phase 2:

- **Gmail integration** — recruiter threading, response drafting, opportunity linkage. Deferred due to permission sensitivity and trust burden.
- **Calendar intelligence** — interview scheduling awareness, prep reminders. Deferred to Phase 2.
- **Ambient job monitoring** — passive background capture of job postings during normal browsing. Requires explicit Phase 2 activation model.
- **Multi-tab workflow coordination** — tracking state across multiple open job listings simultaneously.
- **Passive capture mode** — user activates a session where all visited JD pages are automatically queued. Phase 2 only.

These are not rejected. They are sequenced. Phase 1 must establish the active-copilot model and earn user trust before ambient modes are introduced.

---

## 11. Non-Goals

This document explicitly does not design for:

- **Form auto-submission.** The extension never submits applications. Submit is always a user action.
- **Mass-apply workflows.** The extension is not an application bot. Opportunity-by-opportunity intentionality is a design principle, not a limitation.
- **Passive surveillance.** The extension does not monitor browsing behavior in the background.
- **Independent reasoning.** The extension does not run its own LLM calls or scoring logic. All intelligence routes through the runtime.
- **Platform-coupled brittle scraping.** The extension avoids tight DOM assumptions that break on layout updates.

---

## 12. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 09 — Browser Extension & Ambient Intelligence Layer
- DOC 19 — UX Patterns & Interaction Design

This document influences:
- DOC 10 — n8n Orchestration & Automation Architecture
- DOC 11 — Observability, Logging & Explainability Framework

This document should be treated as the canonical browser automation and extension architecture reference for Linkright.
