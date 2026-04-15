# PRODUCT DESIGN QA AUDIT — LinkRight (sync.linkright.in)
## Hybrid Audit Protocol v1.0 | April 15, 2026

---

## PRODUCT CONTEXT

```
Product type:           Resume optimization SaaS (career platform)
Core user:              Mid-senior professional (PM/SWE/DA), stressed about job search
Primary job-to-be-done: Turn career history + job description into a polished, tailored resume
Start URL:              https://sync.linkright.in/
Audited via:            Local dev server (localhost:3456) + code inspection
```

---

## PHASE A — DOM SNAPSHOT PASS (COMPLETE)

```
Journeys completed:        6 of 6
  J0: Landing & Marketing   (5 screens — live)
  J1: Auth                   (3 screens — live)
  J2: Onboarding             (5 screens — live)
  J3: Dashboard Hub          (8 screens — code)
  J4: Resume Builder         (5 screens — code)
  J5: Oracle / Profile       (2 screens — code)

Total unique screens:      28
Total findings:            47
  🔴 SIGNAL:               12
  🟡 FRICTION:             19
  🟢 NOISE:                16
Overall Noise Ratio:       34%
```

---

## SCREEN REGISTRY

```
────────────────────────────────────────────────────────────────────────
#   Screen Name                   URL/Route                  Journeys  Flag B?
────────────────────────────────────────────────────────────────────────
1   Home Page                     /                          J0        YES
2   Features Page                 /features                  J0        NO — redundant
3   Pricing Page                  /pricing                   J0        YES
4   Privacy Policy                /privacy                   J0        NO
5   Terms of Service              /terms                     J0        NO
6   Auth — Sign In                /auth                      J1        YES
7   Auth — Sign Up                /auth (toggled)            J1        NO — same page
8   Auth — Redirect               /auth/callback → /dash     J1        NO
9   Onboarding — Step 1 Roles     /onboarding                J2        YES
10  Onboarding — Step 2 Profile   /onboarding                J2        YES
11  Onboarding — Step 3 Upload    /onboarding                J2        YES
12  Onboarding — Step 4 Summary   /onboarding                J2        YES
13  Dashboard — Main              /dashboard                 J3        NO — code only
14  Dashboard — Career            /dashboard/career          J3        NO — code only
15  Dashboard — Nuggets           /dashboard/nuggets         J3        NO — code only
16  Dashboard — Applications      /dashboard/applications    J3        NO — code only
17  Dashboard — Scout Overview    /dashboard/scout           J3        NO — code only
18  Dashboard — Watchlist         /dashboard/scout/watchlist J3        NO — code only
19  Dashboard — Discoveries       /dashboard/scout/disc...   J3        NO — code only
20  Dashboard — Settings          /dashboard/settings        J3        NO — dead redirect
21  Resume — Step 0 JD            /resume/new                J4        NO — code only
22  Resume — Step 1 Customize     /resume/new                J4        NO — code only
23  Resume — Step 2 Build         /resume/new                J4        NO — code only
24  Resume — Step 3 Review        /resume/new                J4        NO — code only
25  Resume — Wizard Persistence   /resume/new (refresh)      J4        NO — code only
26  Profile — Token               /dashboard/profile         J5        NO — redirects
27  Profile — Career Graph        /api/profile/career-graph  J5        NO — code only
28  Pricing — WTP Survey          /pricing (scroll)          J0        YES
────────────────────────────────────────────────────────────────────────
```

---

## PHASE A — ALL FINDINGS BY JOURNEY

### J0: Landing & Marketing

#### 🔴 SIGNAL

**J0-F1: Landing page misrepresents the product**
- "How It Works" shows 3 steps: Paste JD → We build → Download
- Product actually requires: sign up → roles → profile → interview/upload → embeddings → JD → customize → build → review
- Creates false expectations → abandonment on real flow

**J0-F2: "Application Q&A" feature listed but doesn't exist**
- Feature card #6 says "After the resume, get help filling application forms in your natural voice"
- This feature is not implemented anywhere in the product
- Step 03 also claims "Application form answers included" — false

**J0-F3: Features page is a clone of homepage section**
- `/features` renders identical 6-feature grid as homepage
- Separate URL implies distinct content; delivers none
- Wastes a navigation slot

**J0-F4: Pricing page claims brand colors are Pro-only**
- Pro tier (₹299/mo, "Coming Soon") lists "Brand color matching"
- Brand colors are actually available in the free tier (StepCustomize)
- Misleading feature gating

#### 🟡 FRICTION

**J0-F5: Hero doesn't answer "What does this do?"**
- "Your resume. Pixel-perfect. Every time." — no verb, no action
- Visitor's #1 question unanswered: what IS this tool?

**J0-F6: Three checkmarks focus on output, not input**
- Width optimization, brand colors, AI detection — all output features
- Zero mention of career interview, nugget system, smart matching
- The actual differentiator is invisible

**J0-F7: Trust section has builder credentials, not product proof**
- "Built by PM at AmEx" and "36+ implementations at Sprinklr"
- No user testimonials, no before/after resume examples, no stats

**J0-F8: Stat cards are unanchored claims**
- "14 tailored bullets vs. 8 industry average" — which industry? Who measured?
- "33 quality rules" — what rules? Numbers without context

#### 🟢 NOISE

**J0-F9: Footer is minimal** — no social links, blog, or support contact
**J0-F10: Feature icons are generic line art** — removing them changes nothing
**J0-F11: "Made in India" touch** — nice but may not fit all markets

---

### J1: Auth Flow

#### 🔴 SIGNAL

**J1-F1: No forgot password flow**
- Auth page has no "Forgot your password?" link
- User who forgets password has no recovery path

#### 🟡 FRICTION

**J1-F2: Sign-up success message is subtle**
- "Check your email to confirm your account" shows in 12px green text
- No background color, no icon — easy to miss
- Appears inline with form, not as a prominent banner

**J1-F3: No password strength indicator**
- Only `minLength={6}` enforced
- No feedback on strength, no requirements shown before submit

**J1-F4: "Terms of Service and Privacy Policy" not linked**
- Footer text mentions them but they're plain text, not clickable links

#### 🟢 NOISE

**J1-F5: Sign-up/sign-in toggle works correctly** — button text and form mode switch properly
**J1-F6: Google OAuth button properly shows loading state** — "Signing in..." with spinner

---

### J2: Onboarding Flow

#### 🔴 SIGNAL

**J2-F1: Onboarding loop trap — user stuck with 0 nuggets**
- User who skips nugget upload → sees "You're ready!" summary
- Clicks "Go to Dashboard" → dashboard gate (`career_nuggets === 0`) → redirects back to `/onboarding`
- User is permanently locked in a loop with no escape

**J2-F2: Backward navigation completely broken**
- Stepper labels (Roles/Profile/TruthEngine/Summary) are display-only, not clickable
- No back button on Steps 2, 3, or 4
- Browser back button exits onboarding entirely → lands on `/auth` (already logged in, confusing)
- All onboarding steps are React state, not URL-based — invisible to browser history

