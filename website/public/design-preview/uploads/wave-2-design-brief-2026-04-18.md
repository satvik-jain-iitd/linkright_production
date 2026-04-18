# LinkRight — Full User Journey Brief for claude.ai/design

> **Purpose:** hand-off to claude.ai/design so it can design every screen of the product end-to-end, in the LinkRight design system, matching the product intent.
>
> **How to use:**
> 1. Open claude.ai/design, new project.
> 2. Attach this brief + the `LinkRight Design System.zip` bundle (from `specs/design-artifacts/D-Design-System/`).
> 3. Instruct claude.ai/design: *"Use the LinkRight Design System attached. Generate mockups for every numbered screen in this brief, in sequence. Think like a product designer solving for the user's intent — not a developer implementing spec. Create variations where useful."*
> 4. Iterate visually in claude.ai/design until the flow feels right.
> 5. Once approved, I implement screen-by-screen from the mockups.

---

## Part 1 — Who + what + why

**Product:** LinkRight is a career navigation OS for ambitious job-seekers in India (initial ICP: PM / SWE / DA, 3–8 years experience). It turns the job hunt from an anxiety-ridden one-person project into a daily 10-minute ritual with a memory-backed co-pilot.

**The five pillars:**
1. **Discover** — LinkRight builds a career memory layer from the user's resume, follow-up insights, diary entries, interview answers, and application outcomes. This is the user's living profile and the foundation for everything else. Users grow it voluntarily; the deeper the memory, the sharper the output.
2. **Find** — Scout scans every ATS (LinkedIn, Greenhouse, Lever, Ashby, Workable, Workday, Amazon.jobs) and ranks roles honestly against the memory. Top-20 curated, not feed-of-200. No 100%-match theatre.
3. **Outreach** — for every application: tailored resume + cover letter + LinkedIn DM + recruiter email + portfolio site. Five artefacts, one click.
4. **Prepare** — personalised interview drills (product sense, system design, case, SQL, behavioural). The memory knows what the user doesn't know.
5. **Broadcast** — the memory layer drafts authentic LinkedIn posts from the user's real daily wins, failures, learnings. Scheduled via n8n, posted through user's own LinkedIn OAuth.

**Discover is the foundation, not a hidden backend.** It starts the moment a user uploads a resume and is surfaced as a first-class pillar in the journey — users see their memory grow, add to it voluntarily, and watch the other four pillars get sharper because of it. Every downstream surface (Find, Outreach, Prepare, Broadcast) retrieves from Discover. The more the user uses LinkRight, the more Discover knows.

**The user's job-to-be-done:** land a better role faster, with less silent-despair doomscroll.

**What the product is NOT:**
- Not a resume tool. Resume is one artefact of five per application.
- Not a job board. Scout is a signal-filter — "top 20 today", not "feed of 200".
- Not a chatbot. LLMs are the engine, not the interface.

**Voice (every headline passes these tests):**
- Specific number or mechanic backing the promise.
- A real human-operator wrote it, not a corporate marketer.
- The "I" of the product is human. "We build your resume" beats "Our AI engine generates resumes."
- No "empowerment", "unleash", "revolutionize", "game-changer".
- Sentence case. Never ALL CAPS except eyebrow labels.

**Jargon rule (critical):** the internal terms in this brief — *Discover, Find, Outreach, Prepare, Broadcast, memory layer, atoms, nuggets, apply-pack, first-person interpretation, pillars* — are for **my/designer clarity only**. They must NEVER appear in user-facing UI copy. Use plain English the user already knows:

| Internal term | User-facing phrasing |
|---|---|
| Discover / memory layer | "your profile", "what LinkRight knows about you", "your career" |
| Atoms | "details", "highlights" |
| Nuggets | "highlights", "parts of your story", "what stood out" |
| Apply-pack / 5 artefacts | "your application kit" or just list them: *"resume, cover letter, LinkedIn message, recruiter email, portfolio"* |
| First-person interpretation | "how we read your resume", "your story in your words" |
| Embedding / embedding ready | "getting your profile ready", "almost ready" |
| Pillar / zone | never surface to user |
| Scout | OK to use as a section name; don't over-explain |

