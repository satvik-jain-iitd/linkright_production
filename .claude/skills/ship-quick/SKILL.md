---
name: ship-quick
description: Full BMAD multi-module product release workflow. Routes greenfield vs brownfield. Orchestrates 5 modules (BMM, CIS, WDS, TEA, Core), 14 agents, 37 steps. Tracks all work via Beads 4-layer dependency graph.
user-invocable: true
trigger: When user says "ship quick", "ship it", "new release", "quality release", "build this", "ship this", or wants to plan and execute a full product release.
---

# Ship Quick — BMAD Multi-Module Release Workflow

You are executing the Ship Quick skill. This orchestrates a complete product release using the BMAD methodology across 5 modules, 14 agents, and 37 steps. Every task is tracked via Beads (`bd`), and all 6 tools from the Coding Constitution are used at every step.

---

## HARD RULES — Context & Token Management

### Token Discipline
- **NEVER exceed 10,000 tokens** in any single tool call output, file write, or agent prompt
- If content is large, split into multiple smaller writes/calls
- Keep agent prompts focused and scoped — don't dump entire project context into one prompt

### Fresh Worktree Per Phase
- **Every phase starts in a NEW worktree** (`git worktree add`)
- This ensures clean context with zero baggage from prior phases
- Previous phase artifacts are committed to the branch before starting new worktree
- Worktree naming: `ship-quick-phase-{N}-{date}`

### Compact After Every Phase / Every 3 Tasks
- After completing **every phase** OR **every 3 tasks** (whichever comes first):
  1. Commit all work in current worktree
  2. Write a **Phase Summary** (max 200 words, bullet points)
  3. Save summary to `_bmad-output/summaries/phase-{N}-summary.md`
  4. Close all completed bd tasks
  5. `bd status` to confirm state

### Phase Summaries (MANDATORY)
- After each phase, present a summary to the user
- **Language: Romanized Hindi** (all summaries MUST be in Romanized Hindi)
- Format: **Max 200 words**, bullet points only
- Must include:
  - Kya kiya (actions taken)
  - Kya banaya (artifacts/files created)
  - Key findings (if any)
  - Aage kya hoga (next phase preview)
- This is NOT optional — every phase ends with a summary

### Per-File Summaries (MANDATORY)
- **Every file created** during Ship Quick must have a companion summary
- Save to: `_bmad-output/summaries/file-{filename}-summary.md`
- **Language: Romanized Hindi**
- Format: **Max 200 words**, bullet points
- Must include:
  - File ka naam aur path
  - Yeh file kya hai (purpose)
  - Isme kya kya hai (contents overview)
  - Key sections/data points
  - Isko kaun use karega aur kab (who uses this, when)
- Create these summaries IMMEDIATELY after creating each file
- Present to user inline (in chat) AND save to summaries folder

---

## STEP 0: ROUTE — Ask the User

Before anything else, determine the project type:

```
Ask: "Is this a greenfield project (building from scratch) or brownfield (improving existing codebase)?"
```

**If GREENFIELD** — User provides: product idea, target users, tech stack, constraints. No codebase to scan. Follow the Greenfield Flow below.

**If BROWNFIELD** — User provides: codebase path, reference implementation (optional), known issues, quality standards. Follow the Brownfield Flow below.

---

## STEP 1: Create Beads Dependency Graph

Before ANY execution, convert the entire plan into a `bd` dependency graph with 4 layers:

```bash
# Create the epic
bd create --type=epic --title="Ship Quick: {project_name}"

# For each phase, create features:
bd create --type=feature --parent={epic_id} --title="Phase 1: Discovery"

# For each workflow in a phase, create stories:
bd create --type=story --parent={feature_id} --title="Generate Project Context"

# For each granular step in a workflow, create tasks:
bd create --type=task --parent={story_id} --title="Scan codebase structure"
```

**4 layers:** Epic > Feature > Story > Task

**Execution rule:** Always start at the MOST GRANULAR task (leaf node). Pick up > mark in_progress > complete > close. Parent closes only when ALL children close.

**Session continuity:** `bd ready` at session start shows what's unblocked. New session picks up exactly where previous left off — the Beads graph IS the context.

---

## EXECUTION PROTOCOL (Apply to EVERY Task)

```
BEFORE any task:
  1. bd ready                              → see what's unblocked
  2. search_memories("<task topic>")       → check if solved before (mem0)
  3. qmd "<what am I building/fixing>"     → surface relevant local docs
  4. chub get <library>                    → if external lib involved
  5. bd update {task_id} --status=in_progress

DURING task:
  6. Run tests after every meaningful change
  7. If API fails → chub get <library> before debugging
  8. If unexpected → qmd "<symptom>" before assuming
  9. bd update {task_id} --notes="..." if approach changes

AFTER task:
  10. bd close {task_id}
  11. add_memory("<what was built/fixed + pattern>")  → mem0
  12. bd remember "<insight>" if non-obvious learning

AT HUMAN GATES:
  13. send_message → notify user via AgentMail
  14. Wait for explicit approval before proceeding

FOR LIVE TESTING:
  15. agent-browser snapshot → map current UI state
  16. agent-browser act → test user flows
```