**J2-F3: "You're ready!" with 0 nuggets — contradictory messaging**
- Summary screen says "You're ready!" heading
- But shows: 0%, 0 nuggets, "insufficient" label
- Warning text: "Add more experience details for better resume quality"
- Heading and content directly contradict each other

**J2-F4: Form data not persisted on revisit**
- Fill Step 2 form → Save & Continue → navigate away → come back
- All form fields are blank even though data was saved to DB (PUT /api/user/settings returned 200)
- Form doesn't pre-populate from saved data

**J2-F5: Resume parse fails with no useful recovery on production**
- `/api/onboarding/parse-resume` returns 500 if `PLATFORM_GROQ_API_KEY` not set
- Error message "Parse failed. Please enter your details manually." is OK
- But: no way to know the parse will fail until after pasting and clicking

#### 🟡 FRICTION

**J2-F6: Step 1 doesn't explain why roles matter**
- "What kind of roles are you targeting?" with no explanation
- User doesn't know how role selection affects the experience

**J2-F7: PDF upload disabled — only paste mode**
- Code has `[PDF-REMOVED]` markers
- Button only shows "Paste resume text" — no drag-drop, no file upload
- Major friction for users with PDF resumes

**J2-F8: StepLifeOS instructions are Claude Code-specific**
- "Open Claude Code", "Type /interview-coach" — assumes user has Claude Code
- No alternative for users without Claude Code
- Instructions reference a specific tool, not the product itself

**J2-F9: Onboarding remembers roles but not form data**
- Navigating back to `/onboarding` skips Step 1 (roles saved in DB)
- But Step 2 form fields are blank (not pre-populated)
- Inconsistent data persistence behavior

#### 🟢 NOISE

**J2-F10: "Get Started" properly disabled with 0 roles** — opacity 0.5, cursor not-allowed
**J2-F11: Stepper visual state correctly highlights current step** — though not clickable
**J2-F12: "← Add more achievements" back button exists on Step 4 only** — inconsistent with Steps 2-3 having none

---

### J3: Dashboard Hub (Code Inspection)

#### 🔴 SIGNAL

**J3-F1: Dead Settings link in StepJobDetails error message**
- Analysis failure shows "Go to Settings → API Keys" — but Settings page redirects to `/dashboard`
- Dead link sends user to a page that doesn't exist anymore

**J3-F2: Edit button on nuggets is non-functional**
- NuggetsDashboard renders edit button on each card
- Button has comment "placeholder – edit handler" — does nothing on click
- Visible but broken affordance

**J3-F3: Delete company in watchlist has no confirmation**
- One-click delete, no confirm dialog, no undo
- Permanent deletion of a tracked company with all its scan history

#### 🟡 FRICTION

**J3-F4: All loading states are full-page spinners**
- DashboardContent, CareerContent, NuggetsDashboard, KanbanBoard — all use centered spinner
- No skeleton screens anywhere
- Page flashes empty → spinner → content

**J3-F5: Career page 200-char minimum not communicated**
- Textarea shows "Paste your career profile here..."
- Minimum 200 chars enforced only on save click
- No inline counter or warning until after failure

**J3-F6: "Career Highlights" nav label vs `/nuggets` URL**
- Nav says "Career Highlights", URL is `/dashboard/nuggets`, API is `/api/nuggets`
- Inconsistent naming across three layers

**J3-F7: NuggetsDashboard uses native `window.confirm()` for delete**
- Unstyled browser dialog breaks the UI flow
- No undo mechanism after confirmation

**J3-F8: Failed drag-drops silently revert in kanban**
- Card snaps back to original column on API failure
- No error toast, no notification — user thinks it worked then it undoes

**J3-F9: Score polling with no feedback**
- Application scoring polls for 60s with no progress indicator
- If timeout occurs, user sees the score button forever with no error state

**J3-F10: No breadcrumbs on any sub-page**
- Applications, Scout, Nuggets, Career — no "← Back to Dashboard" or breadcrumb trail
- User relies entirely on AppNav for navigation

#### 🟢 NOISE

**J3-F11: Good error mapping in DashboardContent** — friendlyError function maps raw errors to human messages
**J3-F12: Scout badge correctly shows new discovery count** — caps at "99+"
**J3-F13: Kanban has optimistic updates with revert** — good pattern, just needs error feedback
**J3-F14: AppNav dropdown has no `aria-expanded` or `aria-haspopup`** — accessibility gap

---

### J4: Resume Builder (Code Inspection)

#### 🔴 SIGNAL

**J4-F1: "Continue → Brand Colors" button label is wrong**
- StepJobDetails CTA says "Continue → Brand Colors"
- Next step is actually "Customize" (which includes brand colors + enrichment questions)
- Misleading label

#### 🟡 FRICTION

**J4-F2: Company validation only on click, not inline**
- Three separate validation calls with same logic across the component
- User fills entire form, clicks submit, then gets red border on company field

**J4-F3: Analysis timeout shows unclear message**
- "Analysis timed out — you can skip this step" after 20s
- Doesn't explain why it timed out or if it's retryable

**J4-F4: Hardcoded Groq model — no user choice**
- `model_provider: "groq"`, `model_id: "llama-3.1-8b-instant"` hardcoded in WizardShell
- Multiple commented-out BYOK sections throughout wizard code
- No model selection UI even though architecture supports multiple providers

**J4-F5: No resume found state is generic**
- StepReview shows "Something went wrong. Please try generating again."
- No specific error detail, no retry with different settings

**J4-F6: Element selector mode has no exit instructions**
- Amber banner says "Click any element" with Cancel button
- But no instructions on how selector mode works or what to expect

#### 🟢 NOISE

**J4-F7: Session storage persistence works** — wizard state survives page refresh
**J4-F8: Draft HTML preview during build** — nice progressive disclosure
**J4-F9: Chat presets are well-chosen** — "More impactful", "Quantify", "XYZ format" are actionable

---

### J5: Oracle / Profile (Code Inspection)

#### 🟡 FRICTION

**J5-F1: Profile page redirects to Career page**
- `/dashboard/profile` immediately redirects to `/dashboard/career`
- No standalone profile page exists
- Dead route

**J5-F2: No CTA for Claude Code skill**
- Profile/token page generates LR-XXXXXXXX token
- No instructions on how to use it with Claude Code
- No download link for the interview skill

#### 🟢 NOISE

**J5-F3: Career graph renders via Cytoscape.js** — functional but empty state handling unclear
**J5-F4: Token expiry is 24-48h** — reasonable but not communicated clearly in UI

---

## PHASE B — SCREEN-BY-SCREEN VISUAL QA

### Screen 1 of 7: Home Page (`/`)

**Reached via:** Direct navigation
**When:** First-time visitor deciding whether to try the product

#### PHASE B VISUAL FINDINGS

