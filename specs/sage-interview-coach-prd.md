# LinkRight Interview Prep — PRD + Solutioning + Architecture
**Agent: Sage** (LinkRight's AI Interview Expert)

**Document type:** Product Requirements Document + Technical Solutioning + System Architecture
**Owner:** Satvik Jain (PM, LinkRight founder)
**Status:** V1 ~90% delivered — see Section 0.1 for live implementation audit
**Last updated:** 2026-05-13 (same-day build)
**Plan version:** v6 (fresh PRD)

---

## 0.1 Implementation Status (2026-05-13 — same-day build audit)

> Live progress audit. Anything marked ✅ has been **verified live**, not just spec'd. ⚠️ = partially built. ❌ = pending. 🔵 = intentionally deferred per PRD scope.

### Skill structure (foundation)
- ✅ Skill directory: `~/.claude/skills/linkright-interview-coach/` — **36 files** across `lib/` `prompts/` `state/` `scripts/`
- ✅ SKILL.md with frontmatter + 9-step workflow — auto-registered by Claude Code
- ✅ README.md with usage examples
- ✅ PRD persisted at `specs/sage-interview-coach-prd.md` (this file)

### lib/ knowledge base (10 files, all written)
- ✅ `sage_persona.md` — character + 8 operating principles + voice mode config (Rishi default)
- ✅ `round_catalogue.md` — 7 rounds × ~30 problem types with budgets, phases, opening Q banks
- ✅ `signal_taxonomy.md` — 3-layer signal game (5 + 6 + 7 dimensions) with Research_Linkright citations
- ✅ `scoring_rubric.md` — 0-5 anchors per dimension + career-level adjustments via signal_weights.yaml
- ✅ `tradeoff_fairness.md` — 3-phase transition model + bridge-narrative bonus + signal-absence floor
- ✅ `av_projection_rubric.md` — text → spoken-time / AI-smell / specificity / fillers / constraints / tradeoffs
- ✅ `patience_escalation.md` — 4-tier rules (🟢/🟡/🟠/🔴) + ramble interrupt
- ✅ `improvement_playbook_template.md` — strongest-possible-version reconstruction format
- ✅ `linkright_integration.md` — read/write contracts with `~/.linkright/`
- ✅ `gemini_handoff_guide.md` — 4-tier voice cascade + Gemini A/V workflow + setup commands

### prompts/ templates (12 files, all written)
- ✅ `round_opener.md` — round announcement + opening Q + clock card
- ✅ `phase_advance.md` — eval + score + next phase Q
- ✅ `nudge_yellow.md`, `interrupt_orange.md`, `cutoff_red.md`, `ramble_cut.md` — patience escalation
- ✅ `final_scorecard_content_only.md` — text-only scorecard at interview end
- ✅ `final_scorecard_holistic.md` — 4-source aggregation after Gemini A/V
- ✅ `gemini_stage1_video.md`, `gemini_stage2_audio.md`, `gemini_stage3_transcript.md` — paste-ready Gemini prompts with locked JSON schemas
- ✅ `av_handoff_instructions.md` — user guide for offline Gemini workflow

### state/ schemas (3 files)
- ✅ `state-schema.json` — runtime state with versioning
- ✅ `gemini-response-schemas.json` — 3-stage validation schemas
- ✅ `sage-voice-config-schema.yaml` — voice config schema with 4-tier cascade

### scripts/ bash helpers (9 files, all chmod +x)
- ✅ `load_profile.sh` — reads `~/.linkright/profile/`, builds candidate-summary.json (⚠️ signal extraction broken — see Bug B1)
- ✅ `roll_problem_type.sh` — `shuf` random PT within round (smoke-tested 3 rolls)
- ✅ `compute_elapsed.sh` — date math (smoke-tested)
- ✅ `render_clock_card.sh` — clock card markdown from state
- ✅ `validate_gemini_response.sh` — JSON schema validation (⚠️ minor stderr leak — Bug B2)
- ✅ `write_interview_history.sh` — persist to `~/.linkright/interview-history/`
- ✅ `kokoro_speak.sh` — 4-tier voice cascade dispatcher (Rishi default; verified live)
- ✅ `gemini_tts.py` — Gemini API native TTS (Tier 4, DISABLED by default)
- ✅ `sage_setup.sh` — one-shot installer (Python deps + Kokoro model + Rishi voice trigger + config writeback)

### Voice mode (TTS) — fully provisioned + verified live
- ✅ Default voice: **Rishi** (en_IN Indian English male, ships free with macOS)
- ✅ Tier cascade: Tier 2 macOS say (Rishi) → Tier 1 kokoro-onnx → Tier 3 pyttsx3 → Tier 4 Gemini (DISABLED)
- ✅ Free-first principle enforced; Tier 4 opt-in only via `gemini.enabled: true`
- ✅ Python deps installed (kokoro-onnx + soundfile + pyttsx3) via pyenv-aware pip
- ✅ Kokoro model files downloaded (310MB onnx + 5.5MB voices.bin)
- ✅ `~/.linkright/sage-voice.yaml` written with Rishi default
- ✅ Live audio playback verified — Sage's greeting played via Rishi successfully
- ✅ HR intro demo played live through Daniel, Samantha, Lekha, Rishi voices (text-mode comparison)
- ⚠️ Tier 1 (kokoro-onnx neural) installed but never played live (T4 below)

### LinkRight ecosystem integration (V1 scope)
- ✅ Profile read: `~/.linkright/profile/` loaded successfully (Satvik's profile: career_level=mid, 18 highlights)
- ✅ Profile fallback paths spec'd: PDF upload / 5-Q conversational capture
- ✅ Interview history write contract: `~/.linkright/interview-history/<ts>.json` + `latest.json` symlink
- ✅ Story bank write contract: `~/.linkright/story-bank/<theme>-<ts>.md` (opt-in only)
- ✅ Voice config: `~/.linkright/sage-voice.yaml` (Rishi default)
- ✅ signal_weights.yaml integration path verified
- 🔵 Setup wizard hook (`linkright setup --sage-voice`) — V1.1 scope; setup script ready, just needs wiring into `setup_wizard.py`

### Smoke tests passed (component-level)
- ✅ `compute_elapsed.sh` — correct math + human formatting
- ✅ `roll_problem_type.sh` — 3 consecutive random rolls (4.4, 4.5, 4.1)
- ✅ `load_profile.sh` — loaded Satvik's profile (basic fields)
- ✅ `validate_gemini_response.sh` — correctly rejects invalid JSON
- ✅ `kokoro_speak.sh` cascade — Tier 2 macOS say wins with Rishi
- ✅ HR intro demos played live through 4 voices

### ❌ V1 scope — pending (ship-blockers)

| ID | Item | Severity | Effort |
|---|---|---|---|
| **B1** | `load_profile.sh` signal extraction returns `top_3_signals: []` — jq query broken | HIGH (personalization promise depends on this) | 30-60 min |
| **B2** | `validate_gemini_response.sh` — jq stderr leaks before clean error | LOW (cosmetic) | 5 min |
| **T1** | Adversarial reviewer dispatch against full skill diff (per global PR Merge Gate rule) | HIGH | 10 min dispatch + variable |
| **T2** | Memory entries save — 9 lessons captured in PRD, not persisted to `~/.claude/projects/.../memory/` | MEDIUM | 15-20 min |
| **T3** | Live E2E test — invoke `/linkright-interview-coach` + complete 1 full mock (HR 15min or Product Sense 30min) | HIGH | 15-45 min |
| **T4** | Tier 1 kokoro-onnx live audio test — proves neural quality on machine | LOW | 2 min |
| **T5** | PRD commit to repo (user approval required per global rule) | LOW | 1 min |

### Top 3 next actions (priority-ordered, pre-E2E)

1. **Fix Bug B1** (`load_profile.sh` signal extraction) — restores personalization promise. Without real top_3_signals, every scorecard's "personalized ceiling" defaults to 4.0 for everyone. Sage's #1 differentiator nullified.
2. **Run adversarial review** (T1) — bug insurance across 36 files. E2E shows happy-path; reviewer surfaces edge cases (e.g., what if user types `/loop` before round pick? What if state file corrupts mid-fire?).
3. **Save memory entries** (T2) — 9 lessons captured in conversation context will be lost on session compaction. Includes Sage persona spec, round+PT architecture, 3-layer signal game, Gemini handoff pattern, pyenv conflict, etc.

After 1-3: T3 (live E2E test). Verdict from E2E feeds the final PRD section.

### 🔵 V1.1+ explicit deferrals (per Section 3)

- G9: Closed-loop `signal_weights.yaml` auto-update from interview outcomes (doc_24)
- G10: Auto-story-bank suggestions from "wins to document" (doc_26)
- G11: `linkright interview coach` CLI command wrapping the skill
- G12: Resume tailoring informed by interview struggles
- Calibration dial (entry / senior / principal / hostile modes; V1 locked Senior PM)
- `linkright setup --sage-voice` wizard subcommand wiring into `setup_wizard.py`
- Cloud TTS implementation (Tier 5 placeholder in config; not built)
- Gemini Tier 4 free-tier live verification + setup wizard prompt to opt-in

### 🔵 V2 explicit deferrals

- G13: Bi-directional voice (Whisper STT for user-spoken answers)
- G14: Multi-language coaching (Hindi-English code-switching at output)
- G15: Live recording integration (no separate Meet step)
- Group / panel interview mode
- Recorded-mock playback with diff-tracking across sessions

---

## 0. Document Conventions

- **PRD-style sections**: Problem → Goals → Personas → Stories → Functional/Non-Functional Reqs → Solutioning → Architecture → Data Model → Integration → Implementation Phases → Success Metrics → Risks → Open Qs → Appendices.
- **Romanized Hindi** for prose narrative where natural. **English** for technical terms, code, schemas, field labels.
- **Calibrated claims**: every external-tool capability mentioned has a `[VERIFIED 2026-05-13]` or `[INFERRED]` tag. Inferred ones flagged for pre-impl verification.

---

## 1. Executive Summary

**Sage** is LinkRight's AI interview expert agent — a multi-modal, signal-aware PM mock-interview coach that personalizes evaluation to the candidate's resume + career level + transition phase.

**Core promise**: After 5-10 Sage sessions, candidate ko apni interview surface understand hoti hai — content, vocal delivery, body language — across HR / behavioral / culture / product sense / analytical / system design / bar raiser rounds. Output is not a score — it's an **actionable improvement playbook** that shows their "strongest possible version" answer.

**Key differentiators**:
1. **3-layer signal scoring** (psychological / PM-craft / executive-presence) backed by `Research_Linkright/` corpus
2. **Tradeoff-fair calibration** via existing `signal_weights.yaml` (career-level × signal matrix)
3. **Multi-modal A/V coaching** via Google Gemini 3 Pro offline handoff (3-stage methodology)
4. **Optional voice mode** via Kokoro local TTS — Sage speaks questions for real-interview feel
5. **LinkRight ecosystem integration** — reads profile, writes history, optionally feeds story bank + signal-weight closed loop
6. **Personalized improvement playbook** — reconstructs "strongest answer YOU could have given" using candidate's actual resume facts

**Out of scope V1**: Live human pairing, group panels, multi-language coaching, real-time STT for voice answers (V2).

---

## 2. Problem Statement

### Real-world pain
PMs targeting FAANG / unicorn roles spend **50-100 hours preparing per cycle** yet 80-90% fail. Failure modes (from `Research_Linkright/failed_hire_rca_methodology.md`):
1. **ATS filter** (resume) — 30%
2. **Resume not compelling** — 20%
3. **Phone screen failed** — 15%
4. **Interview failed** — 25% ← *Sage's primary domain*
5. **Offer failed** (negotiation) — 10%

Interview failure root causes:
- **Signal mismatch** (60%) — candidate optimized for "answer correctness" but interviewer measured psychological safety + trust + believability + executive presence
- **Generic prep tools** (Pramp, IGotAnOffer, Exponent) score against ideal candidate, not personalized to candidate's background
- **No A/V feedback** — practice partners can't analyze body language scientifically; recordings rarely watched
- **No closed loop** — every cycle starts from scratch; no longitudinal learning

### Why LinkRight is uniquely positioned
- **Resume profile already structured** (`~/.linkright/profile/nuggets.jsonl` + `highlights.jsonl`)
- **Signal weights matrix exists** (`signal_weights.yaml` — 13 signals × 5 career levels)
- **Research corpus exists** (47 docs in `Research_Linkright/` on signals + psychology + presence)
- **Roadmap defines closed-loop learning** (`doc_24_closed_loop_learning_system.md`)

Competitors lack all four. Sage is the wedge.

---

## 3. Goals & Non-Goals

### Goals (V1)
- G1: 7 interview rounds × ~30 problem-type variants supported
- G2: Personalized + tradeoff-fair scoring via `signal_weights.yaml`
- G3: Autonomous timer with human-realistic patience escalation
- G4: Multi-modal A/V coaching via Gemini 3 Pro offline handoff (3-stage methodology)
- G5: Optional voice-output mode via Kokoro TTS (Sage speaks)
- G6: Holistic 4-source scorecard + actionable improvement playbook
- G7: LinkRight integration: read profile, write interview history
- G8: Skill packaged at `~/.claude/skills/linkright-interview-coach/`

### Goals (V1.1+, deferred)
- G9: Closed-loop signal_weights auto-update per `doc_24`
- G10: Story bank auto-population from "wins to document" per `doc_26`
- G11: `linkright interview coach` CLI command (skill exposed as CLI)
- G12: Resume tailoring informed by interview struggles

### Goals (V2)
- G13: Bi-directional voice — user speaks answers via Whisper STT
- G14: Multi-language coaching (Hindi-English code-switching, Indian-market interviews)
- G15: Live recording integration (no separate Meet recording needed)

### Non-Goals (V1) — explicit
- Group/panel interview simulation
- Replacing live mock interview platforms (we complement, not replace)
- Generating "perfect answer scripts" for candidate to memorize (anti-pattern per `interview_stories_positioning_guide.md`)
- Hosting interview recordings on third-party (user keeps files locally)

### Non-Goals (Never)
- Coaching candidate to fabricate experience
- Generic "ideal candidate" scoring without personalization
- Auto-uploading user A/V to third parties without explicit consent

---

## 4. User Personas

### Primary: "Mid-PM-Going-Senior" (Satvik archetype)
- 3-6 years PM experience at 1-2 mid-tier companies
- Targeting FAANG / unicorn senior PM roles (Meta E5 / Google L5 / Amazon L6)
- Has structured resume, some metrics, weak FAANG-style storytelling
- Pain: doesn't know which of "content / pace / framework / presence" is the gap
- Need: surface the gap, give actionable drill

### Secondary: "Transition-IC-to-PM"
- 5-10 years IC (engineer / data / design / ops)
- First PM cycle attempt
- Pain: "do I have enough product experience?" anxiety; bridge-narrative weakness
- Need: tradeoff-fair scoring that values transferable signals; bridge-narrative coaching

### Tertiary: "Senior-Going-Principal" (Bar Raiser practice)
- 7+ years PM, 1-2 FAANG already
- Prepping for Principal / Staff / E7 bar raiser
- Pain: high-stakes curveballs; Leadership Principle drilling
- Need: hostile-mode practice with realistic curveballs; LP-tagged scoring

### Quaternary: "Returner / Career-Re-Entrant"
- 1-3 year career gap (parental / sabbatical / health)
- Pain: re-acclimating to PM interview format; explaining the gap
- Need: tradeoff-fair credit for adjacent experience; gap-narrative coaching

---

## 5. User Stories (JTBD format)

### Setup + Mode Selection
- **US1**: As a PM, I want Sage to load my LinkRight profile so I don't re-explain my background every session
- **US2**: As a PM without LinkRight profile, I want to upload my resume PDF OR answer 5 conversational Qs to bootstrap a session profile
- **US3**: As a PM, I want to pick the interview round (HR / Behavioral / Product Sense / etc.) so I can target my weakest area
- **US4**: As a PM, I want Sage to surprise me with a specific problem type within the round so I practice handling unfamiliar prompts
- **US5**: As a PM, I want to choose between text-only mode and voice-output mode so I can opt into immersive real-interview feel when ready

### During Interview
- **US6**: As a PM mid-interview, I want a visible clock card showing phase elapsed + remaining so I can pace myself
- **US7**: As a PM going over budget, I want Sage to nudge me gently first, then interrupt firmly — like a real interviewer
- **US8**: As a PM rambling, I want Sage to cut me off and redirect to next phase
- **US9**: As a PM voice-mode user, I want Sage's questions spoken aloud so I can practice listening + composing oral answers
- **US10**: As a PM, I want Sage to push back on weak assumptions (Senior-PM-level pushback) so my reasoning gets tested

### Post-Interview Content Scorecard
- **US11**: As a PM, I want a content-only scorecard immediately after interview so I see Layer A/B/C signal scores
- **US12**: As a PM, I want my scores calibrated to my personalized ceiling, not generic ideal, so feedback feels fair
- **US13**: As a PM with a transition background, I want bridge-narrative credit applied where applicable so I'm not penalized for absent-by-design signals

### A/V Coaching Handoff (Gemini)
- **US14**: As a PM who recorded my interview on Meet/Loom/phone, I want Sage to give me 3 paste-ready Gemini prompts so I can get body-language + vocal + transcript analysis
- **US15**: As a PM, I want to paste Gemini JSON results back to Sage so it aggregates with content scoring
- **US16**: As a PM with only audio (no video), I want to skip video stage and still get vocal + transcript analysis

### Improvement Playbook + Drills
- **US17**: As a PM, I want a top-3 gap list with my "strongest possible answer" reconstructed using my actual resume facts
- **US18**: As a PM, I want a 30-sec drill per gap I can practice solo
- **US19**: As a PM, I want next-session drill recommendations (specific problem types) so I make progressive overload work

### LinkRight Integration
- **US20**: As a LinkRight user, I want my interview history persisted to `~/.linkright/interview-history/` so I can review trajectory
- **US21**: As a PM with a strong story I told, I want to save it to my story bank for resume tailoring
- **US22 (V1.1+)**: As a LinkRight user, I want my interview outcomes to update signal weights so future resume tailoring reflects what I'm actually demonstrating verbally

---

## 6. Sage Agent Specification

### 6.1 Identity
- **Name**: Sage
- **Role**: LinkRight's interview expert agent
- **Background (in-character)**: Persona of a senior PM who has been on 200+ hiring committees across Meta, Google, Amazon, Stripe, Linear, and Indian unicorns (Razorpay, Cred, Zomato, Swiggy). Specializes in PM craft + signals.
- **Calibration**: senior-PM-bar by default; can dial to entry / principal / hostile via setting

### 6.2 Voice & Tone (personality)
- **Communication style**: Direct + warm + Socratic. Asks "why" before declaring "wrong". Uses Romanized Hindi when natural; English when precision needed.
- **Pushback style**: Names the gap, then asks the candidate to reconsider — doesn't lecture.
- **Praise economy**: Uses praise sparingly; reserves "strong" for genuinely strong answers. Default tone is neutral-curious.
- **Cultural fluency**: Familiar with Indian + US tech market; doesn't assume FAANG = only target.
- **Failure tolerance**: Treats wrong answers as learning surface; never demeans.

### 6.3 Voice Mode (Kokoro TTS) [INFERRED — verify pre-impl]
- **Voice profile**: Calm, deliberate, mid-range pitch, ~140 wpm baseline. Mentor-like.
- **Suggested Kokoro voice ID**: `am_adam` (American English, male, deliberate) — alternates: `am_michael`, `bm_george`. User can pick.
- **Pacing**: 2s pause before asking probing pushbacks; faster cadence for follow-ups.
- **Tone modulation**: Slight pitch drop at sentence end (authority signal); deliberate emphasis on key nouns.

### 6.4 Operating Principles (Sage's worldview)
1. **Signal > correctness**: Score the signal sent, not the surface answer.
2. **Personalized ceiling > generic ideal**: Every score is calibrated to candidate's max plausible.
3. **Tradeoff-fair**: Missing X is OK if Y is strong. Transition phase matters.
4. **Specificity density = authenticity** (2026-era signal vs AI-smell).
5. **Pushback to elicit thinking, not to defeat**: Socratic, not adversarial.
6. **Time discipline is part of the test**: Real interviewers pace you.
7. **Improvement playbook > score**: User leaves with a drill plan, not a number.
8. **Privacy first**: A/V files stay local; user runs Gemini on their own.

### 6.5 Operating Modes
| Mode | Description | When to use |
|---|---|---|
| **text-only** | All Sage interactions via text; clock card refreshes every 90s | Default; lowest setup friction |
| **voice-output** | Sage's questions spoken via Kokoro TTS; user types answers | Real-interview feel; auditory practice |
| **voice-bi-directional** (V2) | Sage speaks + user speaks; Whisper STT transcribes user | Most immersive; V2 scope |
| **silent-grading** (V2) | User uploads recorded interview from elsewhere; Sage only grades | Post-hoc analysis |

---

## 7. Functional Requirements

### FR1 — Profile Intake
- FR1.1: Skill MUST attempt to load `~/.linkright/profile/metadata.yaml`
- FR1.2: If profile exists, build `candidate-summary.json` with career_level, top_3_signals, absent_signals, transition_phase, domain_arc, story_inventory
- FR1.3: If profile absent, MUST offer: (a) upload resume PDF OR (b) 5-Q conversational capture
- FR1.4: PDF upload MUST use `markitdown` or `pypdf` to extract text; MUST NOT block on parse errors (degrade to 5-Q)

### FR2 — Round Selection (USER-PICKED)
- FR2.1: Skill MUST present `AskUserQuestion` with 7 round options + descriptions + duration ranges
- FR2.2: User picks ONE round; selection is final for the session

### FR3 — Problem Type Roll (RANDOM)
- FR3.1: Within picked round, skill MUST randomly select 1 problem type via `shuf -i 1-N -n 1`
- FR3.2: Roll MUST be announced openly (user sees the dice)
- FR3.3: Problem type determines: duration, phase structure, opening Q

### FR4 — Voice Mode Selection
- FR4.1: After round + PT roll, skill MUST ask user: text-only OR voice-output
- FR4.2: If voice-output AND Kokoro not installed: prompt install one-liner OR fallback to text-only
- FR4.3: User can toggle mid-session via `/voice on|off` (V1.1)

### FR5 — State Initialization
- FR5.1: Write `/tmp/mock-interview-state-<uuid>.json` per state-schema.json
- FR5.2: Schema MUST be versioned (e.g., `"schema_version": "1.0"`)
- FR5.3: State file MUST survive context compaction

### FR6 — Timer Mechanism
- FR6.1: User MUST type `/loop` to enable autonomous timer
- FR6.2: Each fire MUST happen every 90s via `ScheduleWakeup(delaySeconds=90)`
- FR6.3: Each fire MUST: read state, compute elapsed, decide tier, render clock card, take action, update state, schedule next
- FR6.4: Skill MUST handle context compaction by re-reading state from disk on each fire

### FR7 — Clock Card Rendering
- FR7.1: Clock card MUST appear at start of each interviewer turn
- FR7.2: Must show: round/PT, phase index, start time, soft cutoff, hard cutoff, now, elapsed, remaining, total elapsed, tier badge
- FR7.3: Tier badge: 🟢 GREEN / 🟡 YELLOW / 🟠 ORANGE / 🔴 RED

### FR8 — Patience Escalation
- FR8.1: 🟢 elapsed ≤ budget → patient pushback
- FR8.2: 🟡 budget < elapsed ≤ budget+60s → gentle nudge appended
- FR8.3: 🟠 budget+60 < elapsed ≤ budget+180s → mild interrupt + skip pushback + advance
- FR8.4: 🔴 elapsed > budget+180s → hard cutoff + log + advance
- FR8.5: Ramble interrupt (length-based): reply > 350 words → first 1-2 points only + redirect

### FR9 — In-Session Scoring (Content)
- FR9.1: Each phase scored on Layer A (5 dims), Layer B (6 dims), Layer C (Cognitive Clarity, Pressure Mgmt, Interruption Handling — text-derivable subset)
- FR9.2: Each score weighted by `signal_weights[dim][career_level]`
- FR9.3: Tradeoff-fair adjustments applied (transition-phase floor, top-signal bonus)
- FR9.4: Per-phase A/V projection metrics computed (word count, AI-smell, specificity, fillers-as-written, constraint mentions, tradeoff mentions)

### FR10 — Voice Output (Kokoro)
- FR10.1: If voice-output mode, Sage's question text MUST be piped through Kokoro to generate WAV
- FR10.2: Audio MUST play via `afplay` (macOS) / `aplay` (Linux) — platform-aware
- FR10.3: User can press Enter or type to skip current audio
- FR10.4: Voice profile MUST be configurable via `~/.linkright/sage-voice.yaml`

### FR11 — Content-Only Final Scorecard
- FR11.1: At interview end, render content-only scorecard with Layer A/B/C scores + time discipline + improvement playbook (text-derived)
- FR11.2: Offer A/V coaching: Yes / No / Later

### FR12 — A/V Coaching Handoff (Gemini)
- FR12.1: If Yes, display Stage 1 (video) Gemini prompt with `{{session_id}}` pre-filled
- FR12.2: Provide step-by-step instructions: "Open gemini.google.com → upload .mp4 → paste prompt → run → copy JSON"
- FR12.3: User pastes Stage 1 JSON → validate via schema → on success, advance to Stage 2
- FR12.4: Repeat for Stage 2 (audio) and Stage 3 (transcript)
- FR12.5: Allow partial submission (skip stages user didn't run)
- FR12.6: All 3 prompts MUST target Gemini 3 Pro or Gemini 3.1 Pro (latest as of impl); prompts MUST instruct "if unable to confidently identify a signal, set field to null"

### FR13 — Holistic Scorecard
- FR13.1: After all A/V stages received (or skipped), render holistic scorecard with 4-source matrix (Content / Video / Audio / Transcript)
- FR13.2: Cross-source agreement = strong signal; disagreement flagged as informative
- FR13.3: Improvement playbook MUST reconstruct "strongest possible version" using candidate's actual profile facts
- FR13.4: Verdict: STRONG HIRE / HIRE / LEAN HIRE / NO HIRE / STRONG NO calibrated to difficulty bar

### FR14 — LinkRight Integration (V1)
- FR14.1: Write final scorecard to `~/.linkright/interview-history/<ts>.json`
- FR14.2: Update `~/.linkright/interview-history/latest.json` symlink
- FR14.3: If user says "save this story", write `~/.linkright/story-bank/<theme>.md` with STAR fields
- FR14.4: All writes append-only; never overwrite

### FR15 — Drill Recommendations
- FR15.1: End of interview, present top-3 next-session drill recommendations
- FR15.2: Recommendations MUST specify: round + problem type + target metric (e.g., "Run Round 4 PT 4.3 — target Layer B Strategy ≥ 3.5")

### FR16 — Privacy + Consent
- FR16.1: Skill MUST NOT auto-upload any A/V file
- FR16.2: Story bank entries written ONLY on explicit user consent per entry
- FR16.3: Profile data read-only; never modified by skill

---

## 8. Non-Functional Requirements

| NFR | Target | Rationale |
|---|---|---|
| NFR1 — Latency (clock fire) | < 5s per fire to render | Maintains real-time feel |
| NFR2 — Kokoro voice synthesis | < 2s per question text → audio | Avoids awkward silence |
| NFR3 — Token budget per interview | ≤ 40K tokens for 45-min interview | Cost-aware; user can complete without sub burn |
| NFR4 — Offline-friendly | All scoring + Kokoro local | Works without internet for content+voice modes |
| NFR5 — A/V handoff requires internet | Gemini call user-side | Acceptable — explicit out-of-Claude step |
| NFR6 — Privacy | A/V files stay local | User keeps full control |
| NFR7 — Reproducibility | Same profile + same Q → similar score | Deterministic where possible |
| NFR8 — Cross-platform | macOS + Linux | Windows not in scope V1 |
| NFR9 — Recovery from interruption | State file → resume mid-interview | `linkright resume-interview <session>` |
| NFR10 — Skill load time | < 3s | Fast invocation |

---

## 9. Solutioning / Approach

### 9.1 Core stack
```
┌─────────────────────────────────────────────────────────────┐
│                        SAGE (Skill)                          │
│  ~/.claude/skills/linkright-interview-coach/                 │
│                                                              │
│  Workflow Layer: SKILL.md + workflow steps                   │
│  Prompt Layer: 13 prompt templates (in-session + Gemini)     │
│  Scoring Layer: signal_weights.yaml + 3-layer rubric         │
│  State Layer: /tmp/mock-interview-state-<uuid>.json          │
└────────────┬─────────────────┬────────────────┬──────────────┘
             │                 │                │
             ▼                 ▼                ▼
    ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
    │ /loop +        │ │ Kokoro TTS   │ │ Gemini 3 Pro   │
    │ ScheduleWakeup │ │ (local)      │ │ (user-side)    │
    │ (Claude        │ │              │ │                │
    │ Code           │ │ Voice output │ │ Video/Audio/   │
    │ harness)       │ │ for Sage     │ │ Transcript     │
    └────────────────┘ └──────────────┘ └────────────────┘
             │                 │                │
             ▼                 ▼                ▼
    ┌─────────────────────────────────────────────────────┐
    │           LinkRight Profile + Ecosystem             │
    │  ~/.linkright/profile/         (read)                │
    │  ~/.linkright/interview-history/  (write)            │
    │  ~/.linkright/story-bank/       (write, opt-in)      │
    │  signal_weights.yaml           (read)                │
    └─────────────────────────────────────────────────────┘
```

### 9.2 Timer mechanism (validated)
- **Primary**: `/loop` (self-paced) + `ScheduleWakeup(delaySeconds=90)`
- **Fallback**: `/loop 90s` (fixed interval)
- **Precision boundary** (optional V1.2): `CronCreate` for hard phase-end fires

### 9.3 Voice synthesis (Kokoro) [INFERRED — verify model availability + install path pre-impl]
- **Model**: kokoro-82M (open-source, ~330MB)
- **Install**: `pip install kokoro` OR Docker image
- **Invocation**: `kokoro-cli --voice am_adam --text "..." --output question.wav`
- **Playback**: `afplay question.wav` (macOS) | `aplay question.wav` (Linux)
- **Fallback if Kokoro unavailable**: `pyttsx3` (lower quality but built-in)
- **Setup**: skill first-run prompts user to install Kokoro; provides one-liner
- **Voice config**: `~/.linkright/sage-voice.yaml` — voice_id, speed, pitch

### 9.4 Gemini 3 Pro A/V analysis (user-side offline)
- **Model**: Gemini 3 Pro or Gemini 3.1 Pro (user picks latest)
- **Interface**: gemini.google.com/app (web) OR API (advanced users)
- **3 stages** (locked JSON output schema):
  - Stage 1: Video-only (visual presence)
  - Stage 2: Audio-only (vocal delivery)
  - Stage 3: Transcript-only (narrative content)
- **Handoff**: skill emits prompt with `{{session_id}}` → user runs → JSON back → skill validates + aggregates
- **Rationale for offline**: Claude can't process A/V; Gemini can. User keeps file local. Decoupled architecture.

### 9.5 Personalized scoring engine
- Read `signal_weights.yaml` per candidate's career level
- Per-dimension: raw_score × weight, then tradeoff-fair adjustments
- Personalized ceiling shown alongside raw score
- Bridge-narrative bonus for transition phases 1-2
- Top-signal demonstration bonus (×1.2 cap 5.0)

### 9.6 Improvement playbook generation
- For each top-3 gap:
  - Quote user's actual answer phrase
  - Use candidate's profile facts to reconstruct "strongest possible version"
  - Provide 30-sec drill
  - Suggest story-bank entry candidate
  - Expected lift on Layer A/B/C scores

---

## 10. System Architecture

### 10.1 Component diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                          USER (PM candidate)                        │
└──────┬───────────────────────────────────────────────┬─────────────┘
       │ chat                                          │ A/V file
       │                                               │ + Gemini run
       ▼                                               ▼
┌─────────────────┐                            ┌──────────────────┐
│  Claude Code    │                            │ Google Gemini    │
│  Session        │                            │ 3 Pro / 3.1 Pro  │
│                 │                            │ (gemini.google.  │
│  ┌───────────┐  │                            │  com)            │
│  │   SAGE    │  │   ────  Gemini prompts ─►  │                  │
│  │  (Skill)  │  │                            │  3 Stages:       │
│  └─────┬─────┘  │   ◄──── JSON results ────  │  Video / Audio   │
│        │        │                            │  / Transcript    │
│        │        │                            └──────────────────┘
│        │ /loop  │
│        │ +      │
│        │ Wakeup │
│        │        │
│        ▼        │
│  ┌───────────┐  │     ┌──────────────────┐
│  │  State    │◄─┼────►│  /tmp/mock-      │
│  │  file ops │  │     │  interview-      │
│  └───────────┘  │     │  state-<uuid>    │
│        │        │     └──────────────────┘
│        │        │
│        ▼        │
│  ┌───────────┐  │     ┌──────────────────┐
│  │  Kokoro   │──┼────►│  ~/.kokoro/      │
│  │  TTS      │  │     │  (model cache)   │
│  │  (local)  │  │     └──────────────────┘
│  └─────┬─────┘  │              │
│        │ WAV    │              │
│        ▼        │              │
│  ┌───────────┐  │              ▼
│  │  afplay   │──┼─────► (speakers — Sage's voice)
│  │  / aplay  │  │
│  └───────────┘  │
│                 │
│  ┌───────────┐  │     ┌──────────────────────────────┐
│  │ LinkRight │◄─┼────►│  ~/.linkright/               │
│  │ I/O       │  │     │   profile/      (read)        │
│  │           │  │     │   interview-history/ (write)  │
│  │           │  │     │   story-bank/   (write, opt)  │
│  └───────────┘  │     │   sage-voice.yaml (read)      │
└─────────────────┘     └──────────────────────────────┘
```

### 10.2 Sequence diagram — One full Sage session (text-only)

```
USER         SAGE            STATE FILE      LINKRIGHT       /loop+Wake
  │             │                │              │                │
  │─ invoke ───►│                │              │                │
  │             │                │              │                │
  │             │── load profile ──────────────►│                │
  │             │◄──── candidate-summary ───────│                │
  │             │                │              │                │
  │◄─ Q: pick   │                │              │                │
  │   round ───►│                │              │                │
  │  "4. Product│                │              │                │
  │   Sense"    │                │              │                │
  │             │── roll PT ─────│              │                │
  │             │  (shuf 1-5)    │              │                │
  │             │  → PT 4.3      │              │                │
  │◄─ announce  │                │              │                │
  │   PT + dur ─┤                │              │                │
  │             │── init state ─►│              │                │
  │◄─ Phase 1 Q │                │              │                │
  │   + clock   │                │              │                │
  │   card      │                │              │                │
  │             │                │              │                │
  │── /loop ───►│                │              │                │
  │             │── ScheduleWakeup(90) ─────────────────────────►│
  │             │                │              │                │
  │── reply ───►│                │              │                │
  │             │── eval reply ──│              │                │
  │             │  + score       │              │                │
  │             │── update state►│              │                │
  │             │                │              │                │
  │  [90s fire] │                │              │                │
  │             │◄─ fire ─────────────────────────────────────── │
  │             │── read state ◄─│              │                │
  │             │── compute tier │              │                │
  │             │  (🟢 green)    │              │                │
  │◄─ clock     │                │              │                │
  │   refresh   │                │              │                │
  │             │── Wakeup(90) ─────────────────────────────────►│
  │             │                │              │                │
  │  ...phases continue...                                       │
  │             │                │              │                │
  │  [final phase end]                                            │
  │             │                │              │                │
  │◄─ content   │                │              │                │
  │   scorecard │                │              │                │
  │◄─ "A/V?"    │                │              │                │
  │             │                │              │                │
  │── "Yes" ───►│                │              │                │
  │◄─ Stage 1   │                │              │                │
  │   Gemini    │                │              │                │
  │   prompt    │                │              │                │
  │             │                │              │                │
  │  [USER GOES TO gemini.google.com, RUNS PROMPT]                │
  │             │                │              │                │
  │── paste     │                │              │                │
  │   JSON ────►│                │              │                │
  │             │── validate     │              │                │
  │             │  schema        │              │                │
  │◄─ Stage 2   │                │              │                │
  │   prompt    │                │              │                │
  │  ...(repeat for Stage 3)...                                  │
  │             │                │              │                │
  │             │── aggregate    │              │                │
  │             │  4 sources     │              │                │
  │◄─ holistic  │                │              │                │
  │   scorecard │                │              │                │
  │◄─ playbook  │                │              │                │
  │             │                │              │                │
  │             │── write hist ─────────────────►│                │
  │             │                │              │                │
  │◄─ "save     │                │              │                │
  │   story?"   │                │              │                │
  │── "Yes" ───►│                │              │                │
  │             │── write story ────────────────►│                │
  │             │                │              │                │
  │◄─ drill     │                │              │                │
  │   recs +    │                │              │                │
  │   end       │                │              │                │
```

---

## 11. Data Model

### 11.1 candidate-summary.json (built from LinkRight profile)
```json
{
  "schema_version": "1.0",
  "career_level": "mid|fresher|early_career|senior|executive",
  "transition_phase": 1|2|3|null,
  "domain_arc": "string (e.g., 'data-analyst→PM')",
  "top_3_signals": ["data-driven", "user-empathy", "build-execution"],
  "absent_signals": ["revenue-impact-scale", "executive-influence"],
  "story_inventory": [
    {"theme": "leadership", "summary": "...", "metrics": {...}, "source_bullet": "..."}
  ],
  "personalized_ceilings": {
    "product_sense": 4.2, "execution": 4.5, "strategy": 3.8, ...
  }
}
```

### 11.2 state-schema.json
```json
{
  "schema_version": "1.0",
  "session_id": "<uuid>",
  "candidate": { ... candidate-summary ... },
  "round": {
    "id": 4, "name": "Product Sense",
    "problem_type": {"id": "4.3", "name": "Design X for Y"},
    "question": "Design WhatsApp for senior citizens in tier-2 cities",
    "budget_seconds": 2700,
    "difficulty_bar": "Senior PM (E5/L5)"
  },
  "mode": {
    "voice_output": true,
    "voice_profile": "am_adam",
    "voice_speed": 1.0,
    "tts_engine": "kokoro|pyttsx3"
  },
  "timing": {
    "interview_start_ts": 1747142400,
    "current_phase_idx": 3,
    "phases": [
      {"name": "Clarify", "budget_s": 300, "start_ts": 1747142400, "end_ts": 1747142680, "status": "done"}
    ],
    "patience_tier": "green|yellow|orange|red",
    "last_user_msg_ts": 1747143200,
    "last_fire_ts": 1747143290
  },
  "scoring_content": {
    "Phase1": {
      "layer_a": {"safety": 4, "friction": 3, ...},
      "layer_b": {"product_sense": 4, ...},
      "layer_c": {"cognitive_clarity": 4, "pressure_management": 3, ...},
      "av_projection": {"spoken_time_s": 120, "ai_smell": 0.02, "specificity": 0.18, "fillers": 0.01, "constraints_named": 2, "tradeoffs_named": 1},
      "personalized_ceiling": 4.2,
      "weighted_score": 3.8,
      "tradeoff_credits": ["..."],
      "notes": ["..."]
    }
  },
  "scoring_gemini": {
    "stage1_video": null,
    "stage2_audio": null,
    "stage3_transcript": null,
    "received_ts": {"stage1": null, "stage2": null, "stage3": null}
  },
  "behavior_log": {
    "ramble_count": 0,
    "hard_cutoffs": 0,
    "yellow_nudges": 1,
    "orange_interrupts": 0,
    "stories_saved": []
  },
  "verdict": null,
  "improvement_playbook": null
}
```

### 11.3 Gemini Stage 1/2/3 response schemas
Locked JSON shape per stage (see Appendix E for full prompts).

### 11.4 ~/.linkright/interview-history/<ts>.json
```json
{
  "session_id": "<uuid>",
  "timestamp": "2026-05-13T14:32:18Z",
  "round": "Product Sense",
  "problem_type": "Design X for Y",
  "question": "...",
  "candidate_snapshot": { ... candidate-summary at session time ... },
  "scorecard": {
    "layer_a": {...}, "layer_b": {...}, "layer_c": {...},
    "av_metrics": {...},
    "verdict": "HIRE",
    "personalized_overall": "13.2 / 15"
  },
  "playbook": {
    "top_gaps": [...], "drill_recommendations": [...]
  },
  "gemini_av_attached": true|false,
  "duration_seconds": 2734,
  "behavior_log": {...}
}
```

### 11.5 ~/.linkright/story-bank/<theme>.md (per saved story)
```markdown
---
theme: leadership-without-authority
created: 2026-05-13
source_session: <uuid>
career_level_at_capture: mid
metrics:
  impact_metric: "30% reduction in onboarding time"
  scale_metric: "team of 8"
linked_resume_bullet: "Led cross-functional onboarding redesign..."
---

## Situation
...

## Task
...

## Action
...

## Result
...

## Reflection / Learning
...

## Adaptable to question types
- Leadership without authority
- Conflict resolution
- Influence
```

---

## 12. Integration Points

### 12.1 LinkRight profile read (V1)
- Path: `~/.linkright/profile/`
- Files: `metadata.yaml`, `nuggets.jsonl`, `highlights.jsonl`, `embeddings.npz` (optional for semantic match)
- Read-only contract; Sage never modifies

### 12.2 LinkRight signal_weights read (V1)
- Path: `context/cli/linkright/src/linkright/resume/data/signal_weights.yaml`
- 13 signals × 5 career levels matrix
- Used for: ceiling computation, tradeoff-fair adjustment

### 12.3 LinkRight interview history write (V1)
- Path: `~/.linkright/interview-history/<ts>.json`
- Append-only; never overwrite
- Symlink: `~/.linkright/interview-history/latest.json`

### 12.4 LinkRight story bank write (V1, opt-in)
- Path: `~/.linkright/story-bank/<theme>-<ts>.md`
- Triggered only on explicit user "save this story"

### 12.5 Kokoro TTS invocation (V1, optional)
- Binary/CLI: `kokoro` or `python -m kokoro`
- Voice config: `~/.linkright/sage-voice.yaml`
- Fallback: `pyttsx3` if Kokoro absent

### 12.6 Gemini handoff (V1)
- No programmatic integration; user-side workflow
- Sage emits paste-ready prompt with session metadata
- User pastes JSON back; Sage validates via schema

### 12.7 /loop + ScheduleWakeup (V1)
- Claude Code harness primitive
- User invokes `/loop` once at clock-start
- Sage schedules each next fire (90s default)

### 12.8 LinkRight CLI exposure (V1.1)
- Future: `linkright interview coach` → wraps Sage skill
- Roadmap doc_08 (CLI runtime layer) describes CLI primitive contract

### 12.9 Closed-loop signal_weights update (V1.1)
- Interview history events → roll up into per-candidate signal_weights deltas
- Spec'd per `doc_24_closed_loop_learning_system.md`

---

## 13. API / Interface Specifications

### 13.1 Skill invocation triggers
- Direct: `/linkright-interview-coach`
- Aliases (from SKILL.md frontmatter):
  - "mock interview"
  - "practice PM interview"
  - "interview coach"
  - "Sage"
  - "FAANG mock"
  - "bar raiser practice"

### 13.2 Mid-session commands (V1)
| Command | Effect |
|---|---|
| `/loop` | Enable autonomous timer |
| `stop` | End interview, jump to scorecard |
| `skip phase` | Force phase advance (counts as cutoff in scorecard) |
| `pause` | Pause clock (V1.1) |
| `/voice on\|off` | Toggle voice mode mid-session (V1.1) |
| `explain score X` | Sage explains a phase's score |
| `save story` | Triggers story bank save flow |

### 13.3 Bash script signatures
| Script | Input | Output |
|---|---|---|
| `load_profile.sh` | none | `candidate-summary.json` on stdout |
| `roll_problem_type.sh <round_id>` | round_id 1-7 | `{"pt_id": "4.3", "name": "Design X for Y", "budget_s": 2700}` |
| `compute_elapsed.sh <start_ts>` | unix timestamp | elapsed seconds |
| `render_clock_card.sh <state_file>` | state path | markdown clock card |
| `validate_gemini_response.sh <stage> <json_file>` | stage 1/2/3 + JSON path | exit 0 + parsed; exit 1 + errors |
| `write_interview_history.sh <state_file>` | state path | history file path |
| `kokoro_speak.sh <text> <voice_id>` | text + voice | WAV file path |

### 13.4 AskUserQuestion flows
- Round selection (7 options + descriptions)
- Voice mode (text-only / voice-output)
- A/V coaching offer (Yes / No / Later)
- Story save (per strong answer)
- Drill drill mode (drill weakest phase / try new round / end)

---

## 14. Implementation Phases

### Phase 1 — Skill skeleton + research-grounded libraries (Day 1-2)
- Create `~/.claude/skills/linkright-interview-coach/`
- Write `SKILL.md` with full frontmatter + 9-step workflow
- Write `README.md` with usage examples
- Write `lib/round_catalogue.md` (7 rounds × ~30 PTs with budgets, phases, opening Q banks)
- Write `lib/signal_taxonomy.md` (3-layer game with `Research_Linkright/` file:line citations)
- Write `lib/scoring_rubric.md` (0-5 anchors per dimension + career adjustments)
- Write `lib/tradeoff_fairness.md` (transition phase rules)
- Write `lib/av_projection_rubric.md` (in-session text projection)
- Write `lib/patience_escalation.md` (4-tier rules + ramble interrupt)
- Write `lib/improvement_playbook_template.md`
- Write `lib/linkright_integration.md`
- Write `lib/gemini_handoff_guide.md`
- Write `lib/sage_persona.md` (in-character spec)

### Phase 2 — Prompts library (Day 3-4)
- 7 in-session prompts (opener, phase-advance, escalations, ramble cut, final scorecard content-only, holistic scorecard)
- 3 Gemini prompts (Stage 1 video, Stage 2 audio, Stage 3 transcript) — paste-ready
- A/V handoff instructions for user
- Sage greeting template
- Voice-mode greeting variant

### Phase 3 — State + schemas (Day 5)
- `state/state-schema.json`
- `state/gemini-response-schemas.json` (3 stage schemas)
- Validation helpers

### Phase 4 — Helper scripts (Day 6-7)
- 6 bash scripts (load_profile, roll_problem_type, compute_elapsed, render_clock_card, validate_gemini, write_interview_history)
- `kokoro_speak.sh` with pyttsx3 fallback
- All scripts idempotent + safe to re-run

### Phase 5 — Kokoro voice mode integration (Day 8-9)
- Verify Kokoro install path + CLI [pre-impl verification step]
- Wire Sage's Q-rendering through `kokoro_speak.sh` when voice mode on
- Test playback on macOS via `afplay`
- Configure `~/.linkright/sage-voice.yaml` default

### Phase 6 — Gemini handoff (Day 10)
- Test 3 stage prompts on real Gemini 3 Pro [pre-impl verification — confirm model availability + UI flow]
- Iterate on JSON output format until stable
- Document user workflow in `lib/gemini_handoff_guide.md`

### Phase 7 — LinkRight integration (Day 11-12)
- Verify `~/.linkright/profile/` read path works for both fresh + populated profiles
- Test interview history write
- Test story bank write with sample story
- Ensure all writes append-only

### Phase 8 — Manual E2E QA (Day 13)
- Run 3 full sessions across 3 round types (HR, Product Sense PT 4.3, System Design)
- Verify clock fires, tier escalation, ramble interrupt
- Record 1 video, run through Gemini, paste back, verify aggregation
- Test profile-missing path (PDF upload + 5-Q fallback)

### Phase 9 — Adversarial review (Day 14)
- Dispatch `adversarial-reviewer` against full skill diff (per global PR Merge Gate rule)
- Address all BLOCK items; loop until SIGN OFF

### Phase 10 — Ship (Day 15)
- bd create + close
- Commit + push (skill lives in `~/.claude/skills/` — separate from repo, but distributable spec lives in repo `specs/sage-prd.md`)
- Save memory entries
- Optional: PR a copy into `~/Documents/linkright_production/specs/sage-prd.md` for spec versioning

---

## 15. Success Metrics

### Leading indicators (first month post-launch)
- M1: Sessions completed per user / week (target: 2+)
- M2: A/V mode adoption rate (target: 30%+)
- M3: Voice-output mode adoption (target: 20%+)
- M4: Drill recommendation acceptance (user runs recommended next session): target 50%+
- M5: Story bank entries per user (target: 3+ in first month)

### Lagging indicators (3+ months)
- M6: User self-reported "this improved my actual interview outcome": qual survey
- M7: Score delta over 5+ sessions: avg Layer C improvement +0.5
- M8: AI-smell density reduction over sessions: avg -30%
- M9: Time-discipline improvement: hard cutoff rate decline

### North Star
- M10: % of users who report Sage-coached interviews resulted in offer → target: surface in retrospective survey at 3-month mark

---

## 16. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Kokoro install friction | Med | Med | Bundle one-liner install; fallback to `pyttsx3`; voice mode optional |
| Gemini 3 Pro UI changes break prompts | Med | Med | Schema-based validation catches breakage; user reports surface in lib/gemini_handoff_guide.md updates |
| Gemini response invalid JSON | High | Low | Validate via schema; retry with stricter prompt; allow partial submission |
| User has no video recording | High | Low | Skip Stage 1; still process Stage 2 audio + Stage 3 transcript |
| User has no recording at all | High | Low | Content-only scorecard is complete by itself |
| /loop not initiated | Med | Med | Skill refuses to start clock; explicit instruction to user |
| Context compaction mid-interview | High | Low | State file in `/tmp` is source of truth; re-read on each fire |
| ~/.linkright not present | High | Low | Fallback to PDF upload OR 5-Q conversational; write to `~/.claude/interview-history/` if dir missing |
| Hallucination in score reconstruction | Med | High | "Strongest possible version" anchored to specific profile facts (nuggets.jsonl); never invents experience |
| User-uploaded A/V leak via Gemini | Med | Med | Skill explicitly instructs: "Gemini stores conversation; review their data policy. Use Gemini account you control." |
| Cost (Gemini-side) | Low | Low | Free tier covers typical use; user controls usage |
| Score gaming (user feeds Sage perfect answers from past sessions) | Low | Low | Each session question is rolled fresh; gaming costs more effort than legit practice |
| Skill becomes dependency for LinkRight CLI but lives in `~/.claude/skills/` | Med | Med | V1: copy spec to repo `specs/sage-prd.md`; V1.1: vendorize skill into LinkRight CLI package |

---

## 17. Open Questions

| OQ | Question | Owner | Resolution path |
|---|---|---|---|
| OQ1 | Exact Gemini 3 Pro vs 3.1 Pro feature delta — which one for V1? | Satvik | Test both pre-impl; pick based on JSON adherence quality |
| OQ2 | Kokoro CLI binary path on macOS — bundled or installed via pip? | Impl team | Verify Day 1 of Phase 5 |
| OQ3 | Should V1 include Whisper STT for user-spoken answers? | Satvik | Defer to V2 unless trivial setup found |
| OQ4 | Should Sage have multiple voice profiles (different "interviewer personas")? | Satvik | V1 ships with 1 profile; V2 adds 3-5 (warm / clinical / hostile / bar-raiser) |
| OQ5 | Multi-language support timeline | Satvik | V2; defer until V1 stable |
| OQ6 | Should scorecard be shareable (export to PDF / Notion)? | Satvik | V1.1; low priority |
| OQ7 | Should skill auto-update signal_weights.yaml or require user approval? | Satvik | V1.1 — require approval (per global rule "confirm before mutating LinkRight artifacts") |
| OQ8 | How to handle session resume after laptop sleep? | Impl team | State file in `/tmp` is durable; on next invocation, scan for in-progress sessions and offer resume |
| OQ9 | Storage location for Sage skill — `~/.claude/skills/` vs vendored inside LinkRight | Satvik | V1: `~/.claude/skills/`; spec in repo for versioning |
| OQ10 | Bar-raiser hostility level dial | Satvik | V1 fixed at Senior PM bar; V1.1 adds dial (entry / senior / principal / hostile) |

---

## 18. Appendices

### Appendix A — Research_Linkright cite list (mandatory reading for impl)
- `interview_psychology_and_decision_influence_system.md` — 5-layer psychological model
- `executive_presence_and_behavioral_signaling_system.md` — 7-dim presence framework + remote behavior
- `product_manager_case_interview_master_system.md` — 6 PM eval categories + case structure
- `interview_stories_positioning_guide.md` — STAR + story-bank design
- `interview_tone_positioning_guide.md` — tone calibration by company type
- `interview_intro_positioning_guide.md` — opening structure + first-impression power
- `cross_domain_career_transitions_guide.md` — 3-phase transition fairness
- `ai_era_authenticity_and_human_signal_guide.md` — specificity density / AI-smell
- `jd_intelligence_and_signal_mapping_system.md` — JD decoding + 7 PM archetypes
- `failed_hire_rca_methodology.md` — 5 failure modes

### Appendix B — Roadmap_Linkright cite list
- `doc_12_career_navigation_intelligence_long_term_compounding_system.md` — interview intelligence + compounding
- `doc_24_closed_loop_learning_system.md` — outcome tracking + signal weight updates
- `doc_26_personal_operating_rhythm.md` — weekly review feeding story bank
- `doc_18_evaluation_framework.md` — quality metrics
- `doc_29_trust_privacy_governance.md` — privacy approach
- `doc_08_cli_runtime_mcp_execution_layer.md` — CLI exposure plan (V1.1)

### Appendix C — signal_weights.yaml reference
Located: `context/cli/linkright/src/linkright/resume/data/signal_weights.yaml`
Schema: 13 signals × 5 career levels (executive / senior / mid / early_career / fresher)
Used by Sage for: ceiling computation + tradeoff-fair adjustment.

### Appendix D — Round + Problem Type catalogue (summary; full in lib/round_catalogue.md)
7 rounds × ~30 problem types total. User picks round → skill rolls PT → PT determines budget + phase structure + opening Q bank.

### Appendix E — Gemini Stage 1/2/3 prompt drafts
(Same as v5 plan — paste-ready prompts with {{session_id}} placeholders, locked JSON output schemas. Will live at `prompts/gemini_stage{1,2,3}.md`.)

### Appendix F — Kokoro CLI reference [INFERRED — verify pre-impl]
- Install: `pip install kokoro-tts` OR `pip install kokoro`
- Voice IDs (English male): `am_adam`, `am_michael`, `bm_george`
- Voice IDs (English female): `bf_emma`, `af_sky`, `am_sarah`
- Sample command: `kokoro-cli --voice am_adam --text "..." --output q.wav --speed 1.0`
- Playback: `afplay q.wav` (macOS) | `aplay q.wav` (Linux)

### Appendix G — SKILL.md frontmatter draft
```markdown
---
name: linkright-interview-coach
description: |
  Sage — LinkRight's AI interview expert. FAANG-grade PM mock interview coach with personalized signal-aware evaluation, multi-modal A/V coaching via Google Gemini 3 Pro offline handoff, optional voice mode via Kokoro TTS, autonomous timer, and actionable improvement playbook. User picks ROUND (HR/Behavioral/Culture/Product Sense/Analytical/System Design/Bar Raiser); skill rolls PROBLEM TYPE within. Pulls profile from LinkRight (~/.linkright/profile/). Tradeoff-fair scoring via signal_weights.yaml. LinkRight-integrated: writes interview-history, optionally appends story-bank. Triggers: /linkright-interview-coach, "mock interview", "practice interview", "Sage", "FAANG mock", "bar raiser practice".
triggers:
  - /linkright-interview-coach
  - mock interview
  - practice interview
  - PM interview practice
  - FAANG mock
  - bar raiser practice
  - Sage
  - interview coach
---
```

---

## 19. Memory To Save (post-approval)

1. **"Sage = LinkRight's AI interview expert agent"** — persona/character for the interview-coach skill at `~/.claude/skills/linkright-interview-coach/`. Sage is the named interviewer in-session.

2. **"Round picked by user, Problem Type random within"** — key UX architecture; duration determined by rolled PT.

3. **"3-layer signal game scoring"** — Layer A psychological (5 dims) + Layer B PM eval (6 dims) + Layer C executive presence (7 dims). Each scored 0-5. All three required for FAANG-fidelity.

4. **"Gemini handoff pattern for multi-modal"** — when Claude can't process A/V, design structured Gemini prompts with locked JSON output schema. User runs offline → pastes back → Claude aggregates. Reusable pattern.

5. **"3-stage A/V methodology"** — video-only (body language) + audio-only (vocal delivery) + transcript-only (narrative content). Isolates signal channels; cross-source agreement = strong signal.

6. **"Personalized ceiling > generic ideal"** — score against candidate's strongest possible version given career level + transition phase, never against "perfect candidate".

7. **"Kokoro TTS for voice mode"** — local TTS for Sage's voice output; pyttsx3 fallback. Optional mode for real-interview feel.

8. **"Verify time-driven mechanisms before claiming Claude can't"** — `/loop` + `ScheduleWakeup` + `CronCreate` enable real-time background polling.

9. **"PRD format for major skill design"** — full PRD (Problem → Goals → Personas → Stories → FRs/NFRs → Solutioning → Architecture → Data Model → Integration → Phases → Metrics → Risks → Open Qs → Appendices) is the right format for ambitious skill scope. Plain "plan file" too shallow for skill-level architecture.

---

## 20. Verification (how user confirms post-impl)

1. `~/.claude/skills/linkright-interview-coach/SKILL.md` exists with full frontmatter
2. `/linkright-interview-coach` invocation loads skill and greets as Sage
3. Profile loads from `~/.linkright/profile/` (or fallback prompted)
4. Round selection AskUserQuestion offers 7 rounds with descriptions
5. Problem type rolled via `shuf`; output visible
6. Duration matches problem type table
7. Voice mode option offered; Kokoro speaks Sage's Q if selected
8. State file at `/tmp/mock-interview-state-<uuid>.json` is inspectable
9. Clock card auto-refreshes every 90s
10. Patience escalation 🟢→🟡→🟠→🔴 if user over-talks
11. Ramble interrupt triggers at 350+ words
12. Content-only scorecard rendered at end
13. A/V offer presented; 3 Gemini prompts paste-ready with session_id
14. Pasted Gemini JSON validated; holistic 4-source scorecard rendered
15. Improvement playbook reconstructs strongest-possible-version answers from candidate's profile
16. Verdict calibrated to round difficulty
17. Scorecard saved to `~/.linkright/interview-history/<ts>.json`
18. Story bank entries written on explicit user save
19. Drill recommendations specify exact next-session round + PT + target metric
20. `adversarial-reviewer` SIGN OFF achieved before merge

---

**END OF PRD v6**
