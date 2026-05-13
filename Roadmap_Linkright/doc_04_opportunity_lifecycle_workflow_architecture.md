# DOC 04 — Opportunity Lifecycle & Workflow Architecture

## 1. Purpose

This document defines how Linkright models, orchestrates, and manages opportunities and workflows.

It specifies:

- opportunity-centric architecture
- lifecycle states
- workflow structure
- workflow orchestration
- event-driven execution
- sub-workflow coordination
- replayability
- approval systems
- automation sequencing
- workflow boundaries
- execution semantics
- orchestration philosophy

This document defines the operational backbone of Linkright.

---

# 2. Operational Philosophy

Linkright is fundamentally opportunity-centric.

The core operational object is:

```text
Opportunity
```

Everything operationally important should attach to an opportunity.

Examples:
- JD capture
- fit scoring
- resume tailoring
- autofill generation
- recruiter communication
- HR prep
- interview prep
- negotiation support
- final outcome tracking

The system should not behave like isolated commands.

It should behave like:
- a coordinated workflow system
- built around evolving career opportunities

---

# 3. Opportunity Definition

An opportunity represents a single career opportunity lifecycle.

Examples:
- LinkedIn job posting
- recruiter outreach
- startup founder conversation
- referral opportunity
- internal role transition
- inbound recruiting pipeline

An opportunity accumulates:
- states
- workflows
- artifacts
- retrieval rationale
- logs
- communication history
- scoring
- outcomes

An opportunity becomes the canonical operational container.

---

# 4. Opportunity Structure

An opportunity should generally contain:

- opportunity_id
- source
- company
- role
- location
- employment type
- compensation metadata if available
- raw JD
- parsed JD
- tags
- lifecycle state
- sub-workflow states
- fit scores
- retrieval outputs
- artifacts
- logs
- associated profile version
- associated resume versions
- communication records
- interview records
- timestamps

The opportunity object should remain extensible.

---

# 5. Lifecycle Philosophy

An opportunity moves through lifecycle states.

The lifecycle should remain:
- explicit
- inspectable
- replayable
- automation-friendly
- operationally simple

The lifecycle should avoid:
- ambiguous states
- hidden transitions
- silent automation
- fragmented orchestration

---

# 6. Primary Lifecycle States

Recommended primary states:

```text
Captured
Considering
Optimizing
Applied
Interviewing
Offer
Closed
Archived
```

Only one primary lifecycle state should exist at a time.

Primary states represent:
- the dominant operational phase
- the highest-level status of the opportunity

---

# 7. Sub-Workflows

Sub-workflows operate independently within a primary state.

Examples:

While in:
```text
Optimizing
```

Possible sub-workflows:
- resume optimization
- cover letter generation
- autofill generation
- company intelligence generation
- recruiter-risk analysis

While in:
```text
Interviewing
```

Possible sub-workflows:
- HR prep
- intro-call prep
- story prep
- case prep
- salary preparation
- networking prep

Sub-workflows should:
- remain modular
- remain independently observable
- support retries
- support replayability
- support approval checkpoints

---

# 8. Tags

Tags provide lightweight contextual classification.

Examples:
- high_priority
- ai_pm
- startup
- bigtech
- dubai
- referral
- recruiter_contacted
- needs_metrics
- needs_confirmation

Tags should:
- remain flexible
- remain lightweight
- not replace lifecycle states
- not replace workflows

Tags are contextual metadata.

---

# 9. Workflow Philosophy

A workflow is a bounded operational process.

Examples:
- JD parsing
- signal extraction
- retrieval
- tailoring
- width optimization
- PDF rendering
- autofill answer generation
- recruiter reply generation

Workflows should:
- have explicit inputs
- have explicit outputs
- emit logs
- support replayability
- remain composable
- remain observable

Workflows should avoid:
- hidden side effects
- silent mutations
- uncontrolled state drift

---

# 10. Workflow Contracts

Every workflow should define:

- workflow_id
- workflow_type
- inputs
- outputs
- dependencies
- triggering conditions
- retry semantics
- approval requirements
- observability requirements
- generated artifacts
- side effects
- execution boundaries

Workflow contracts should remain deterministic and inspectable.

---

# 11. Event-Driven Execution

The system should support event-driven orchestration.

Examples of events:
- JD captured
- score threshold crossed
- resume generated
- application submitted
- recruiter replied
- interview scheduled
- profile updated
- artifact invalidated

Events may trigger:
- workflows
- rescoring
- regeneration
- notifications
- retries
- downstream automation

Events should remain:
- explicit
- logged
- replayable

---

# 12. Orchestration Philosophy

Linkright should separate:

- orchestration
from
- intelligence execution

Important principle:

```text
n8n orchestrates.
Linkright runtime executes intelligence.
```

Meaning:

Orchestration systems handle:
- triggers
- queues
- retries
- scheduling
- workflow coordination
- notifications
- state updates

Core intelligence remains inside:
- retrieval systems
- scoring systems
- generation systems
- validation systems
- runtime execution layer

This separation is critical.

---

# 13. Approval Checkpoints

Not all workflows should execute autonomously.

Some workflows should require:
- review
- approval
- confirmation
- manual overrides

Examples:
- major profile updates
- aggressive reframing
- recruiter communication
- application submission
- compensation communication