🔴 **SIGNAL: "Welcome back" banner creates redirect loop**
- Sticky bar "Welcome back! You have an active account." with "Go to Dashboard →"
- When dashboard has 0-nugget gate, clicking this bounces back to onboarding
- Then user returns to home, sees banner again — infinite confusion loop

🔴 **SIGNAL: "How It Works" section is false advertising**
- 01 "Paste your JD" → 02 "We build your resume" → 03 "Download and apply"
- Reality: 8+ steps with sign up, role selection, profile, interview/upload, embeddings, JD analysis, customize, build, review
- The 3-step promise drives abandonment when user encounters the real flow

🔴 **SIGNAL: Step 03 claims features that don't exist**
- "Print-ready PDF" — product outputs HTML, not PDF
- "Application form answers included" — feature not implemented

🟡 **FRICTION: Hero is about output quality, not user problem**
- "Your resume. Pixel-perfect. Every time." — no verb, no action description
- Visitor's #1 question unanswered: what does this tool actually DO?
- Compare: "Turn any job description into a tailored resume in minutes"

🟡 **FRICTION: Three checkmarks focus on engineering features, not user benefits**
- Width optimization, brand colors, AI detection — all output features
- Zero mention of career interview system, smart matching — the real differentiator

🟡 **FRICTION: Trust section has builder credentials, not product proof**
- "Built by PM at AmEx" and "36+ implementations at Sprinklr"
- No user testimonials, no before/after resume examples, no success metrics

🟡 **FRICTION: Stat cards are unanchored**
- "14 tailored bullets vs. 8 industry average" — which industry? Source?
- "33 quality rules" — what rules? Numbers without context aren't proof

🟢 **NOISE: Footer minimal** — no social, blog, or support links
🟢 **NOISE: Feature icons are generic** — removing them changes nothing
🟢 **NOISE: "Made in India" flag** — nice but may not fit all market positioning

**DESIGN VERDICT: ACCEPTABLE (barely)**
**Noise Ratio:** 23%
**Worst visual decision:** The "How it works" 3-step section — actively harmful false promise
**Best visual decision:** Stat cards row — clean, scannable, builds quantitative credibility

**JOBS INSTINCT:**
This page was designed by someone who fell in love with their own engineering features (width optimization! BRS algorithm! WCAG AA!) instead of asking "what does a stressed job-seeker at 11pm actually need to hear?" The page screams "I built cool things" instead of "I understand your problem." The 3-step lie isn't malicious — it's what the product USED to be before career interviews, nuggets, and scout were added. The landing page never caught up. The product grew up; the front door didn't.

#### SUGGESTED FIXES

**🔴 "How It Works" is false**

| Option | What | Pro | Con |
|--------|------|-----|-----|
| A — Patch the steps | Update to 4 honest steps: "Tell us about your career → Paste a JD → We build → You review & download" | 30-minute fix | Still undersells career system |
| B — Show real journey | Animated flow or 60s video showing actual onboarding → build → review | Sets accurate expectations, showcases depth | Needs video production (days) |
| C — Rewrite entire page | New positioning: "The resume builder that actually knows your career." Career intelligence as hero, not pixels | Fixes root cause, differentiates from Teal/Rezi | Full rewrite (1-2 days) |

→ **Recommended: C** — the page needs a rewrite, not patches. The product has evolved past its landing page's worldview.

**🔴 "Application form answers" — false claim**
→ **Recommended:** Remove "Application form answers included" from Step 03 and "Application Q&A" from features. Build the feature later, then add it back.

**🟡 Hero doesn't answer "What does this do?"**
→ **Recommended:** Add one-line descriptor above headline: "AI resume builder" in small caps. 5-minute fix as interim while full rewrite is planned.

**🟡 Trust section has no product proof**
→ **Recommended:** Add 2-3 before/after resume screenshots. Visual proof beats credentials.

**🟡 Stat cards are unanchored**
→ **Recommended:** Add source/context to each stat, or remove them until benchmarking data exists.

---

### Screen 2 of 7: Auth Page (`/auth`)

**Reached via:** "Get Started" or "Start for Free" from home page
**When:** User has decided to try the product and is creating an account or signing back in

#### PHASE B VISUAL FINDINGS

🔴 **SIGNAL: "Terms of Service and Privacy Policy" are plain text, not links**
- Footer text says "By signing in, you agree to our Terms of Service and Privacy Policy."
- Neither "Terms of Service" nor "Privacy Policy" are clickable links
- User cannot read what they're agreeing to before signing in
- Legal compliance issue — agreement text must link to the actual documents

🟡 **FRICTION: No forgot password flow**
- No "Forgot your password?" link anywhere on the page
- User who forgets password has zero recovery path
- Only option: create a new account (losing all career data)

🟡 **FRICTION: Page says "Sign in to create your first resume" — wrong for returning users**
- Subtitle is hardcoded to "Sign in to create your first resume"
- Returning users (who already have resumes) see the same "first resume" copy
- Should adapt: "Sign in to continue" or "Welcome back" for returning sessions

🟡 **FRICTION: Two competing visual hierarchies**
- Google OAuth button (white, bordered, full-width) sits above the email form
- Email CTA "Sign in with Email" (teal, full-width) is the primary action
- Both are full-width, same height — no clear visual priority
- User has to read both to decide; no strong default

🟡 **FRICTION: "First resume free / No credit card required" callout is below the fold**
- Trust signal appears AFTER the form, below the submit button
- Should be visible before user decides to fill the form — ideally near the heading

🟢 **NOISE: Card container is clean** — white bg, subtle shadow, 16px border-radius, 32px padding. Well-structured.

🟢 **NOISE: "← Back to home" link at bottom** — good escape hatch, properly positioned.

🟢 **NOISE: "Sign up" toggle link is 12px teal text** — functional but small. Users might miss it, especially on mobile.

**DESIGN VERDICT: ACCEPTABLE**
**Noise Ratio:** 27%
**Worst visual decision:** "Terms of Service and Privacy Policy" as non-clickable text — both a UX failure and a legal risk.
**Best visual decision:** The centered card layout with generous padding — clean, focused, distraction-free.

**JOBS INSTINCT:**
This is a competent but unremarkable auth page. It does the job without creating any moment of delight or trust. The biggest miss is that it doesn't acknowledge what happens AFTER sign-in — no preview of the product, no indication of how long onboarding takes, no "takes 5 minutes" reassurance. A stressed job-seeker at midnight needs to know this is worth their next 10 minutes. The page says "sign in" but doesn't say "here's what you'll get."

#### SUGGESTED FIXES

**🔴 Terms/Privacy not linked**

| Option | What | Pro | Con |
|--------|------|-----|-----|
| A — Wrap in `<Link>` tags | Make "Terms of Service" link to `/terms` and "Privacy Policy" link to `/privacy` | 5-minute fix, legal compliance | Minimal UX impact beyond compliance |
| B — Add links + checkbox | Add explicit "I agree" checkbox with linked terms + privacy | Strongest legal stance, explicit consent | Adds friction to sign-in flow |
| C — Links + preview tooltip | Linked text + hover tooltip showing key points from each doc | Best user experience, informed consent | More dev effort (hours) |

