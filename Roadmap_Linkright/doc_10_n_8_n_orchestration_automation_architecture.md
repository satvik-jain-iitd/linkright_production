# DOC 10 — n8n Orchestration & Automation Architecture

## 1. Purpose

This document defines the orchestration, automation, event-routing, workflow-coordination, and execution-triggering architecture of Linkright.

It specifies:

- orchestration philosophy
- automation boundaries
- event systems
- queue systems
- workflow chaining
- trigger architecture
- approval gating
- async processing
- webhook contracts
- automation observability
- retry systems
- automation safety
- future autonomous workflows

This document defines the orchestration layer of Linkright.

---

# 2. Orchestration Philosophy

Linkright should separate:

```text
Orchestration
from
Intelligence Execution
```

Important architectural principle:

```text
n8n orchestrates.
Linkright runtime executes intelligence.
```

This separation is foundational.

---

# 3. Role of n8n

The orchestration layer should primarily manage:

- triggers
- queues
- workflow coordination
- retries
- scheduling
- event routing
- notifications
- async execution
- approval gating
- workflow chaining
- integration coordination

The orchestration layer should avoid:
- owning retrieval logic
- owning semantic reasoning
- owning generation logic
- owning validation systems
- owning ontology semantics

Those belong inside:
- runtime layer
- retrieval systems
- validation systems
- deterministic systems

---

# 4. Event-Driven Architecture

The orchestration layer should be event-driven.

Examples of events:

- JD captured
- opportunity created
- fit score updated
- opportunity state changed
- resume generation completed
- autofill generation completed
- recruiter replied
- interview scheduled
- profile updated
- artifact invalidated
- retry requested
- approval granted

Events should remain:
- explicit
- logged
- replayable
- inspectable

---

# 5. Event Philosophy

Events should represent:
- meaningful state transitions
- workflow triggers
- operational milestones
- execution coordination points

Events should avoid:
- unnecessary noise
- hidden side effects
- implicit transitions

The event system should support:
- observability
- replayability
- debugging
- workflow coordination

---

# 6. Queue Systems

The orchestration layer should support queues.

Possible queues:
- JD scoring queue
- tailoring queue
- autofill-generation queue
- prep-generation queue
- retry queue
- notification queue
- validation queue

Queues should support:
- retries
- prioritization
- batching
- observability
- cancellation
- replayability

---

# 7. Workflow Chaining

n8n should support chained workflows.

Example:

```text
JD Captured
→ Score Opportunity
→ Mark Considering
→ Generate Resume
→ Generate Cover Letter
→ Validate Artifacts
→ Notify User
```

Workflow chains should remain:
- explicit
- inspectable
- modular
- observable

The system should avoid:
- hidden orchestration chains

---

# 8. Trigger Architecture

Workflows may trigger from:
- browser extension events
- CLI actions
- MCP calls
- scheduled jobs
- webhook events
- Gmail events
- manual actions
- workflow completions
- state transitions

Triggers should remain:
- inspectable
- replayable
- deterministic where possible

---

# 9. Opportunity-Centric Automation

Automations should generally attach to opportunities.

Examples:

Opportunity state:
```text
Considering
```

May trigger:
- tailoring workflows
- prep workflows
- recruiter analysis
- company intelligence generation

Opportunity-centric orchestration helps preserve:
- operational clarity
- lineage
- contextual consistency

---

# 10. Workflow State Coordination

Orchestration should coordinate:
- primary lifecycle states
- sub-workflow states
- retries
- approvals
- invalidations
- downstream dependencies

Workflow state coordination should remain:
- explicit
- observable
- replayable

---

# 11. Approval Gating

Certain workflows should require approval.

Examples:
- application submission
- recruiter communication
- profile mutations
- aggressive reframing
- automated networking
- compensation communication

Approval systems improve:
- trust
- safety
- controllability
- explainability

The orchestration layer should support:
- pause states
- approval states
- escalation states

---

# 12. Async Processing

Many workflows should support asynchronous execution.

Examples:
- batch JD scoring
- artifact rendering
- prep generation
- retrieval-heavy workflows
- browser automation

Async workflows should support:
- progress tracking
- retries
- resumability
- observability
- cancellation

---

# 13. Retry Philosophy

Retries should remain explicit.

Retries may occur because:
- provider failure
- timeout
- validation failure
- orchestration interruption
- network issues
- rendering issues
- queue interruptions