---

## TOOL INTEGRATION MAP

| Tool | When | How |
|------|------|-----|
| **bd** (Beads) | ALL task tracking | `bd create`, `bd update --status=in_progress`, `bd close`, `bd remember` |
| **chub** (Context Hub) | Before ANY external library code | `chub get <library>` before Anthropic/Supabase/FastAPI/Next.js code |
| **qmd** | Before each phase to surface local docs | `qmd "how is X implemented"`, `qmd "<topic>"` |
| **agent-browser** | Live site testing after each change | `agent-browser snapshot` to map UI, `agent-browser act` to test |
| **AgentMail** | Notify user at human gates + long tasks | `send_message` at Gate 1 and Gate 2 |
| **mem0** (OpenMemory) | Before coding: search. After: store | `search_memories` before, `add_memory` after |

---

## GREENFIELD FLOW

### Phase 0: Init
- `bmad-init` → config.yaml (modules: bmm, cis, wds, tea)
- `bd create` epic "Ship Quick: {project_name}" (greenfield)

### Phase 1: Discovery (no codebase — 5 steps)
1. **cis: Design Thinking (DT)** — Agent: Maya → empathy map of target users
2. **bmm: Domain Research (DR)** — Agent: Mary → industry deep-dive (6 steps)
3. **bmm: Market Research (MR)** — Agent: Mary → competitive landscape (6 steps)
4. **bmm: Technical Research (TR)** — Agent: Mary → tech feasibility (6 steps)
5. `qmd` search for relevant prior work in local docs

**Parallel:** Agents 1-3 can run as parallel sub-agents in separate worktrees.

### Phase 2: Creative & Brief (6 steps)
6. **cis: Brainstorming (BS)** — Agent: Carson → 100+ product ideas
7. **cis: Innovation Strategy (IS)** — Agent: Victor → business model innovation
8. **wds: Project Setup (wds-0)** — Agent: Saga → type, complexity, routing
9. **wds: Project Brief (wds-1)** — Agent: Saga → product brief (45 steps)
10. **wds: Trigger Mapping (wds-2)** — Agent: Saga → user interaction map (42 steps)
11. **core: bmad-party-mode** — Multi-agent discussion (PM + Architect + QA + Test)

### Phase 3: Planning (6 steps)
12. **bmm: Create PRD (CP)** — Agent: John → prd.md (15 steps)
13. **bmm: Validate PRD (VP)** — Agent: John → 13 validation checks
14. **bmm: Create UX Design (CU)** — Agent: Sally → UX design (14 steps)
15. **wds: Scenarios (wds-3)** — Agent: Freya → user scenarios (14 steps)
16. **wds: UX Design (wds-4)** — Agent: Freya → visual specs (11 steps)
17. **core: bmad-review-adversarial-general** → cynical PRD review (>=10 findings)

**GATE 1:** `send_message` via AgentMail → user reviews → approve/modify/skip

### Phase 4-7: Same as Brownfield (see below)

---

## BROWNFIELD FLOW

### Phase 0: Init
- `bmad-init` → config.yaml (modules: bmm, cis, wds, tea)
- `bd create` epic "Ship Quick: {project_name}" (brownfield)

### Phase 1: Discovery & Analysis (6 steps)
1. **bmm: Generate Project Context (GPC)** — Agent: Winston → project-context.md (3 steps: discover → generate → complete)
2. **bmm: Document Project (DP)** — Agent: Paige → reference quality doc (2 sub-workflows: deep-dive or full-scan)
3. **core: bmad-distillator** → compress context for downstream agents (4 stages: analyze → compress → verify → validate)
4. **core: bmad-index-docs** → searchable doc index
5. **bmm: Technical Research (TR)** — Agent: Mary → industry benchmarks (6 steps)
6. **cis: Design Thinking (DT)** — Agent: Maya → empathy map of user pain points

**Parallel:** Steps 1, 2, 5 as parallel sub-agents (each in own worktree). Steps 3-4 after 1-2 complete. Step 6 independent.