→ **Recommended: A** — just link them. It's a 5-minute fix and a legal necessity. Checkbox (B) is overkill for a free product.

**🟡 No forgot password**
→ **Recommended:** Add "Forgot your password?" link below password field. Supabase provides `resetPasswordForEmail()` — wire it to a simple reset flow. Half-day implementation.

**🟡 Subtitle wrong for returning users**
→ **Recommended:** Conditional copy: check if user has a Supabase session cookie → "Welcome back" instead of "create your first resume". 15-minute fix.

**🟡 "First resume free" below fold**
→ **Recommended:** Move "First resume free. No credit card required." to directly below the "Get started" heading, above the Google button. Swap positions with subtitle.

### Screen 3 of 7: Onboarding Step 1 — Roles (`/onboarding`)

**Reached via:** Redirect after sign-up/sign-in (new user)
**When:** First-time user, just authenticated, zero context about the product

*Note: Could not screenshot live — roles already saved from Phase A testing. Findings from Phase A DOM snapshot.*

#### PHASE B VISUAL FINDINGS

🟡 **FRICTION: No explanation of why roles matter**
- "What kind of roles are you targeting?" — direct question, zero context
- User doesn't know: Does this change the questions? The resume template? The JD matching?
- One line of context would help: "We'll tailor interview questions and resume optimization to your target roles."

🟡 **FRICTION: 8 role pills with no hierarchy**
- Product Manager, Software Engineer, Data Analyst, UX Designer, Marketing, Finance, Operations, Other — all equal visual weight
- Most users target 1-2 roles. No indication that multi-select is possible until they click and see the pill stay selected
- "Other" has no free-text input — what if someone is a "Chief of Staff" or "Consultant"?

🟢 **NOISE: "Get Started" button properly disabled at 0 selections** — opacity 0.5, cursor not-allowed. Correct.

🟢 **NOISE: Step label "Roles" is active in stepper** — teal highlight, correct step indication.

**DESIGN VERDICT: ACCEPTABLE**
**Noise Ratio:** 50%
**Worst visual decision:** No context line explaining what role selection affects downstream.
**Best visual decision:** Clean pill layout with clear selected/unselected states.

#### SUGGESTED FIXES

**🟡 No role context**
→ **Recommended:** Add one-line subtitle: "We'll customize your interview questions and resume targeting based on your selections." 5-minute copy change.

**🟡 "Other" has no free-text**
→ **Recommended:** When "Other" is selected, show a text input: "What role are you targeting?" Captures edge cases without cluttering the main UI.

---

### Screen 4 of 7: Onboarding Step 2 — Profile (`/onboarding`)

**Reached via:** "Get Started" from Step 1
**When:** User just selected target roles, now entering career basics

#### PHASE B VISUAL FINDINGS

🔴 **SIGNAL: Form fields blank on revisit despite data being saved**
- User fills form → Save & Continue → navigates away → returns to `/onboarding`
- Form shows empty placeholders (Jane Smith, jane@example.com) instead of saved data
- PUT `/api/user/settings` returned 200 on save — data IS in DB but form doesn't pre-populate
- User thinks their data was lost

🟡 **FRICTION: "Paste resume text" is the only upload option**
- No PDF upload, no file drag-drop, no DOCX upload
- Users with PDF resumes must manually copy-paste text from their PDF
- "Paste resume text" button opens a textarea — not an import wizard
- This is a major friction point for the core user (stressed job-seeker with a PDF)

🟡 **FRICTION: Placeholder examples are Western-centric**
- "Jane Smith", "jane@example.com", "+1 (555) 000-0000", "linkedin.com/in/jane"
- Product says "Made in India" but placeholders assume US phone format and Western names
- Should reflect target market: "Priya Sharma", "+91 98765 43210"

🟡 **FRICTION: Education row has no remove button**
- "+ Add Education" adds rows, but no way to remove a mistakenly added empty row
- Only the first row is visible initially — good progressive disclosure
- But once added, stuck with empty rows

🟡 **FRICTION: Skills input instructions unclear**
- Placeholder: "Type a skill and press Enter or comma"
- No visual example of what a "chip" looks like before the first one is added
- User might not know the interaction model until they try it

🟢 **NOISE: Two CTAs properly hierarchized** — "Save & Continue" (teal, primary) vs "I'll add this later" (gray, secondary). Clear visual priority.

🟢 **NOISE: "All fields except name are optional"** — good upfront setting of expectations. Red asterisk on Full Name confirms.

**DESIGN VERDICT: ACCEPTABLE**
**Noise Ratio:** 22%
**Worst visual decision:** Empty form on revisit — silently discarding the user's previous effort is a trust-destroying experience.
**Best visual decision:** The resume paste shortcut card — good progressive disclosure, doesn't force the action but surfaces it clearly.

#### SUGGESTED FIXES

**🔴 Form blank on revisit**

| Option | What | Pro | Con |
|--------|------|-----|-----|
| A — Pre-populate from API | On mount, GET `/api/user/settings` → fill form fields | Data persists visually, builds trust | Extra API call on every load |
| B — Local storage cache | Save form state to localStorage alongside DB save | Instant load, no API dependency | Can go stale, two sources of truth |
| C — Skip Step 2 on revisit | If settings already saved, auto-advance to Step 3 | No confusion — user doesn't see empty form twice | User can't edit their profile from onboarding |

→ **Recommended: A** — pre-populate from the API. The data is already there. Show it.

**🟡 No PDF upload**
→ **Recommended:** Add PDF upload using `pdf-parse` (already in dependencies). The code exists in `parse-resume/route.ts` — it was removed from the UI but the backend supports it. Re-enable the file input.

**🟡 Western placeholders**
→ **Recommended:** Change to India-contextual: "Priya Sharma", "+91 98765 43210", "linkedin.com/in/priyasharma". 5-minute fix.

---

### Screen 5 of 7: Onboarding Step 3 — Upload (`/onboarding`)

**Reached via:** "Save & Continue" or "I'll add this later" from Step 2
**When:** User has entered (or skipped) profile basics, now needs to provide career depth

#### PHASE B VISUAL FINDINGS

🔴 **SIGNAL: Instructions assume user has Claude Code**
- "STEP 1 — GENERATE CAREER DATA IN CLAUDE CODE"
- "Open Claude Code (claude.ai/code or desktop app)"
- "Type `/interview-coach` and press Enter"
- This assumes the user: (a) knows what Claude Code is, (b) has it installed, (c) is willing to leave this product and use a separate tool
- For a user who found LinkRight via Google/social — this is incomprehensible