Retries should preserve:
- logs
- retry reasons
- lineage
- partial outputs where useful

The system should avoid:
- hidden infinite retry loops

---

# 14. Scheduled Workflows

The orchestration layer may support scheduled workflows.

Examples:
- daily job discovery
- trend analysis
- diary summarization
- stale artifact refresh
- recruiter follow-up reminders
- profile enrichment
- learning summaries

Scheduled workflows should remain:
- observable
- interruptible
- configurable

---

# 15. Webhook Contracts

The orchestration layer should support webhook-based execution.

Possible webhook sources:
- browser extension
- Gmail
- LinkedIn workflows
- future APIs
- browser automation systems
- external integrations

Webhook contracts should remain:
- structured
- version-aware
- observable
- replayable

---

# 16. Integration Philosophy

n8n should coordinate integrations.

Possible integrations:
- Gmail
- Apollo
- Clay
- browser automation systems
- spreadsheets
- databases
- future ATS systems
- future CRM systems

The orchestration layer should avoid embedding:
- core business logic
- semantic reasoning
- retrieval internals

---

# 17. Browser Automation Coordination

The orchestration layer may eventually coordinate:
- browser automation agents
- autofill flows
- recruiter workflows
- UI interactions
- application-state synchronization

Examples:
- automated application drafting
- recruiter outreach assistance
- opportunity-state updates

However:
Phase 1 should prioritize:
- observability
- approval gating
- low-risk automation

---

# 18. Multi-Agent Compatibility

The orchestration layer may eventually coordinate:
- multiple runtime workers
- specialized agents
- browser agents
- retrieval agents
- validation agents
- communication agents

The orchestration layer should remain:
- modular
- inspectable
- interruptible

---

# 19. Automation Safety

Automation systems should prioritize:
- user visibility
- explicit approval boundaries
- replayability
- observability
- failure visibility

The system should avoid:
- opaque autonomous behavior
- uncontrolled messaging
- uncontrolled submissions
- hidden profile mutations

Trust is foundational.

---

# 20. Automation Observability

All orchestrated workflows should emit:
- triggers
- workflow chain
- execution states
- retries
- approvals
- downstream dependencies
- artifact references
- failure logs
- timing information

Automation observability is not optional.

---

# 21. Automation Logs

Automation logs should preserve:
- workflow history
- trigger history
- retry history
- approval history
- execution lineage
- state transitions

Logs should remain:
- structured
- replayable
- inspectable

---

# 22. Failure Philosophy

Automation failures should remain visible.

The system should avoid:
- hidden failures
- silent workflow corruption
- orphaned states
- hidden retries

Failures should preserve:
- logs
- retryability
- lineage
- partial progress where useful

---

# 23. Workflow Invalidations

Some events may invalidate downstream workflows.

Examples:
- profile update
- corrected metrics
- updated opportunity
- revised retrieval
- updated signals

The orchestration layer should support:
- stale marking
- dependency tracking
- regeneration triggers
- invalidation propagation

---

# 24. Multi-Surface Coordination

The orchestration layer should coordinate:
- CLI runtime
- browser extension
- MCP systems
- databases
- external integrations
- future APIs

The orchestration layer should not duplicate:
- runtime intelligence
- retrieval systems
- validation systems

---

# 25. Human-in-the-Loop Philosophy

The orchestration system should remain:
- human-supervised
- approval-aware
- interruptible

Especially for:
- communication
- applications
- networking
- negotiation
- profile changes

Automation should assist first.

---

# 26. Future Automation Evolution

Future orchestration capabilities may include:
- autonomous application systems
- recruiter follow-up systems
- networking automation
- organization intelligence workflows
- contextual career guidance
- recruiter-behavior adaptation
- relationship intelligence
- ecosystem intelligence

These are future layers.

Phase 1 should prioritize:
- workflow stability
- observability
- replayability
- explicit orchestration
- safe automation

---

# 27. Orchestration Boundaries

This document defines:
- orchestration philosophy
- event architecture
- workflow coordination
- automation boundaries
- queue systems
- trigger systems

It does not define:
- retrieval internals
- ontology semantics
- runtime internals
- layout-engine internals
- semantic generation internals

Those belong to other documents.

---

# 28. Document Dependencies

This document depends on:
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 09 — Browser Extension & Ambient Intelligence Layer

This document influences:
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document should be treated as the canonical orchestration and automation architecture reference for Linkright.