### Phase 2: Creative Solutioning (6 steps)
7. **cis: Brainstorming (BS)** — Agent: Carson → 100+ quality monitoring ideas (SCAMPER, Six Hats, Reverse)
8. **cis: Innovation Strategy (IS)** — Agent: Victor → quality as competitive differentiator
9. **cis: Problem Solving (PS)** — Agent: Dr. Quinn → root-cause analysis per quality gap (5 Whys, Fishbone, First Principles)
10. **core: bmad-advanced-elicitation** → refine requirements (Socratic, pre-mortem, red team)
11. **core: bmad-party-mode** → multi-agent discussion (John/PM + Winston/Architect + Quinn/QA + Murat/Test)
12. **wds: Trigger Mapping (wds-2)** — Agent: Saga → complete user interaction map (42 steps)

**Parallel:** Steps 7-8 (ideas track) parallel with 9-10 (analysis track). Step 11 after both. Step 12 independent.

### Phase 3: Planning (6 steps)
13. **bmm: Create PRD (CP)** — Agent: John → prd.md
    - 15 steps: init → discovery → vision → exec-summary → success → journeys → domain → innovation → project-type → scoping → functional → nonfunctional → polish → complete
14. **bmm: Validate PRD (VP)** — Agent: John → 13 validation checks:
    - format-detection → parity-check → density → brief-coverage → measurability → traceability → implementation-leakage → domain-compliance → project-type → SMART → holistic-quality → completeness → report
15. **bmm: Edit PRD (EP)** — Agent: John → fix validation issues (5 steps)
16. **core: bmad-review-adversarial-general** → >=10 PRD findings
17. **wds: Scenarios (wds-3)** — Agent: Freya → user scenarios (14 steps)
18. **wds: UX Design (wds-4)** — Agent: Freya → quality indicator UI (11 steps)

**GATE 1:** `send_message` via AgentMail → user reviews findings → approve/modify/skip

**Sequential:** Each step depends on previous (PRD → Validate → Edit → Review → Scenarios → UX)

---

## SHARED PHASES 4-7 (Both Greenfield and Brownfield)

### Phase 4: Technical Solutioning (7 steps)
19. **wds: Product Evolution (wds-8)** — Agent: Freya → brownfield improvement plan [brownfield only]
20. **bmm: Create Architecture (CA)** — Agent: Winston → architecture.md
    - 9 steps: init → context → starter → decisions → patterns → structure → validation → complete
21. **tea: Test Design (TD)** — Agent: Murat → test-design.md (9 steps)
22. **tea: Test Framework (TF)** — Agent: Murat → test scaffold (9 steps)
23. **tea: NFR Assessment (NR)** — Agent: Murat → non-functional requirements (14 steps: security, performance, reliability, scalability)
24. **bmm: Create Epics & Stories (CE)** — Agent: Winston + John → epics-and-stories.md
    - 4 steps: validate-prerequisites → design-epics → create-stories → final-validation
25. **bmm: Implementation Readiness (IR)** — Gate check (6 steps: document-discovery → prd-analysis → epic-coverage → ux-alignment → epic-quality → final-assessment)

**Parallel after step 20:** Steps 21-23 (TEA track) parallel with step 24 (stories). Both merge into step 25.

### Phase 5: Implementation (6 steps)
26. **bmm: Sprint Planning (SP)** — Agent: Bob → sprint-status.yaml (parse epics → build status → generate YAML)
27. **tea: ATDD (AT)** — Agent: Murat → failing acceptance tests first, TDD red phase (12 steps)
28. **Story Dev Loop** (repeat per story, parallel per epic):
    - `search_memories("<story topic>")` before each story
    - `chub get <library>` before any API code
    - **bmm: Create Story (CS)** — Agent: Bob → story file (6 steps: discover target → load artifacts → architecture analysis → web research → create story → update sprint)
    - **bmm: Dev Story (DS)** — Agent: Amelia → implement (10 steps: find story → load context → detect continuation → mark in-progress → implement red-green-refactor → author tests → run validations → mark task complete → story completion → user support)
    - **bmm: Code Review (CR)** — Agent: Quinn → review (4 steps: gather context → adversarial parallel review → triage → present)
      - Auto-fires: `bmad-review-adversarial-general` (>=10 findings)
      - Auto-fires: `bmad-review-edge-case-hunter` (JSON edge cases)
    - `agent-browser snapshot + act` → test live after each story
    - `add_memory("<pattern>")` after each fix
    - `bd close {story_task_id}`
    - **If CR fails:** DS again → CR again (loop until pass)
29. **bmm: QA Generate E2E Tests (QA)** — Agent: Quinn → test suite (5 steps: detect framework → identify features → generate API tests → generate E2E tests → run + report)
30. **tea: Test Automation (TA)** — Agent: Murat → expand coverage (12 steps)
31. **tea: CI Setup (CI)** — Agent: Murat → CI/CD pipeline (8 steps)

**GATE 2:** `send_message` via AgentMail → user reviews PR → approve/reject