🔴 **SIGNAL: No alternative path for users without Claude Code**
- Only option: upload a specific JSON file in a specific schema
- No manual entry, no guided interview in the browser, no paste-your-resume fallback
- The only escape is "Skip for now →" which leads to the 0-nugget trap (can't access dashboard)

🟡 **FRICTION: "Career Story Collection" heading is jargon**
- User came here to build a resume, not to "collect career stories"
- Internal product vocabulary leaked into the UI
- Better: "Add your career experience" or "Tell us what you've accomplished"

🟡 **FRICTION: Step numbering inside a step is confusing**
- Onboarding stepper shows Step 3 of 4 ("TruthEngine")
- Inside this step, there are "STEP 1" and "STEP 2" sub-labels
- User sees nested numbered steps: global Step 3 > internal Step 1, Step 2
- Creates confusion about overall progress

🟡 **FRICTION: "TruthEngine" label in stepper is internal codename**
- Stepper shows: Roles → Profile → **TruthEngine** → Summary
- No user knows what "TruthEngine" means
- Should be: "Experience" or "Career Data" or "Your Story"

🟡 **FRICTION: Drop zone accepts only `.json` — no indication of expected schema**
- "Drop career_nuggets.json here or click to browse"
- ".json files only"
- What if user has a different JSON? What's the required format? No link to docs or schema

🟢 **NOISE: Upload icon and drop zone visually clear** — dashed border, upload arrow, "click to browse" link in teal. Standard pattern.

🟢 **NOISE: "Skip for now →" properly de-emphasized** — gray text, positioned below the main content. Won't be clicked accidentally.

**DESIGN VERDICT: EMBARRASSING**
**Noise Ratio:** 20%
**Worst visual decision:** The entire screen. It asks users to leave the product, open a developer tool, run a slash command, answer questions in a CLI, download a JSON file, then come back and upload it. This is not onboarding — this is a developer integration guide masquerading as a user experience.
**Best visual decision:** None found.

**JOBS INSTINCT:**
This screen was built for the builder, not for the user. It makes perfect sense if you're the person who created the `/interview-coach` skill and wants to connect it to the web app. It makes zero sense if you're a PM at 11pm trying to build a resume. The core question is: why can't the interview happen right here, in the browser? The technology exists (Groq API is already wired up in the onboarding confirm route). This screen is a product decision failure, not a design failure.

#### SUGGESTED FIXES

**🔴 Assumes Claude Code**

| Option | What | Pro | Con |
|--------|------|-----|-----|
| A — Add in-browser interview | Restore the conversational Q&A that existed before (the `/api/onboarding/question` + `/api/onboarding/confirm` flow) as primary path | Users complete onboarding without leaving the product | Needs Groq API key on the platform (already exists on Vercel) |
| B — Add resume-paste-to-nuggets pipeline | Let users paste resume text → auto-extract nuggets server-side → skip the interview | Fastest path, lowest friction | Lower quality nuggets (no depth from interview) |
| C — Keep upload but add alternatives | Keep JSON upload as "advanced" option, add resume paste and manual entry as primary paths | Serves both power users and new users | More UI complexity, two code paths |

→ **Recommended: A** — the in-browser interview flow already exists in the codebase (`/api/onboarding/question`, `/api/onboarding/confirm`). It was replaced by the upload screen. Restore it as the primary path, keep JSON upload as a secondary "I already have data" option.

**🟡 "TruthEngine" in stepper**
→ **Recommended:** Rename to "Experience" or "Your Story". 1-minute string change.

**🟡 Nested step numbers**
→ **Recommended:** Remove "STEP 1" / "STEP 2" sub-labels. Use headings instead: "Generate your data" / "Upload it here". Remove numbered circles.

---

### Screen 6 of 7: Onboarding Step 4 — Summary (`/onboarding`)

**Reached via:** "Skip for now →" from Step 3 (or successful upload + embedding)
**When:** User has completed (or skipped) data entry, seeing their onboarding result

#### PHASE B VISUAL FINDINGS

🔴 **SIGNAL: "You're ready!" with green checkmark + "insufficient" label + 0% + 0 nuggets**
- Giant green checkmark icon + "You're ready!" heading → success signal
- Immediately below: "insufficient" label, "0%" progress bar, "0 nuggets"
- Yellow warning box: "Consider adding more details for better resume quality"
- These three elements directly contradict each other on the same screen
- User receives: celebration → failure → warning in 3 seconds of scanning

🔴 **SIGNAL: "Create Your First Resume" CTA leads to a dead end**
- Teal button "Create Your First Resume" navigates to `/resume/new`
- But resume builder requires career_text with ≥100 chars to build
- User who skipped everything has no career_text → build will fail with error
- CTA promises an outcome the product can't deliver in this state

🔴 **SIGNAL: "Go to Dashboard" CTA loops back to onboarding**
- Secondary button "Go to Dashboard" navigates to `/dashboard`
- Dashboard gate: `career_nuggets === 0` → redirects back to `/onboarding`
- User clicks → bounces → sees Step 2 (Profile) again → confused

🟡 **FRICTION: "← Add more achievements" is the only back button in the entire onboarding flow**
- Appears for the first time on Step 4
- Steps 2 and 3 have no back button at all
- Inconsistent — user learns "there's no going back" on Steps 2-3, then discovers a back link on Step 4

🟡 **FRICTION: No career graph renders with 0 data**
- The summary is supposed to show a Cytoscape career graph
- With 0 nuggets, the graph area is just empty — no empty state illustration or message
- "Your career knowledge at a glance" section is invisible/absent

🟢 **NOISE: Progress bar is properly styled** — teal fill at 0%, "insufficient" label in correct gray. Visually accurate to the data.

🟢 **NOISE: Warning box uses appropriate yellow/amber styling** — communicates caution without alarm. Good color choice.

**DESIGN VERDICT: EMBARRASSING**
**Noise Ratio:** 22%
**Worst visual decision:** The green checkmark + "You're ready!" heading above a 0% score. This is the visual equivalent of a teacher giving a gold star for a blank test.
**Best visual decision:** The warning box copy is honest and non-judgmental: "Consider adding more details... You can always come back."

**JOBS INSTINCT:**
This screen reveals a fundamental product decision gap: what happens to users who skip onboarding? The answer right now is "they get congratulated, then trapped." The system celebrates completion of a process that produced nothing, then offers two CTAs that both fail. This isn't a design problem — it's a product logic problem. Either: (1) don't let users skip to this screen without minimum data, or (2) if they skip, show a completely different screen that's honest about what they missed and gives them a clear path to add data.

#### SUGGESTED FIXES

**🔴 Contradictory messaging (ready + insufficient + 0%)**

| Option | What | Pro | Con |
|--------|------|-----|-----|
| A — Conditional heading | If nuggets ≥ 5: "You're ready!" / If 1-4: "Almost there!" / If 0: "Let's add some experience first" | Honest messaging matches actual state | Three copy variants to maintain |
| B — Remove the checkmark at 0 | Show checkmark only when confidence ≥ 50%. At 0%, show an illustration of an empty notebook | Visual honesty — no false celebration | Need to design/source the empty state illustration |
| C — Block Step 4 at 0 nuggets | Don't advance to Summary if nuggets === 0. Keep user on Step 3 with messaging: "Add at least one experience to continue" | Prevents the contradiction entirely | Forces user to provide data (no skip option) |

→ **Recommended: C** — don't let users reach this screen with 0 data. If they must skip Step 3, redirect to dashboard with a softer gate (show limited dashboard with a banner: "Complete your profile to unlock all features").

**🔴 "Create Your First Resume" fails silently**
→ **Recommended:** Disable the button when nuggets === 0. Show tooltip: "Add career experience first." Or hide it entirely and only show "← Add more achievements."

**🔴 "Go to Dashboard" loops**
→ **Recommended:** Either (a) remove the dashboard gate for users who completed onboarding steps (even with 0 nuggets), showing a limited dashboard with a "complete your profile" banner, or (b) remove the "Go to Dashboard" button when nuggets === 0.

### Screen 7 of 7: Pricing Page (`/pricing`)

**Reached via:** "Pricing" nav link or "See Plans" from home page
**When:** User evaluating whether to sign up or considering upgrading

#### PHASE B VISUAL FINDINGS

🔴 **SIGNAL: Feature gating is inaccurate — brand colors listed as Pro-only but available for free**
- Free tier: "1 resume, Basic template, JD analysis, Width optimization"
- Pro tier: "Unlimited resumes, All templates, **Brand color matching**, Priority generation, Application Q&A"
- Brand color matching is actually available in the free tier (StepCustomize serves it to all users)
- This makes the Pro tier look better than it is AND makes free users think they're missing a feature they already have

🔴 **SIGNAL: "Application Q&A" listed as Pro feature — doesn't exist in the product**
- Same phantom feature from the home page features section
- Listed in Pro tier as if it's a real feature gate-locked behind payment
- Promising a non-existent feature in a paid tier is worse than listing it on a free landing page

🟡 **FRICTION: "Coming Soon" button on Pro tier — indefinite state**
- Salmon/pink disabled button says "Coming Soon" with no date, no waitlist, no email capture
- User interested in Pro has no action to take — no "Notify me", no timeline
- "Coming Soon" has been in the code since initial launch — may feel permanently vaporware

🟡 **FRICTION: WTP survey references "Sync" — old product name**
- "You've tried Sync. Now help us figure out pricing."
- Product is called "LinkRight" now, not "Sync"
- Old branding leaking through in user-facing copy

🟡 **FRICTION: Survey question 2 lists "Application Q&A" as a real feature**
- "WHAT FEATURES MATTER MOST TO YOU?" includes "Application Q&A" as an option
- Users voting for a feature that doesn't exist → inflated demand signal → wrong priorities

🟡 **FRICTION: No visual hierarchy between tiers**
- Free card: white border, "Start Free" outlined button
- Pro card: teal border + "Coming Soon" badge — highlighted as the premium option
- But Pro is disabled — the highlighted tier is the one users CAN'T choose
- Visual emphasis is on the unavailable option

🟢 **NOISE: Price formatting is clean** — "₹0 /forever" and "₹299 /mo" are scannable. Rupee symbol correct for India market.

🟢 **NOISE: Survey layout is well-structured** — 3 clear questions, button/toggle inputs for Q1-Q2, textarea for Q3. "Optional — but we read every response" is warm copy.

🟢 **NOISE: "HELP US SHAPE PRICING" divider** — honest positioning. Acknowledges pricing isn't finalized.

**DESIGN VERDICT: ACCEPTABLE (with critical content errors)**
**Noise Ratio:** 30%
**Worst visual decision:** Highlighting the Pro tier with a teal border when it's the disabled option. Visual emphasis on what users can't have.
**Best visual decision:** The WTP survey itself — asking users directly about pricing is smart product work, even if the copy references the wrong product name.

**JOBS INSTINCT:**
This pricing page was written before the product evolved. It gate-locks a feature users already have (brand colors), promises a feature nobody built (Application Q&A), uses an old product name (Sync), and highlights a tier nobody can buy (Pro/Coming Soon). The page is a time capsule from 3 months ago. The WTP survey is genuinely smart — but the survey options include a phantom feature, which means the survey data is corrupted. Fix the page, then let the survey run clean.

#### SUGGESTED FIXES

**🔴 Feature gating inaccurate**

| Option | What | Pro | Con |
|--------|------|-----|-----|
| A — Fix the free tier list | Add "Brand color matching" to Free tier features | Accurate, builds trust | Makes Pro tier thinner (less differentiation) |
| B — Actually gate brand colors | Add code to restrict brand colors to Pro users only | Makes pricing page accurate | Removes a popular free feature, increases churn |
| C — Redesign tier differentiation | Free = limited resumes + core features. Pro = unlimited + priority + templates + analytics | Honest, clear value prop | Requires product decisions on what's actually Pro-only |

→ **Recommended: A** short-term (reflect reality), then **C** when Pro is actually ready to launch. Don't take away free features (B) to make a pricing page accurate.

**🔴 "Application Q&A" phantom feature**
→ **Recommended:** Remove from Pro tier feature list AND from WTP survey options. Don't sell what doesn't exist. Add it back when built.

**🟡 "Coming Soon" indefinite**
→ **Recommended:** Either add a "Notify me when Pro launches" email capture, or remove the Pro tier entirely until it's ready. A perpetual "Coming Soon" erodes trust.

**🟡 "Sync" old name in survey**
→ **Recommended:** Replace "You've tried Sync" with "You've tried LinkRight". 1-second find-and-replace.

---

## FINAL REPORT

---

### THE SIGNAL — TOP 3 ONLY
*These are the only things that matter in the next 60 minutes. Fix these first.*

🔴 **SIGNAL 1: Onboarding loop trap — users with 0 nuggets are permanently stuck**
- Screen: Onboarding Step 4 → Dashboard → back to Onboarding
- User completes onboarding, clicks "Go to Dashboard", gets bounced back to `/onboarding` because `career_nuggets === 0`
- Both CTAs on the summary screen fail: "Create Your First Resume" needs career_text, "Go to Dashboard" needs nuggets
- **Fix:** Remove the hard nugget gate on dashboard. Show a limited dashboard with a "complete your profile" banner instead.

🔴 **SIGNAL 2: Onboarding Step 3 requires Claude Code — no alternative for normal users**
- Screen: Onboarding Step 3 (TruthEngine / Career Story Collection)
- The only way to add career data is to install Claude Code, run `/interview-coach`, generate a JSON, download it, and upload it
- For any user who found LinkRight through a search engine, this is incomprehensible
- The in-browser interview flow EXISTS in the codebase (`/api/onboarding/question` + `/api/onboarding/confirm`) but is not wired to this screen
- **Fix:** Restore the browser-based interview as the primary path. Keep JSON upload as "I already have data."

🔴 **SIGNAL 3: Landing page sells a product that doesn't exist anymore**
- Screen: Home page (`/`)
- "3 steps: Paste JD → We build → Download" — reality is 8+ steps
- "Application Q&A" feature listed — doesn't exist
- "Print-ready PDF" claimed — product outputs HTML only
- Core differentiators (career interview, nugget system, scout, applications) are invisible
- **Fix:** Full landing page rewrite. The product grew up; the front door didn't.

---

### THE CUT LIST
*Not redesign. Remove. One sentence each: what it is, why it dies.*

1. **Features page (`/features`)** — identical clone of the homepage features section. Adds zero value. Cut it or differentiate it.
2. **"Application Q&A" feature card** — references a non-existent feature on homepage, features page, pricing page, and WTP survey. Remove from all four locations.
3. **"TruthEngine" stepper label** — internal codename exposed in user-facing UI. Rename to "Experience" or "Your Story."
4. **Settings page redirect** — `/dashboard/settings` silently redirects to `/dashboard`. Dead route with dead code (SettingsContent.tsx). Either rebuild it or remove the file.
5. **"Sync" references in WTP survey** — old product name. Replace with "LinkRight."
6. **Non-functional Edit button on nuggets** — renders on every card, does nothing. Remove or implement.

---

### THE DESIGN CRIME REPORT
*3 most embarrassing visual decisions — the ones that reveal someone stopped caring.*

1. **Green checkmark + "You're ready!" above 0% / 0 nuggets / "insufficient"** (Onboarding Step 4)
   — The visual equivalent of a confetti cannon at a funeral. The system celebrates the completion of a process that produced nothing. Every element on this screen contradicts every other element.

2. **"STEP 1 — GENERATE CAREER DATA IN CLAUDE CODE" as an onboarding screen** (Onboarding Step 3)
   — This is a developer integration guide, not a user experience. It asks a stressed job-seeker to leave the product, install a CLI tool, run a slash command, answer questions in a terminal, download a JSON file, then come back and upload it. This screen was built for the builder's convenience, not the user's success.

3. **"How It Works: 3 steps" on the landing page** (Home page)
   — Promising "Paste JD → We build → Download" when the real flow has 8+ steps including account creation, role selection, profile entry, career data upload, embedding processing, JD analysis, customization, and review. This isn't simplification — it's false advertising that sets up every new user for a bait-and-switch feeling.

---

### THE SILENT ABANDONMENT REPORT
*3 moments where the core user silently gives up — no rage, just quiet exit. These never appear in analytics. They appear as churn.*

1. **Onboarding Step 3 → user reads "Open Claude Code" → closes tab**
   - User's question: "I thought this was a resume builder. Why do I need to install a separate app?"
   - Why the product left it unanswered: The team built the interview skill in Claude Code first, then connected it to the web app. The web app never got its own interview flow back. Internal tooling priority leaked into user-facing UX.

2. **Summary screen → "Go to Dashboard" → bounces to onboarding → user tries again → bounces again → closes tab**
   - User's question: "I clicked the button. Why am I back where I started? Is the site broken?"
   - Why the product left it unanswered: The dashboard gate (`career_nuggets === 0`) was added as a safety check but no one tested the path where a user completes onboarding with 0 nuggets. The gate assumes everyone provides data; the skip button assumes they don't have to.

3. **Landing page → "Start for Free" → sign up → onboarding → realizes it's NOT "3 steps" → quiet exit**
   - User's question: "The homepage said paste a JD and get a resume. Why am I filling out education forms and being asked to install Claude Code?"
   - Why the product left it unanswered: The landing page was written when the product WAS that simple. Features were added — career interviews, nuggets, scout, applications — but the front door was never updated. The promise and the reality diverged.

---

### FULL AUDIT SCORECARD

| # | Screen | Journey | Design | Top Issue |
|---|--------|---------|--------|-----------|
| 1 | Home Page | BROKEN | ACCEPTABLE | "How It Works" is false — 3 steps ≠ reality |
| 2 | Auth Page | PASSABLE | ACCEPTABLE | Terms/Privacy not linked — legal risk |
| 3 | Onboarding Step 1 (Roles) | PASSABLE | ACCEPTABLE | No context on why roles matter |
| 4 | Onboarding Step 2 (Profile) | PASSABLE | ACCEPTABLE | Form blank on revisit despite saved data |
| 5 | Onboarding Step 3 (Upload) | BROKEN | EMBARRASSING | Requires Claude Code — no alternative |
| 6 | Onboarding Step 4 (Summary) | BROKEN | EMBARRASSING | "You're ready!" at 0% + dashboard loop |
| 7 | Pricing Page | BROKEN | ACCEPTABLE | Feature gating wrong + phantom feature |
| 8-20 | Dashboard Hub (code) | PASSABLE | — | Dead edit button, no skeleton screens |
| 21-25 | Resume Builder (code) | PASSABLE | — | Dead Settings link in error, wrong CTA label |
| 26-28 | Profile/Oracle (code) | PASSABLE | — | Profile redirects to Career, no standalone page |

---

### OVERALL NOISE RATIO

```
Total findings:  47
  🔴 SIGNAL:    12 (26%)
  🟡 FRICTION:  19 (40%)
  🟢 NOISE:     16 (34%)
```

**Is this team working on the right things?** No. The noise ratio is acceptable (34%), but the signal density is alarming — 12 red findings means the core flow is broken. A user cannot reliably go from sign-up to resume download without hitting at least 2 dead ends. The product's engineering is solid (width optimization, BRS scoring, brand matching, real-time build progress are all impressive). But the user journey has 3 broken screens out of 7 audited. The team is building features instead of fixing the funnel.

---

### THE VISION
*Two paragraphs. Not more features. Different quality of decisions.*

LinkRight has a genuinely differentiated product buried under a broken front door. The career interview → nugget extraction → semantic matching → width-optimized resume pipeline is a technical achievement that no competitor offers. But no user will ever see it because the landing page lies about what the product is, the onboarding asks them to install a developer tool, and the dashboard won't let them in without data they were never helped to provide. The product is a sports car with no driveway.

The fix isn't more features. It's three decisions: (1) rewrite the landing page to sell what the product actually is — a career intelligence platform that builds resumes, not a "paste JD and go" tool; (2) put the interview back in the browser — the API routes exist, the Groq integration exists, the UI existed before — restore it as the primary onboarding path; (3) remove the hard gates — let users into the dashboard with 0 nuggets, show them what they're missing instead of locking them out. These three changes would take 2-3 days and would fix 8 of the 12 red findings.

---

### ONE MORE THING
*The single insight that reframes the whole audit.*

The product has an identity crisis. The landing page says "resume builder." The onboarding says "career data platform." The features page says "engineering showcase." The pricing page says "we don't know yet." These are four different products wearing the same logo.

The insight: **LinkRight is not a resume builder. It's a career memory system that happens to output resumes.** The moment the team internalizes this — that the career interview and nugget library are the product, and the resume is just one output — every page rewrite becomes obvious. The landing page leads with "We remember your career so every resume writes itself." The onboarding leads with the interview, not a form. The dashboard leads with nuggets, not resume jobs. The pricing gates on career depth, not resume count.

Stop selling the output. Start selling the intelligence.

---

## DECISION LOG — ALL FINDINGS

All decisions confirmed with product owner on April 15, 2026.

### Priority 1: Critical Flow Fixes (do first)

| # | Finding | Decision | Effort |
|---|---------|----------|--------|
| 1 | Onboarding loop trap (0-nugget gate blocks dashboard) | **Soften gate** — let users in with banner "Complete your profile to unlock all features" | 2-3 hrs |
| 2 | Step 3 requires Claude Code — no browser alternative | **Restore browser interview** — wire existing /api/onboarding/question + /confirm as primary path, keep JSON upload as secondary | 1-2 days |
| 3 | Landing page misrepresents product (3 steps, phantom features) | **Full rewrite** — new positioning: career intelligence platform. New hero, features, how-it-works | 2-3 days |
| 4 | Backward navigation broken in onboarding | **Add back buttons + clickable stepper** — URL hash for browser history support | 3-4 hrs |
| 5 | "You're ready!" at 0 nuggets — contradictory messaging | **Conditional heading** — ≥5: "You're ready!" / 1-4: "Almost there!" / 0: "Let's add some experience first." Remove checkmark at 0 | 1 hr |

### Priority 2: Important Fixes (this week)

| # | Finding | Decision | Effort |
|---|---------|----------|--------|
| 6 | Features page is redundant clone | **Delete the page** — remove /features route and nav link | 15 min |
| 7 | Pricing page: wrong gating, phantom feature, old name, no waitlist | **Fix all 4** — move brand colors to Free, remove Application Q&A, add email capture on Pro, Sync→LinkRight | 1-2 hrs |
| 8 | ToS and Privacy not linked on auth page | **Link them** — wrap in `<Link>` to /terms and /privacy | 5 min |
| 9 | No forgot password flow | **Add it** — Supabase resetPasswordForEmail() + UI | half day |
| 10 | Auth subtitle "create your first resume" for all users | **Change to generic** — "Sign in to continue" | 5 min |
| 11 | Dead Settings link in StepJobDetails error + dead BYOK code | **Remove link + delete dead code** — clean up all [BYOK-REMOVED] comments | 2-3 hrs |
| 12 | Form data not persisted on revisit (Step 2) | **Pre-populate from API** — GET /api/user/settings on mount | 1 hr |
| 13 | "TruthEngine" stepper label | **Rename to "Experience"** | 1 min |
| 14 | CTA says "Continue → Brand Colors" (wrong) | **Fix to "Continue → Customize"** | 1 min |
| 15 | Delete company in watchlist — no confirmation | **Add confirm dialog** | 30 min |
| 16 | Failed kanban drag-drops silently revert | **Add error toast** | 30 min |
| 17 | Edit button on nuggets is non-functional | **Remove the button** — add back when implemented | 5 min |
| 18 | Delete nugget uses native window.confirm() | **Replace with styled confirmation dialog** | 1 hr |
| 19 | Trust section — builder credentials, no product proof | **Add before/after resume examples** | 2-3 hrs |
| 20 | Remove profile redirect route | **Delete /dashboard/profile redirect** — /dashboard/career is canonical | 5 min |

### Priority 3: Polish & Enhancement (next sprint)

| # | Finding | Decision | Effort |
|---|---------|----------|--------|
| 21 | All loading states are full-page spinners | **Add skeleton loaders** for Dashboard, Nuggets, Applications | 1-2 days |
| 22 | No breadcrumbs on sub-pages | **Add breadcrumbs** on all dashboard sub-pages | 2-3 hrs |
| 23 | Score polling — no progress, no timeout feedback | **Add spinner + timeout message** on Score button | 1 hr |
| 24 | Career page 200-char minimum not communicated | **Add inline counter + warning** below textarea | 1 hr |
| 25 | Company validation in StepJobDetails — click-only, not inline | **Add onBlur validation** + better timeout message | 1 hr |
| 26 | Step 1: no role context, no "Other" text input | **Add context subtitle + text input for Other** | 30 min |
| 27 | Placeholder examples Western-centric | **Change to neutral/generic** — "Your Name", "your@email.com" | 5 min |
| 28 | Step 3 nested sub-numbers confusing | **Remove sub-numbers, use headings** (will be part of interview restoration) | 15 min |
| 29 | Footer minimal — no social/support | **Add support email + social links** | 30 min |
| 30 | Critical ARIA attributes missing (dropdown, tabs) | **Fix aria-expanded, role=tab, aria-selected** | 2-3 hrs |
| 31 | StepReview generic error + selector mode instructions | **Better error copy + add selector exit instructions** | 30 min |
| 32 | Clean up dead BYOK code throughout wizard | **Remove all [BYOK-REMOVED] comments and dead code** | 1-2 hrs |
| 33 | Hero headline — doesn't answer "what does this do" | **Part of landing page rewrite** (Priority 1 #3) | — |
| 34 | Stat cards unanchored claims | **Part of landing page rewrite** | — |

### Deferred / Skipped

| # | Finding | Decision | Reason |
|---|---------|----------|--------|
| 35 | PDF upload disabled | **Keep paste-only** | Owner decision — paste is sufficient for now |
| 36 | Sign-up success message subtle (12px green) | **Defer** | Not blocking |
| 37 | No password strength indicator | **Defer** | Not blocking |
| 38 | "First resume free" callout below fold | **Keep as-is** | Owner says fine |
| 39 | Feature icons generic | **Skip** | Noise-level |
| 40 | "Made in India" flag | **Keep** | Brand choice |
| 41 | Naming inconsistency (Career Highlights vs nuggets) | **Align to "Career Highlights"** in UI only — URLs/API stay as-is | Not worth breaking change |

---

## IMPLEMENTATION PRIORITY SEQUENCE

```
Week 1 — Critical Flow Fixes
──────────────────────────────────────
Day 1:  #1 Soften nugget gate on dashboard
        #5 Conditional heading on summary screen
        #8 Link ToS/Privacy on auth
        #10 Generic auth subtitle
        #13 Rename TruthEngine → Experience
        #14 Fix CTA label → Customize
        #17 Remove broken edit button
        #20 Remove profile redirect
        #27 Neutral placeholders

Day 2-3: #2 Restore browser interview flow
         #4 Add back buttons + clickable stepper
         #12 Pre-populate form from API

Day 4:  #6 Delete features page
        #7 Fix pricing page (all 4 items)
        #11 Remove dead Settings link + BYOK code
        #32 Clean up dead BYOK code

Day 5:  #9 Add forgot password flow
        #15-16 Confirm dialogs + error toasts
        #18 Styled delete confirmation

Week 2 — Polish + Landing Page Rewrite
──────────────────────────────────────
Day 1-3: #3 Landing page full rewrite
         #19 Before/after resume examples
         #33-34 New hero + anchored stats

Day 4-5: #21 Skeleton loaders
          #22 Breadcrumbs
          #23 Score polling feedback
          #24 Inline char counter
          #25 Inline company validation
          #26 Role context + Other input
          #29 Footer social links
          #30 ARIA attributes
          #31 Review step error + selector copy
```
