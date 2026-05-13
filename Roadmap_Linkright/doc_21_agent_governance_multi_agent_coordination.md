# DOC 21 — Agent Governance & Multi-Agent Coordination

## 1. Purpose

This document defines the governance model, taxonomy, coordination protocol, and failure semantics for agents operating within Linkright.

It specifies:

- agent philosophy
- agent taxonomy
- coordination model
- agent contracts
- memory mutation protocol
- human escalation triggers
- failure isolation
- extension boundaries for future autonomous agents

This document governs how agents operate, what they own, and where they stop.

---

## 2. Agent Philosophy

Agents in Linkright are specialized executors, not autonomous decision-makers.

Each agent has a bounded task contract:
- it receives defined inputs
- it produces defined outputs
- it does not exceed its scope
- it does not call other agents directly

This is deliberate.

The system is built on a career OS that must remain trustworthy. Agents that exceed their scope introduce opacity. Opacity breaks trust. Trust is foundational (see DOC 01, section 7).

The design principle is:

```text
Narrow scope. Clear contract. Visible behavior.
```

An agent that does less reliably is more useful than one that does more unpredictably.

---

## 3. Agent Taxonomy

Six agent types cover the full operational scope of Linkright.

### 3.1 Retrieval Agent

Responsibility: fetch and rank signals relevant to a given JD and identity context.

- Inputs: JD parse output, profile signals, identity context, target archetype
- Outputs: ranked signal set with relevance scores and provenance
- Side effects: read-only access to profile memory and signal store
- Failure behavior: returns partial results with coverage metadata; never silently drops signals

### 3.2 Generation Agent

Responsibility: write bullets, summaries, and narrative expressions given retrieved signals.

- Inputs: ranked signal set, layout constraints, tone parameters, JD alignment targets
- Outputs: generated text artifacts with per-item provenance and confidence
- Side effects: none — generation is stateless
- Failure behavior: returns partial generation with item-level failure markers

### 3.3 Validation Agent

Responsibility: verify that generated outputs conform to width constraints, schema requirements, and authenticity rules.

- Inputs: generated artifact, layout spec, profile ground truth
- Outputs: validation report with pass/fail per item, width measurements, authenticity flags
- Side effects: none — validation is read-only
- Failure behavior: surfaces all validation failures explicitly; never silently passes a failing artifact

### 3.4 Orchestration Agent

Responsibility: sequence Retrieval, Generation, and Validation agents for a complete resume run or workflow execution.

- Inputs: opportunity context, profile version, run configuration
- Outputs: completed artifact set, run log, partial results on failure
- Side effects: creates a run record; coordinates agent calls in sequence
- Failure behavior: surfaces which stage failed, what completed before the failure, and what the user can recover

The Orchestration Agent is the only agent that calls other agents. Agents do not call each other directly.

### 3.5 Learning Agent

Responsibility: process outcome events and update signal weights based on conversion data.

- Inputs: outcome event stream (application sent, response received, interview scheduled, offer made)
- Outputs: updated signal weight deltas; learning summary
- Side effects: writes to signal weight store via memory mutation protocol (see section 5)
- Failure behavior: skips weight update and logs the dropped event; never corrupts existing weights on partial failure

### 3.6 Suggestion Agent

Responsibility: surface identity upgrade suggestions, relationship connection candidates, and personal rhythm prompts.

- Inputs: recent diary entries, opportunity history, signal trajectory, profile version
- Outputs: suggestion set with supporting rationale; confidence scores; user-facing framing
- Side effects: none — suggestions are read-only until user confirms
- Failure behavior: surfaces no suggestions rather than low-confidence suggestions; explicit empty state is preferable to noisy false positives

---

## 4. Coordination Model

Agents do not call each other.

The Orchestration Agent sequences all agent calls. This keeps execution paths traceable and prevents cascading failures that cross agent boundaries.

Cross-workflow triggers are handled by n8n (see DOC 10). n8n routes events between workflows. The Orchestration Agent handles sequencing within a workflow.

The coordination boundary is:

```text
n8n:                  cross-workflow triggers, scheduling, retries, event routing
Orchestration Agent:  intra-workflow sequencing of Retrieval → Generation → Validation
```

No agent owns workflow routing. No agent decides what to trigger next outside its own contract.

---

## 5. Memory Mutation Protocol

No agent modifies profile memory directly.

Writes to profile memory follow a two-step protocol:

1. Agent produces a proposed mutation with rationale and confidence score.
2. The mutation is surfaced to the user for confirmation before it is applied.

This protocol applies to:
- identity changes (archetype, seniority level, narrative framing)
- signal weight updates beyond a defined confidence threshold
- new signals derived from diary or outcome data

Routine writes that do not affect identity — such as run logs, artifact versions, and outcome event records — do not require user confirmation. They follow standard append-only logging.

The distinction is:

```text
Routine append → no confirmation needed
Identity-affecting mutation → user confirmation required
```

---

## 6. Human Escalation Triggers

An agent escalates to the user rather than executing autonomously when any of the following conditions are met:

1. The action affects irreversible state: sending an email, submitting an application, posting externally, deleting a record.
2. The agent's confidence falls below a defined threshold for the output type.
3. The proposed action would modify identity: archetype, seniority level, career narrative, or positioning framing.
4. Conflicting signals are detected and the conflict cannot be resolved deterministically.

Escalation does not mean failure. It means the system has reached a boundary where human judgment is required.

When escalating, the agent surfaces:
- what it was trying to do
- why it is pausing
- what the user needs to decide
- what the options are

The user is never asked to debug an agent. The agent provides the decision frame; the user makes the call.

---

## 7. Failure Isolation

If one agent in a sequence fails, the orchestrator does not silently discard the run.

The failure behavior is:

- surface what completed before the failure
- surface the failure reason at the agent and step level
- offer the user a recovery path: retry the failed agent, skip the step, or inspect the partial output

Silent failure is not permitted at any agent boundary.

This extends the runtime failure philosophy from DOC 08, section 20. The agent layer does not introduce new opacity. Every failure visible in the runtime remains visible at the agent coordination level.

---

## 8. Future Extension: Autonomous Agents

Phase 2 may introduce agents with broader execution scope:

- Networking Agent — identifies connection candidates and drafts outreach
- Outreach Agent — coordinates follow-up communication across opportunities
- Calendar Agent — manages interview scheduling and preparation windows

These agents are not designed here. They are acknowledged as a planned extension.

The current governance model is designed to accommodate them without requiring structural changes:

- the coordination model (Orchestration Agent as the single sequencer) scales to additional agent types
- the memory mutation protocol applies to any agent that touches profile memory
- the human escalation triggers remain the same; new agents must respect them

The design constraint is:

```text
Do not prevent Phase 2 autonomous agents.
Do not assume they exist.
```

Any agent architecture decision that would block autonomous extension is a design mistake. Any assumption that Phase 2 agents already exist is a premature build.

---

## 9. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 10 — n8n Orchestration & Automation Architecture
- DOC 00 — Architectural Decisions Log (Decisions 2, 4, 9)

This document influences:
- DOC 24 — Closed-Loop Learning Architecture
- DOC 25 — Relationship Graph & Networking Intelligence
- DOC 26 — Personal Operating Rhythm
- DOC 28 — Identity Evolution & Signal Tracking

This document should be treated as the canonical agent governance and coordination reference for Linkright.