**Parallel in step 28:** Independent epics run in separate worktrees:
- worktree-epic-1: Backend stories (quality judge, bug fixes)
- worktree-epic-2: Frontend stories (quality dashboard)
- worktree-epic-3: Test stories (unit, E2E)

### Phase 6: Quality Assurance (5 steps)
32. **tea: Test Review (RV)** — Agent: Murat → quality audit 0-100 score (13 steps)
33. **tea: Traceability (TR)** — Agent: Murat → requirement→test→code matrix (9 steps) + quality gate decision
34. **core: bmad-review-adversarial-general** → final cynical review of complete release diff
35. **core: bmad-review-edge-case-hunter** → edge case analysis of complete release diff
36. **core: bmad-editorial-review-structure + bmad-editorial-review-prose** → polish all generated docs

**Parallel:** Steps 32-33 (TEA track) parallel with 34-35 (review track). Step 36 after both.

`agent-browser` → full E2E test of deployed product after all QA passes.

### Phase 7: Retrospective (1 step)
37. **bmm: Retrospective (ER)** — Review sprint results, quality scores, test coverage
    - `add_memory("Release completed: <summary>")`
    - `bd remember "<key insight>"`
    - `bd close` all remaining tasks
    - Verify: `bd ready` shows empty (all work done)

---

## CONTINUOUS LOOP (Post-Deployment)

After every production deployment, Ship Quick can auto-loop:

```
PRODUCTION DEPLOY (git push / Vercel / CI merge)
       |
       v
1. Create fresh worktree (git worktree add .claude/worktrees/quality-audit-{date})
2. Spawn new agent (fresh context window)
3. bd ready → check Beads graph for unfinished work
4. If clean slate → create new Beads graph for this cycle
5. Run Phase 1-3 (Discovery → Creative → Planning)
6. GATE 1: AgentMail → user reviews findings
7. If approved → Phase 4-5 (Solution → Implement) in worktree
8. GATE 2: AgentMail → user reviews PR
9. If merged → Deploy → Loop to step 1
10. Store quality snapshot: .quality/audit-{date}.yaml
11. add_memory("Quality audit: {date} | Score: {score} | Delta: {delta}")
```

**Human gates:** Agent NEVER deploys or merges without explicit user approval.

**Fresh context:** Each cycle starts with new worktree + new agent. Loads: SKILL.md + project-context.md + latest quality metrics. Previous retrospective.md available as reference.

**Quality tracking:** Each cycle produces a snapshot:
```yaml
# .quality/audit-{date}.yaml
date: 2026-04-06
quality_score: 82
grade: B
improvements_proposed: 5
improvements_implemented: 3
test_review_score: 85
delta_from_last: +7
```

---

## AGENTS ROSTER (14 Total)

| Agent | Module | Role | Phases |
|-------|--------|------|--------|
| John | BMM | Product Manager | PRD, Validate, Edit, Stories |
| Winston | BMM | System Architect | GPC, Architecture, Epics, IR |
| Mary | BMM | Business Analyst | Domain/Market/Tech Research |
| Paige | BMM | Technical Writer | Document Project |
| Sally | BMM | UX Designer | UX Design (greenfield) |
| Bob | BMM | Scrum Master | Sprint Planning, Create Story |
| Amelia | BMM | Developer | Dev Story |
| Quinn | BMM | QA Engineer | Code Review, QA Tests |
| Maya | CIS | Design Thinking Maestro | Empathy map |
| Carson | CIS | Brainstorming Specialist | 100+ ideas |
| Victor | CIS | Innovation Oracle | Differentiation strategy |
| Dr. Quinn | CIS | Problem Solver | Root-cause analysis |
| Freya | WDS | UX Designer | Scenarios, UX Design, Product Evolution |
| Saga | WDS | Strategic Analyst | Trigger Mapping, Project Brief |
| Murat | TEA | Test Architect | All 8 TEA workflows |

---

## QUALITY GATES

| Gate | Condition | Action on Failure |
|------|-----------|-------------------|
| PRD Validation (Phase 3) | Passes 13 checks | Edit PRD, re-validate |
| Adversarial Review (Phase 3) | No critical gaps | Edit PRD for gaps |
| Implementation Readiness (Phase 4) | 6 checks pass | Revise architecture/stories |
| Code Review (Phase 5, per story) | Adversarial + Edge Case pass | Fix → re-review |
| GATE 1 — Human (Phase 3) | User approves plan | Modify/skip per user |
| GATE 2 — Human (Phase 5) | User approves PR | Reject → fix → re-submit |
| Test Review (Phase 6) | Score >= 80/100 | Expand tests, fix gaps |
| Traceability (Phase 6) | Every PRD req mapped to test | Add missing tests |
