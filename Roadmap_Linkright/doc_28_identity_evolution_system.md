# DOC 28 — Identity Evolution System

## 1. Purpose

This document defines the professional identity tracking and evolution architecture of Linkright.

It specifies:

- the philosophy of identity as a dynamic, evidence-grounded construct
- the layers of professional identity the system maintains
- the signals that trigger identity upgrade suggestions
- the user-controlled flow for confirming or dismissing upgrades
- archetype evolution and drift detection
- identity consistency enforcement across generated artifacts
- historical identity preservation for past roles
- Phase 2 multi-persona support

This document defines how Linkright tracks who the user is becoming, not only who they were when they first created a profile.

---

## 2. Core Philosophy

Professional identity is not static.

A PM who joined a startup at IC level four years ago is not the same professional today.
Their signals have compounded.
Their responsibilities have grown.
Their archetype may have drifted.
Their seniority level may have crossed a threshold.

A system that does not track this evolution will generate increasingly misaligned artifacts over time.

The identity evolution system exists to prevent that drift without replacing the user's judgment.

The core constraint is this:

The system detects.
The user confirms.
The system never auto-updates professional identity.

Identity is too strategically consequential to update silently.
A seniority level claim that is one level too high can damage credibility.
An archetype that has drifted too far from accumulated evidence creates incoherent positioning.

The system surfaces the signal.
The user decides what is true.

---

## 3. Identity Layers

Professional identity in Linkright is structured as three distinct layers.

### 3.1 Seniority Level

The user's current seniority band.

Examples:

- IC
- Senior IC
- Staff / Principal
- Manager
- Director
- VP
- Executive

Seniority level governs:

- how resume bullets are framed (organizational scope vs task scope)
- what competencies are foregrounded in retrieval
- how the summary section positions years of experience
- what promotion readiness analysis targets

### 3.2 PM Archetype

The user's primary PM subtype.

Examples:

- Execution Operator PM
- AI Workflow PM
- Systems PM
- Growth Experimentation PM
- Strategic Platform PM
- Human Coordination PM

Archetypes are not mutually exclusive.
A user may have a primary archetype and a secondary archetype.

The primary archetype governs:

- retrieval signal weighting (which signals get amplified)
- artifact generation framing
- opportunity fit scoring

The secondary archetype is used for signals that supplement the primary without overriding it.

### 3.3 Narrative Coherence Score

A system-maintained assessment of how consistent the user's expressed signals are with their confirmed identity profile.

This score is not shown as a number to the user.
It is used internally to flag inconsistencies before artifact generation.

Examples of low coherence conditions:

- user has claimed Director seniority but all logged evidence supports Senior IC behavior
- user has claimed AI Workflow PM archetype but signals are predominantly execution-operator signals
- user's most recent role signals differ substantially from their stated primary archetype

Low coherence triggers a soft flag before resume generation:

```text
Some of your strongest recent signals may not match your current identity profile.
Review before generating?
```

The user can proceed, review, or update.

---

## 4. Signal Detection for Identity Upgrade

The system continuously monitors accumulated evidence for identity upgrade signals.

Four trigger categories:

### 4.1 Title Signal

User mentions a new title in a diary entry.

Examples:

- "just got promoted to Senior PM"
- "got the Director title offer today"
- "moving into a Staff PM role"

The system detects this as a direct identity upgrade signal and surfaces the upgrade suggestion immediately.

### 4.2 Tenure Threshold

User crosses a tenure milestone in a role without a logged title change.

Default thresholds:

- 18 months at current seniority level without promotion signal
- 24 months in same archetype context without drift signal

These thresholds are not automatic.
Crossing them triggers a review prompt, not an upgrade.

### 4.3 Responsibility Signal

Logged behavior crosses a responsibility threshold associated with a higher seniority band.

Examples:

- managing 3 or more direct reports or junior PMs (Director-level signal)
- owning cross-org portfolio prioritization without explicit title (Director behavior)
- representing the product function to executive leadership on a recurring basis (VP-adjacency signal)
- architecting a multi-team system end-to-end without a senior engineering partner directing the scope (Staff-level signal)

Each responsibility threshold maps to a seniority band.
When multiple responsibility signals from the same band accumulate over a rolling 90-day window, the upgrade suggestion fires.

### 4.4 Archetype Drift

Signals logged over time consistently point to a PM subtype different from the user's current primary archetype.

Example:

A user whose primary archetype is Execution Operator PM accumulates 3 months of diary entries that are predominantly about AI workflow design, trust systems, and automation orchestration.

The system surfaces:

```text
Recent signals suggest your work may be drifting toward AI Workflow PM patterns.
Update your archetype?
```

Archetype drift detection uses a rolling 60-day window.
The threshold for suggestion is when more than 60% of recent signal tags point to a different archetype.

---

## 5. Upgrade Suggestion Flow

When a detection trigger fires, the system initiates a single, non-blocking suggestion.

Format:

```text
Based on signals from the past [N] weeks, you appear to be operating at [level / archetype].
Update your identity profile?

[Yes — update now] [Not yet] [Dismiss for 4 weeks]
```