If a user-facing label would need a tooltip to explain it, rewrite the label instead.

---

## Part 2 — The journey, four macro phases

```
ENTER  →  BUILD  →  ACT  →  GROW (loops back)
```

- **Enter** — landing → signup → first upload. Zero friction, one clear ask.
- **Build** — resume upload is the ONLY required input. Memory starts from that. Deeper personalization is optional, voluntary, rewarded.
- **Act** — preferences → matching jobs → 5-artefact apply-pack → interview prep. This is where user sees value every day.
- **Grow** — diary entries, streak, outcomes, social broadcast. The flywheel: every action feeds memory, memory sharpens the next action.

**Non-negotiables:**
- First screen post-signup = resume upload. Not role selection, not preferences, not a chat. The fastest path from "I'm here" to "you understand me".
- Every screen's copy answers *"what do I do now, and why does it matter?"* in 5 seconds.
- Match scores are honest. If the user is a 62% fit, we show 62%, with the 3 real gaps.

---

## Part 3 — Screens (ordered by journey)

Each screen: user's goal, what shows up, what they do, what happens next. Copy direction only where it matters — let the design system handle the rest.

---

### 1. Landing (`/`)

**User's goal:** understand in 5 seconds whether this is worth signing up for.

**Must be visible:**
- One headline that names the real problem.
- One subhead that names the solution in a concrete, number-backed way.
- **One** primary CTA ("Start for Free").
- Three to five proof tiles — each names one thing LinkRight does, in plain English (e.g. *"A profile that remembers you"*, *"Everything you need for one application"*, *"Honest match scores"*, *"Posts drafted from your real wins"*). No internal terminology on the tiles.
- A tiny, honest "how it works" strip.
- Social proof (founder pedigree + one or two numbers that don't feel invented).

**Copy direction (not final wording — claude.ai/design should iterate):**
- Headline should sound like: *"Job hunting is broken. LinkRight fixes the five things that matter."* — but crisper.
- Subhead should hint at the idea of a profile that gets smarter about you — without using words like "memory layer" or "AI engine". Plain English. Something like *"A profile that learns what you're good at, so your applications get sharper every week."*
- Don't undersell. This is a career OS with five shipped pillars, not a resume generator.
- Don't oversell. Claims must be defensible (e.g. "no AI slop" is only true after Package B; don't promise what we haven't built — broadcast is "soon").

**User does:** clicks Start for Free → Screen 3.

**Out of this screen:** pricing (secondary link), features (anchor scroll), existing-user sign-in.

**States:** default, returning-user (banner above hero: *"Welcome back — go to your dashboard →"*).

**Principle:** density over length. If the message doesn't land above the fold, more words won't save it.

---

### 2. Pricing (`/pricing`)

**User's goal:** figure out if it fits their budget before they invest effort.

**Must be visible:** Free tier limits (3 resumes/month) · Pro tier (₹499/mo, unlimited, Oracle, brand colours, broadcast) · clear comparison of what's included in each · honest "coming soon" labels.

**User does:** picks a plan → signup (same as landing).

**Principle:** no dark patterns. No fake discount countdown. No "most popular" sticker on a plan we're pushing.

---

### 3. Signup / Signin (`/auth`)

**User's goal:** get into the product in under 15 seconds.

**Must be visible:** Google OAuth button (primary — most users will pick this) · email + password fallback · honest heading that reflects mode (`Create your account` vs `Welcome back`).

**After signup success:** go directly to Screen 4 — no interstitial celebrations, no tutorials, no "pick your theme".

**Principle:** if they wanted to fill a form, they'd be on LinkedIn.

---

### 4. Resume upload + outline + first-person narration (`/onboarding`) — **FIRST SCREEN POST-SIGNUP**

**User's goal:** give LinkRight just enough material to start being useful. This is the ONLY required input.

**Must be visible:**
- A clear, warm invitation to drop a resume. Formats: PDF, DOCX, TXT, or paste text. File upload is primary; paste is secondary.
- Helper copy explaining that this is the memory seed — every downstream feature retrieves from it.
- After parse completes, two pieces of content side-by-side (desktop web layout — see Part 10 for platform scope):
  - **The structured outline** — a visual reading of the resume. Companies → roles → projects (with one-liner + 2-3 key achievements each), plus education, skills, certifications. Every field inline-editable.
  - **The first-person interpretation** — a detailed, line-by-line first-person retelling of the entire resume. Every role expanded into its own first-person narration; every project described in the user's voice; every resume bullet rewritten as a first-person sentence (e.g. *"At Amex, I led a 12-person team redesigning the returns flow. The problem was … what I did was … the outcome was an 18% conversion lift."*). NOT a one-paragraph summary — a full, verbose, section-by-section narration that covers every line of the resume. Organised alongside the outline (one narration block per role/project for parallel reading). This IS the canonical seed for the memory layer — the richer and more accurate this becomes, the sharper every downstream pillar gets. Every block inline-editable; user can rewrite in their own voice or trim.
- A way to swap resumes if they uploaded the wrong one.

**User does:** uploads → reviews both views → edits anything that feels off → clicks one CTA that says "Save and continue" (or similar).

**What happens after:** backend parses into structured data + fires categorisation + embedding in the background. User advances immediately (doesn't wait for embedding).

**States:** empty (before upload) · parsing (5–15s, show what we're doing) · parsed (the two views above) · parse failed (offer paste-text retry).

**Principle:** show the user *our interpretation* before we lock it into a resume. Trust is earned by exposing our understanding early.

---

### 5. Your profile — highlight cards (`/onboarding/profile` or similar)

**User's goal:** see what LinkRight picked up from the resume, add more depth where it matters. Second screen post-signup — right after resume upload.

**Why this comes BEFORE preferences:** the user's profile is the product's foundation. Surfacing it early builds trust (*"they understood me"*) and lets the user invest while the initial setup finishes in the background.

**User-facing copy direction (plain English — no "memory layer", no "atoms", no "nuggets"):**
- Header: something like *"Here's what stood out from your resume. Add more where you want — the more we know, the better everything gets."*
- Progress / status strip: plain phrasing like *"Getting your profile ready — 12 of 33 highlights processed"*. NOT "embedding" or "atoms".
- Each card: a short extracted highlight from the resume + where it came from (*"from your Amazon role"*, *"from your projects section"*).
- Primary CTA: **"Continue to find jobs →"** — always enabled, never blocks.
- Secondary CTA: **"Skip — I can add more from my profile later"**.

**Must be visible:**
- Header + one-line context.
- Progress indicator for any background processing.
- A grid of highlight cards (~10–30 cards depending on resume depth).
- Cards open Screen 6 (follow-up modal) on click.
- The two CTAs above.
- A low-key secondary action somewhere on the page (not hero): *"Have everything written up already? Upload a career file →"* that opens the same bulk-upload flow from Screen 20 (template download + file upload). Don't push it; offer it.

**User does:** clicks 1–3 cards that catch their eye, answers quick follow-ups, continues. Or skips entirely.

**States:** still-processing (show progress, cards still interactable) · ready (stats settle, small quiet success signal) · skip (straight to Screen 7).

**Also accessible from:** dashboard any time after onboarding — returning users open this page to review, add, or edit highlights.

**Principle:** voluntary is the whole point. 1 of 20 answered is a win. Never block the funnel.

---

### 6. Highlight expand — 3 follow-ups (modal/drawer from Screen 5)

**User's goal:** add more context on one highlight — in under 60 seconds.

**User-facing copy direction (plain English):**
- The clicked highlight sits at the top, unchanged.
- Below: three follow-up questions, each a simple short question like *"What was the biggest challenge here?"*, *"What outcome are you most proud of?"*, *"Who else worked on this with you?"*. Tailored to the highlight.
- No "nugget", no "signal", no "atom" in the UI.

**Must be visible:**
- Parent highlight text at top.
- Three follow-up questions, visually connected (tree-style with connectors — NotebookLM feel).
- Each question has its own textarea. User answers any, all, or none.
- Per-question save — partial depth is saved.
- Close action: **"Done"** (returns to Screen 5).

**Global toast (appears anytime, non-intrusive):** *"Your profile is ready — your resume and matches will be sharper now."* when background processing finishes.

**Principle:** follow-ups are gifts, not assignments. 1 of 3 answered is a win.

---

### 7. Job preferences (`/onboarding/preferences`)

**User's goal:** tell LinkRight what kind of roles they actually want — once, quickly.

**Must be visible:** target roles (multi-select, with chips) · location preference (remote/hybrid/onsite/any) · cities · work authorisation · company stage · compensation range · notice period. Every field optional except at least one target role. An "I'll decide later" skip option.

**User does:** fills what they care about, clicks "Find roles".

**What happens after:** preferences save + Scout queries the job database with those filters. User goes to Screen 8.

**Principle:** filters here are the LAST place the user fiddles with them. On the next screen (results) they're locked.

---

### 8. Find roles — ranked matching jobs (`/onboarding/jobs` or `/dashboard/jobs`)

**User's goal:** see which jobs are actually worth their time today. Pick one to customise for.

**Must be visible:**
- A short "searching" state (3–8 seconds, programmatic DB query, no LLM).
- Results header: how many matches, when the list was last refreshed.
- **One spotlighted recommendation at the top** — the best-fit role, visually distinct. It carries the match score, the top 3 reasons why it's a fit, and the primary CTA: "Start custom application".
- A ranked list below — every other matching role, score visible, same CTA per row.
- No filter controls on this screen. If they want to change filters: one clear "← Back to preferences" link.
- Empty state: "Nothing matched right now" — with a helpful suggestion and a "Tune preferences" CTA.

**User does:** clicks "Start custom application" on one role (usually the spotlight).

**What happens next:**
- If the user's profile is fully processed → straight to Screen 9 (customisation layout).
- If the profile is still processing → gentle inline banner in plain English: *"We're still finishing your profile — adding a couple more details now will make your first draft sharper."* Two buttons: **"Add a few more details →"** (back to Screen 5) OR **"Go ahead anyway"** (forward to Screen 9, with a note that the first draft may be thinner). Never a full-screen block.

**Principle:** recommend ONE. A feed of 200 is noise. Top 20 in a list with a clear #1 is a decision.

---

### 9. Resume customisation — layout plan (`/resume/customize?job_id=…`)

**Entry context:** user clicks "Start custom application" with embedding ready; OR they chose "Continue anyway" from Screen 8's pending-memory branch; OR they returned from Discover (Screen 5) after adding insights and the memory is now ready. Either way, the job is already known — **no JD input step is needed.**

**User's goal:** decide the SHAPE of the resume before any writing begins. Think blueprint before construction.

**Must be visible:**
- The job context (company, role) as a quiet chip at top.
- A visual plan of the one-page resume — sections rendered as blocks in their eventual position, with rough size/width/bullet-count indicators. Treat it like an architect's plan view.
- User can: reorder sections (drag), resize (drag), toggle sections on/off.
- Clear signal if the plan exceeds one page — must fit A4.
- Sidebar or panel for section-level controls (bullet budget, show/hide).
- Single primary CTA: "Confirm layout → Start writing".

**User does:** tweaks the plan, confirms.

**Principle:** let users feel authorship over structure. Stops them from later blaming the AI for the shape.

---

### 10. Resume customisation — live bullet writing

**User's goal:** watch their resume take shape and trust the output.

**Must be visible:**
- The A4 resume preview, with bullets streaming in one at a time (the 120ms-stagger animation already exists in code).
- A status panel showing phases (Layout → Writing → Condensing → Width optimizing → Scoring → Validating), with the current phase highlighted.
- Progress bar + elapsed time.
- If a bullet is actively being written into a section: a subtle "writing…" indicator.
- If the pipeline fails: clear error card with a Retry CTA.

**User does:** waits. Usually 60–90s. Can also scroll around while it writes.

**Principle:** latency stops hurting the moment the user can see progress.

---

### 11. Resume customisation — review + next actions

**User's goal:** review the final resume, download it, and decide what to do next.

**Must be visible:**
- The final A4 resume, clickable bullets (click → inline edit).
- Primary actions: Download PDF, Download HTML, Host on GitHub Pages (already built).
- "Refine this bullet" chip row — appears when a bullet is focused. Options: Shorter · More metrics · Different verb · Custom instruction.
- "What's next" panel with clear links to the next moves:
  - **Find more roles →** (loops back to Screen 6 / Scout)
  - **Interview prep for this role →** (Screen 13)
  - **Cover letter · coming soon** (disabled, gold "Soon" label)
  - **Portfolio website · coming soon** (disabled, gold "Soon" label)

**User does:** downloads or hosts or jumps to next action.

**Principle:** the resume is the milestone, not the destination. Keep the next door open.

---

### 12. Dashboard — returning-user home (`/dashboard`)

**User's goal:** see what matters today in 5 seconds.

**Must be visible:**
- Top row: nav + notification bell + "+ Create resume" CTA + avatar menu.
- **Today's matches** — the 3–5 highest-ranking roles surfaced since last login. Compact cards, each with match score and "Start application" CTA.
- **Keep going** — 2–3 contextual nudges:
  - If there's a resume in progress → "Pick up where you left off"
  - If profile still processing → "Add a few more details while we finish setting up"
  - If it's been 48h since last login → "Here's what changed since you were away"
  - If streak is active → streak card (gold)
- **Your profile** — a prominent card showing how much LinkRight knows (e.g. *"47 highlights · 4 companies · 6 weeks of activity"*). Primary CTA *"Add more →"* routes to Screen 5. No "memory", no "atoms", no "Discover" in the UI label — just "Your profile". The card exists to make the user feel their profile is growing on every return visit.
- **Scout watchlist** — top 3–5 tracked companies with recent activity.

**User does:** clicks into whatever caught their eye. Starts their 10-minute ritual.

**Principle:** dashboards should reward the daily return. Show movement, not static stats.

---

### 13. Interview prep hub (`/dashboard/interview-prep`)

**User's goal:** pick an interview type to practice against a specific role.

**Must be visible:**
- Heading that hints at the product's bet: the memory knows what you don't know.
- Interview-type cards: Product sense · System design · Technical · Case · Behavioural · SQL · Growth · Telephonic screen. Each card = 1 line of what's inside + "Start practice" CTA.
- A "coming soon" tile for the multi-persona recruiter roundtable (Wave 6 advanced).

**User does:** picks a type, jumps into a session (session screen is Wave 6, brief it separately).

**Principle:** interview prep feels like a quiet studio, not a quiz. Sage-toned zone per the design system.

---

### 14. Applications tracker (`/dashboard/applications`)

**User's goal:** track where every application stands without a spreadsheet.

**Must be visible:**
- Kanban columns: Wishlist · Drafting · Applied · Interview · Offer · Rejected. Drag-to-move.
- Each card: company + role + date applied + last activity chip.
- Click a card → deep panel with timeline, last recruiter message, interview notes, linked resume version.
- Outcome feedback on rejection/interview: user can add one-line "what happened" — this feeds memory ("this angle didn't work", "recruiter loved the Walmart story").

**User does:** updates status as things move, logs outcomes.

**Principle:** outcomes are the rarest training signal. Capturing them is a premium feature disguised as hygiene.

---

### 15. Broadcast — connect LinkedIn (first-time onboarding to social flow)

**User's goal:** connect their LinkedIn so LinkRight can draft + eventually post on their behalf.

**Must be visible:**
- One clean explanation of what LinkRight will and won't do: *"We draft posts from your daily diary and wins. Nothing goes live without you clicking Send."*
- A single "Connect LinkedIn" primary CTA that opens LinkedIn OAuth flow (standard).
- A guided link explaining how OAuth works for skeptical users: *"Why does LinkRight need LinkedIn access?"* → expands into plain-English explanation.
- Trust notes: "Revoke any time in LinkedIn settings. We never auto-post unless you schedule it yourself."

**User does:** clicks Connect, completes OAuth in a popup, returns to Screen 16.

**Principle:** LinkedIn OAuth is a high-trust moment. Buy the trust with plain language, not legalese.

---

### 16. Broadcast — personal insights browser

**User's goal:** pick a past win / learning / observation to turn into a post.

**Must be visible:**
- A scrollable list of things from the user's own history that are worth a post — a shipped feature, a metric that moved, a failed experiment that taught something, a strong take from an interview answer.
- Each card shows: short text of the moment, source context (e.g. *"from your diary, 3 days ago"* or *"from your Amazon role"*), and a *"Write a post about this →"* CTA.
- Filter chips at top: Wins · Learnings · Takes · Failures · Shipped. (User-familiar categories; no internal terms.)
- Empty state if not enough material yet: *"Keep shipping. After 7 diary entries we'll start suggesting posts."*

**User does:** picks an insight, clicks "Draft a post".

**Principle:** posts come from the memory layer, not a prompt box. The user curates; the model drafts.

---

### 17. Broadcast — compose + edit

**User's goal:** read the drafted post, edit it until it sounds like them, schedule or save.

**Must be visible:**
- The generated post (~3–5 paragraphs, LinkedIn-appropriate length) in an editable textarea.
- The source insight panel on the side for reference (so user can verify truth).
- Tone/length toggles: Shorter · Punchier · More personal · Add a question at the end (user-friendly, not prompt-engineering).
- Regenerate button (limited — 3 regens per insight, to avoid generation-as-entertainment).
- Preview mode: toggle to see the exact LinkedIn rendering (avatar, name, timestamp placeholder).
- Primary actions: "Schedule post →" OR "Save as draft" OR "Add to tracker".

**User does:** tweaks the text, toggles tone, picks schedule time, confirms.

**What happens behind the scenes (not shown to user):** once scheduled, the post row goes to a queue that n8n picks up on its schedule and posts to LinkedIn via the stored OAuth token.

**Principle:** the user's voice is the product. The model is a draft-bot, not a ghostwriter.

---

### 18. Broadcast — schedule + tracker

**User's goal:** see what's scheduled, what went out, what performed.

**Must be visible:**
- Calendar/list view of scheduled posts — date, time, preview text.
- Posts already sent — date, views, reactions, comments (pulled from LinkedIn API if available).
- Drafts — unfinished drafts saved from Screen 17.
- Simple analytics: "Your posts averaged X reactions in the last 7 days".
- Per-post menu: Edit · Reschedule · Delete · Duplicate.

**User does:** manages queue, revises upcoming posts, sees what's working.

**Principle:** this is where the flywheel becomes visible — the user sees their own voice, scheduled, shipping, receiving reactions. The dopamine hits here fund the rest of the product.

---

### 19. Daily diary (persistent CTA across dashboard; lightweight modal)

**User's goal:** take 60 seconds to log what happened today. Feeds the memory for broadcast, interview prep, and future resume bullets.

**Must be visible:**
- Quick-log widget accessible from anywhere (nav, dashboard hero, or floating button).
- Two input modes: type a quick text OR record a 60-second voice note (Whisper transcribes).
- Prompt hints to lower the blank-page tax: "What did you ship? What did you learn? What pissed you off?"
- After save: subtle confirmation, a small counter tick in plain English (e.g. *"+1 added to your profile"*), streak updates.

**User does:** 60 seconds of writing/talking, saves, moves on.

**Principle:** daily capture is the single highest-leverage habit. Friction must be ≤ 60 seconds or it won't happen.

---

### 20. Profile + account (`/dashboard/profile`)

**User's goal:** manage the account, see what LinkRight knows, and optionally bulk-upload a career JSON file using the provided template.

**Must be visible:**
- Account: email, name, sign out.
- Profile stats — plain phrasing: *"47 highlights · 4 companies · 6 weeks of activity"*. No internal jargon.
- **Bulk upload career file** — a clearly labelled card: *"Already have your career written up? Upload a JSON file."* Two actions: **"Download template"** (gives a filled-example JSON the user can fill in or adapt — sections for companies, roles, projects, skills, certifications, anything the user wants LinkRight to remember) + **"Upload file"** (drag-and-drop). On success: small summary (*"Added 12 new highlights"*) + CTA back to the highlights page (Screen 5) to review.
- Connected integrations: LinkedIn (connected / disconnect), GitHub (for Pages hosting).
- Danger zone: delete account (confirms twice).

**Principle:** settings shouldn't feel like a punishment. Give power users a fast path (bulk upload); don't force casual users to see it front-and-centre.

---

### 21. Notifications drawer (accessible from any screen via bell icon)

**User's goal:** see what changed since their last check, in chronological order.

**Must be visible:**
- Short list (max 8–10), newest first.
- Each item: coloured dot (category) · one-line title · timestamp · click-to-deep-link.
- Categories (plain user-facing labels): *New matching job* (teal) · *Profile ready* (purple) · *Post scheduled / sent* (pink) · *Interview prep reminder* (sage) · *Streak nudge* (gold).
- "Mark all read" at top.
- Empty state for first-time users: *"We'll nudge when something new matters."*

**Principle:** notifications exist to pull the user back; never to push them away. If in doubt, show less.

---

## Part 4 — Cross-screen elements

- **Global nav** (on all dashboard + wizard pages): wordmark left · main sections center · notification bell + create-resume CTA + avatar menu right. Current section visually indicated.
- **Step indicators** for onboarding + resume wizard: pill steps, current step clearly marked (never as "disabled").
- **Toasts**: teal for positive (e.g. *"Profile ready"*, *"Post sent"*), gold for in-flight (e.g. *"Still setting up your profile…"*, rate-limit cooldowns), coral only for destructive or action-required events. Copy in plain English — no "embedding", no "memory layer" in toast text. Never auto-dismiss if the user needs to act.
- **Loading**: single teal spinner + one-line explanation of what's loading.
- **Empty states**: dashed-border card, friendly helper, one clear next action.
- **Coming-soon labels**: gold "Soon" pill, disabled button. Never greyed-out without explanation.

---

## Part 5 — States every screen must handle

| State | When it shows | How it feels |
|---|---|---|
| Empty | no data yet | friendly, inviting, one clear next action |
| Loading | awaiting async | explains what's loading, honest ETA if >5s |
| In-flight / AI working | LLM / embedding running | purple hint, sparkles icon, user can continue other actions |
| Error | server / network / auth failure | calm, specific, retry CTA; never blame the user |
| Success | action completed | brief confirmation, points to next thing |
| Coming soon | future feature | gold "Soon" label, disabled affordance |
| Rate limited | user hit a cooldown | treat as info, not error; show time remaining |

---

## Part 6 — Principles claude.ai/design should internalise

1. **One clear CTA per screen.** If there are two, one must be visibly secondary.
2. **Copy first, design second.** Bad copy in a beautiful card is still bad. Read it aloud.
3. **Density over decoration.** LinkRight is for builders. Don't waste the viewport on hero images.
4. **Progress made visible.** Embedding, writing, scanning — show it moving. Latency hurts less when users can see it work.
5. **The profile is the product's foundation, not plumbing.** Surface it on every relevant screen: a "Your profile" card on the dashboard, source attributions like *"from your Amazon role"* on post drafts and highlights, and plain-English counters (*"47 highlights so far"*). Never expose internal words — "memory", "atoms", "nuggets", "Discover" — to the user.
6. **Honest numbers.** No 100% matches. No "10x faster" without a denominator. Show gaps.
7. **Reduce friction at every step.** If a step can be skipped without harming downstream quality, make it skippable. Discover is voluntary; Preferences has a skip; Find-roles never blocks on embedding.
8. **Loops back to the dashboard.** Every end-of-flow screen has a clear "what now" that feeds the user back into daily use.
9. **Desktop web only.** This is explicitly not a mobile product. Design for ≥1280px canvas. Don't optimise for tablet or phone.

---

## Part 7 — What's in scope for this design round

Screens 1 through 21 above. All critical user-facing surfaces for v1 of the product.

## Part 8 — Out of scope (intentionally not brief-ing yet)

- Admin routes (`/admin/*`) — internal tool, design later
- Interview-session screen (inside Screen 13) — full Wave 6 treatment in a separate brief
- Browser extension visual design — already specced in `specs/wave-8-extension-spec.md`
- Email templates (morning briefings, streak reminders) — Wave 7 separate brief
- **Mobile app / native / mobile-optimised web** — this product is **desktop web only** for now. Maximum surface is "desktop web + browser extension". Do not design mobile variants, tablet layouts, or responsive-down states. Ship desktop-quality, not compromise-everywhere.

---

## Part 9 — Hand-off sequence

1. Attach this brief + `LinkRight Design System.zip` to claude.ai/design.
2. Ask claude.ai/design to produce clickable mockups for screens 1–21, using the design system and its own judgment on visual variations.
3. Iterate visually. Approve or send back.
4. Export final bundle.
5. I implement screen-by-screen against the approved mockups.

## Part 10 — Reminders for claude.ai/design

- **Use the LinkRight Design System.** The zip is attached. Its tokens — teal / coral / purple / gold / pink / sage / skin-peach, Inter type scale, radii, shadows, spacing — are the single source of truth. Don't invent new tokens. When a screen needs a colour, pick from the system. When it needs a component, pick from the system. When the brief is silent on visual detail, the design system fills the gap — not your training data.
- **Desktop web only.** Design for ≥1280px canvas. No mobile, no tablet, no responsive-down states. Ship desktop-quality.
- **Think like a product designer solving user intent.** This brief gives you the WHY and WHAT for each screen, not the HOW. The HOW (layout, component choice, visual hierarchy, variations) is your job. Explore 2–3 variations per screen where there's genuine tension; pick the one that respects the design system + the screen's one-CTA rule.
- **The five pillars are the scaffold:** Discover, Find, Outreach, Prepare, Broadcast. Every screen should make it obvious which pillar the user is in. Use the design system's colour-per-zone guidance (e.g. sage for Prepare, pink for Broadcast human moments, purple for AI-in-flight).
- **Copy discipline:** shorter beats longer, specific beats generic, honest beats aspirational. If a headline sounds like a LinkedIn banner, rewrite it. Read it aloud — if it doesn't sound like a sharp human operator, it's wrong.
- **Voice:** builder-confident, number-led, warm-not-saccharine. Audience is ambitious Indian job-seekers with 3–8 years' experience. They've been let down by career tools before. Earn their trust with specificity, not hype.
- **Friction is the enemy.** Every required step should justify itself. Every optional step should be skippable in one click. Never block the funnel on async work (embedding, scanning) — show progress, let the user continue, deliver when ready.
- **The profile should feel visible, ownable, and growing.** Stats, plain counters, source attributions like *"from your Amazon role"*, the "Your profile" card on the dashboard — the user must feel their profile become more valuable every session. Remember: "profile" in the UI; "memory / atoms / Discover" only in this brief.
- **What to export for me:** a Figma (or equivalent) file with each numbered screen on its own frame, frames named "Screen 01 Landing" through "Screen 21 Notifications". I'll implement screen-by-screen. If you produce multiple variations, label each clearly.
