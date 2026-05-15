### Memory Architecture v2 — Phase 6: `linkright interview coach` (FINAL)

The capstone of the v2 rebuild. Ports the `repeat-after-me` Cloud skill
into the CLI as a Layer-5 consumer of the canonical memory model. Reads
from facts + signals + evidence atoms + coaching playbook → generates
ideal interview answers grounded in the candidate's real career data,
framed by expert coaching methodology, delivered via TTS in realistic
interview cadence.

**Token cost: ~$0.005 per session** vs ~$0.50–1.00 on Claude Cloud — a
~100x reduction because RAG injects only the relevant 3-5 facts + 3
playbook chunks per question instead of loading the full candidate
history + 47-doc playbook into a single Claude context window.

**New command:**

```
linkright interview coach \
  --jd <jd_file> \
  --company "FintechCo" \
  --role "Senior PM" \
  [--round hr|hm|cto|case|founder] \
  [--mode practice|sim] \
  [--voice Samantha] [--no-tts]
```

**Run flow:**

1. **Prereq check** — `linkright onboard` + `linkright coaching-kb build` must have run
2. **`session_profile.classify_session()`** — one Gemini call → `SessionProfile` (seniority, company_stage, role_category, JD-decoded 4-layer, resume risks). Cached for the whole session — every per-question call cites these fields instead of re-classifying.
3. **Init coaching log** — frontmatter + Session Profile section written to `~/.linkright/runs/interview-<ts>/coaching_log.md`
4. **Round + mode picker** (or skip via `--round` / `--mode` flags)
5. **Greeting** — Groq-generated, calibrated to round + warmth + culture, spoken via TTS BEFORE displayed text
6. **Per-question loop:**
   - `answer_gen.generate_question` (Groq 8b, ~200 tok) — calibrated to seniority, round risk, lookup-table category mix, time remaining
   - TTS speaks question → text appears
   - `rag.retrieve_for_question()` — 3-tier cascade: signals → facts → atoms + playbook
   - **Practice mode:** ideal answer shown verbatim (with ⚑ flag if any cited atom is non-resume tier); coaching log gets structured 2-col table + inference note silently
   - **Simulation mode:** waits for candidate answer; structured KEEP/CUT/ADD/GOLD/TONE/TIME feedback + ideal + inference all logged silently; ~50% probabilistic follow-up via `should_followup`
7. **Closing question** — TTS-spoken per-round variant
8. **8-dim scorecard** — `scorecard.generate_scorecard()` (Gemini, structured): 5 answer-quality dims + 3 interviewer-perception dims + headline triplet (strongest asset / primary risk / pre-interview action) + per-signal evidence sentences

**New modules (`coach/`):**

- `tables.py` — every parameter (warmth, time budget, follow-up pressure, question-category weights, closing variants, round info) as static dicts. Skill's "internal reasoning per question" became "lookup table per question" — biggest token-saver of the rebuild.
- `session_profile.py` — one-shot Gemini classifier + `SessionProfile` dataclass with auto-derived seniority_score / answer_length_s / followup_pressure / warmth_level
- `rag.py` — 3-tier cascading retrieval. Signals first (cosine over `signals_embeddings.npz`), then facts via `signal.source_fact_ids` (signal-first principle), then evidence atoms via `fact.evidence_atom_ids` for deeper context, then phase-prefiltered playbook chunks. **Tier flag derivation is architectural** — no manual `--additional-info` flag; the system knows because it tracks evidence tier through the chain.
- `tts.py` — macOS `say` primary, espeak-ng / spd-say fallbacks, non-blocking subprocess.Popen, session-mutable rate + voice
- `coaching_log.py` — daemon-thread background writer; 5 helpers (init_log, append_round_header, append_question_block, append_debrief, append_scorecard); per-question fires-and-forgets
- `answer_gen.py` — five Groq generators (greeting, question, ideal_answer, followup, inference, feedback). Filler-phrase scrubbing. Probabilistic follow-up gate. Closing question lookup.
- `scorecard.py` — 8-dim structured Gemini call → `Scorecard` dataclass with separate `to_screen_md` (terse) and `to_log_md` (full evidence)
- `session.py` — `CoachSession` dataclass + `run_session()` orchestrator + `_run_round()` loop + practice/sim turn handlers
- `cli.py` — Click command registered under `interview` group

**Tier-flag automation (architectural, not manual):**

| Source of cited fact/atom | Tier resolved | Coach behavior |
|---|---|---|
| Fact from `tier=resume_canonical` evidence | `resume_visible` | use freely, no flag |
| Fact from `tier=additional_info`/`diary`/`reflection` evidence | `additional_info_confirmed` | ⚑ flag in displayed answer |
| Pending fact (proposed not confirmed) | `pending` | (Phase 6 conservative — escalates to higher flag tier) |
| Raw atom with no fact yet | `evidence_only` | strongest flag |

**Tests: 36 new pass, 206 total v2 tests across all 6 phases**

- `test_coach_unit.py` (31) — table integrity (round budgets, seniority alignment, weights sum to 1.0), `SessionProfile` derivation + summary MD, TTS (disabled-no-call, markdown stripping, rate clamping, voice mutation), coaching log (frontmatter, blocking append, round header, question block with skip), `answer_gen` helpers (weighted_pick, scrub_filler, should_followup with mocked random, feedback_as_md, closing_question per round), RAG cosine helper (empty inputs, sorted descending, id_filter), tier resolution (resume_canonical, additional_info, diary), `RetrievalBundle.has_non_resume_tier`, `Scorecard.to_screen_md`
- `test_coach_e2e.py` (5) — prereq blocks (no profile, no KB), full practice mode session (mocked Gemini + Groq + embedder + TTS subprocess), simulation mode captures answer + structured feedback in log, session profile persists into log frontmatter

Plan: `~/.claude/plans/okay-what-i-want-elegant-cook.md` (Part G)

---

**Memory Architecture v2 rebuild complete.** Six phases, six PRs, ~7 weeks of plan-time, 206 tests. The user's full workflow is now:

```
linkright onboard -r resume.pdf      # Phase 2 — facts + signals + canonical profile
linkright evidence add memo.md       # Phase 0 — additional context as Memo atoms
linkright diary add                  # Phase 1 — daily journaling compounds memory
linkright enrich                     # Phase 3 — gap-driven RAG proposes new facts
linkright coaching-kb build           # Phase 5 — index methodology playbook
linkright interview coach \           # Phase 6 — practice with real RAG-grounded answers
  --jd jd.md --company X --role Y
```

Token-cost story: a full coach session (~10 questions) costs ~$0.005 on
Groq + Gemini free tier, vs the original Cloud skill which loaded 47 docs
into Claude context for ~$0.50-1.00 per session. ~100x reduction by
making chunks atom-bounded (Phase 0 Memo Format) and retrieval signal-first
(Phase 5 routing prefilter + Phase 6 cascading retrieval).