Responses:

- **Yes — update now**: the identity profile is updated with the new level or archetype. Previous identity is preserved in history. A timestamp and trigger reason are logged.
- **Not yet**: the system waits and re-checks after 4 weeks.
- **Dismiss for 4 weeks**: the system suppresses the suggestion for 4 weeks, then rechecks. If the same pattern persists, the suggestion fires again.

The system never auto-updates identity regardless of how strong the signals are.

This is a hard constraint.

---

## 6. Archetype Evolution Graph

PM subtypes can evolve into one another.

The system maintains a lightweight transition graph that models common archetype evolution paths.

Examples:

- Growth Experimentation PM → AI Workflow PM (when AI tooling signals compound on top of funnel reasoning)
- Execution Operator PM → Systems PM (when cross-org scope and platform signals accumulate)
- Systems PM → Strategic Platform PM (when market reasoning and long-horizon signals emerge)
- Human Coordination PM → Director-track (when organizational alignment signals cross the management threshold)

When archetype drift is detected, the system checks whether the drift direction matches a known transition path.

If it does, the suggestion is framed as evolution:

```text
Your signals suggest a natural evolution toward [archetype].
This aligns with common transition patterns. Worth confirming?
```

If it does not match a known path, the suggestion is framed as a potential inconsistency for the user to evaluate.

The transition graph is not exhaustive.
It is a heuristic that improves suggestion quality without overriding user judgment.

---

## 7. Identity Consistency Guard

Before any resume or LinkedIn content is generated, the system performs an identity consistency check.

The check compares:

- the identity context requested for the artifact (target seniority, target archetype)
- the confirmed identity profile at the time of generation
- the signal strength supporting the requested identity framing

If the requested framing materially exceeds the confirmed identity, the system surfaces a flag:

```text
The requested framing positions you as [X], but your confirmed identity is [Y].
Proceeding may create defensibility risk. Continue?
```

The user can proceed or adjust.

The system does not block generation.
It surfaces the risk and transfers the decision to the user.

This is consistent with the truth-first philosophy established in DOC 01.

---

## 8. Historical Identity Preservation

When a user's identity is updated, the previous identity state is preserved as a dated snapshot.

This matters for resume generation.

When generating bullets for a past role, the system should use the identity context that was accurate at that time, not the user's current identity.

Example:

A user who is now a Director PM was a Senior IC PM from 2019 to 2022.
When generating bullets for that period, the system frames them with the scope and responsibility level appropriate to that role — not through the lens of Director-level framing.

This prevents retroactive inflation.

Retroactive inflation — making past experience sound more senior than it was — is one of the most common and most detectable forms of resume distortion.

The historical identity layer prevents the system from drifting into that failure mode as users grow.

---

## 9. Phase 2 — Multi-Persona Support

Some users operate across more than one archetype track simultaneously.

Examples:

- PM by day, active startup advisor
- PM at an enterprise company, independently building a product on the side
- Staff PM with a parallel executive coaching identity

Phase 2 will introduce multi-persona support.

A persona is a named, distinct identity context with its own archetype, seniority level, and signal weighting.

Users may switch the active persona before generating artifacts.

Personas are not separate profiles.
They share the same underlying memory graph.
They apply different weighting and framing to the same evidence pool.

Phase 2 is not defined in this document.
This section records the design intention so that Phase 1 architecture decisions do not foreclose multi-persona support.

---

## 10. Non-Goals

This document explicitly does not cover:

- assigning identity without user evidence
- overriding user-confirmed identity based on system inference
- managing identity for external parties (the user's manager, the HR system, or the organization)
- generating fake seniority signals
- retroactively inflating past role framing to match current identity

The Identity Evolution System confirms and tracks what the user demonstrates.
It does not assign what the user should be.

---

## 11. Integration

This document integrates with:

- DOC 03 — Canonical Profile & Memory Graph: the confirmed identity profile lives in the memory graph as a first-class entity with version history
- DOC 05 — Retrieval System: retrieval uses current identity to weight signal relevance; historical identity is applied when generating artifacts for past roles
- DOC 06 — Resume Generation: the identity consistency guard runs before every resume generation pass; historical identity snapshots govern bullet framing by role period
- DOC 23 — Career Decision Engine: opportunity fit scoring uses current archetype to evaluate alignment between the user's identity and a target role
- DOC 26 — Personal Operating Rhythm: weekly diary entries are the primary source of responsibility signals and archetype drift signals
- DOC 27 — Post-Offer Professional OS: tenure tracking, responsibility signal capture, and career pivot detection in DOC 27 are the primary feed for identity evolution triggers in this document

---

## 12. Document Dependencies

This document depends on:

- DOC 01 — Vision, Philosophy & System Principles
- DOC 02 — Core Ontology & Semantic Architecture
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System
- DOC 26 — Personal Operating Rhythm & Weekly Review System
- DOC 27 — Post-Offer Professional OS

This document should be treated as the canonical reference for professional identity tracking and evolution in Linkright.