Approval checkpoints increase:
- trust
- safety
- defensibility
- controllability

---

# 14. Replayability

Workflows should support replayability.

Meaning:
- same inputs
- same retrieval context
- same profile version
- same workflow chain

should be reproducible.

Replayability is important for:
- debugging
- experimentation
- auditability
- trust
- evaluation

---

# 15. Retry Semantics

Workflow retries should remain explicit.

Retries may happen because:
- model failure
- timeout
- validation failure
- retrieval inconsistency
- width overflow
- parsing failure
- orchestration interruption

Retries should preserve:
- lineage
- logs
- retry reason
- execution history

The system should avoid silent hidden retries.

---

# 16. Workflow Dependencies

Some workflows depend on others.

Example:

```text
JD Parsing
→ Signal Mapping
→ Retrieval
→ Resume Generation
→ Width Optimization
→ PDF Rendering
```

Dependencies should remain:
- explicit
- inspectable
- deterministic where possible

The system should avoid hidden workflow chains.

---

# 17. Async Processing

Many workflows should support asynchronous execution.

Examples:
- batch JD scoring
- large retrieval pipelines
- artifact rendering
- browser automation
- interview-prep generation

Async workflows should preserve:
- progress visibility
- execution state
- partial outputs
- retry safety
- cancellation support

---

# 18. Workflow Observability

Every workflow should emit structured observability data.

Examples:
- workflow trigger
- inputs
- outputs
- retrieval rationale
- models used
- validation results
- generated artifacts
- timing
- retry history
- user overrides

Observability is not optional.

---

# 19. Workflow State Model

Sub-workflows should support states such as:

```text
Pending
Running
Blocked
Awaiting Approval
Completed
Failed
Cancelled
Stale
```

These states should remain:
- explicit
- inspectable
- automation-friendly

---

# 20. Artifact Lineage

Workflows should preserve artifact lineage.

Example:

```text
Resume_v14.pdf
← generated from
Profile_v7
+ Opportunity_102
+ Retrieval_Run_88
+ Width_Optimization_Run_12
```

Artifact lineage is critical for:
- reproducibility
- debugging
- strategic experimentation
- trust

---

# 21. Workflow Invalidations

Some upstream changes may invalidate downstream artifacts.

Examples:
- profile update
- corrected metric
- updated signal
- modified interpretation
- changed JD

The system should:
- mark dependent artifacts stale
- preserve lineage
- support regeneration
- avoid silent corruption

---

# 22. Batch Operations

The architecture should support batch workflows.

Examples:
- scoring 100 captured JDs
- generating prep packs
- refreshing recruiter-fit analysis
- updating stale artifacts

Batch execution should remain:
- observable
- resumable
- retry-safe
- resource-aware

---

# 23. Browser Extension Interaction

The browser extension should primarily act as:
- contextual sensor layer
- contextual rendering layer
- lightweight command surface

The extension should not become the primary orchestration brain.

The operational core should remain inside:
- runtime layer
- orchestration layer
- retrieval layer
- memory layer

---

# 24. CLI Execution Philosophy

The CLI should behave as:
- deterministic execution runtime
- workflow execution layer
- replayable operational interface
- agent-compatible runtime

CLI commands should eventually become:
- reusable workflow primitives
- orchestration-compatible execution units
- MCP-callable operations

---

# 25. Multi-Surface Architecture

Linkright may eventually support multiple operational surfaces:

- CLI
- browser extension
- MCP server
- APIs
- orchestration workflows
- future dashboard surfaces
- future autonomous agents

All surfaces should share:
- canonical memory
- canonical opportunity model
- canonical workflow contracts

The system should avoid fragmented logic across surfaces.

---

# 26. Human-in-the-Loop Operations

The system should remain human-supervised by default.

Especially for:
- communication
- applications
- networking
- negotiation
- profile changes
- identity shifts

Automation should remain:
- inspectable
- interruptible
- approval-aware

---

# 27. Failure Philosophy

Workflow failures should remain visible.

The system should avoid:
- hidden failure suppression
- silent corruption
- partial hidden mutations

Failures should preserve:
- logs
- state
- retryability
- partial outputs where useful

Users should be able to understand:
- what failed
- why it failed
- what can be retried

---

# 28. Future Workflow Evolution

Future workflow evolution may include:
- autonomous application loops
- recruiter automation
- social/network automation
- email automation
- browser automation agents
- interview simulation agents
- career trajectory orchestration

These are future layers.

Phase 1 should prioritize:
- stable workflows
- strong observability
- replayability
- deterministic contracts
- operational trust

---

# 29. Operational Boundaries

This document defines:
- operational semantics
- orchestration philosophy
- lifecycle behavior
- workflow relationships

It does not define:
- retrieval internals
- memory schema internals
- UI implementation
- deterministic layout engines
- model orchestration internals

Those belong to later documents.

---

# 30. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 02 — Core Ontology & Semantic Architecture
- DOC 03 — Canonical Profile & Memory Graph Architecture

This document influences:
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 09 — Browser Extension & Ambient Intelligence Layer
- DOC 10 — n8n Orchestration & Automation Architecture
- DOC 11 — Observability, Logging & Explainability Framework

This document should be treated as the canonical operational architecture reference for Linkright.

