# DOC 08 — CLI Runtime, MCP & Execution Layer

## 1. Purpose

This document defines the runtime, execution, orchestration boundaries, and agent interoperability layer of Linkright.

It specifies:

- CLI architecture philosophy
- execution runtime design
- command contracts
- MCP integration philosophy
- local-first execution
- execution contexts
- provider orchestration
- artifact handling
- replay execution
- runtime observability
- execution boundaries
- agent interoperability
- execution lifecycle semantics

This document defines the operational execution substrate of Linkright.

---

# 2. Runtime Philosophy

Linkright should behave like:
- a local-first professional intelligence runtime
- a deterministic execution substrate
- a workflow execution engine
- an agent-compatible tool system

The runtime is not:
- merely a chatbot wrapper
- merely a UI application
- merely an orchestration layer

The runtime is the core execution environment for:
- retrieval
- generation
- validation
- optimization
- artifact rendering
- workflow execution

---

# 3. CLI-First Philosophy

Phase 1 should prioritize a CLI-first architecture.

Reasons:
- explicit workflows
- observability
- replayability
- low UX overhead
- fast iteration
- architecture flexibility
- local-first execution
- power-user efficiency
- automation compatibility

The CLI is not only a developer tool.

It is:
- an operational interface
- an execution substrate
- a future automation primitive

---

# 4. Execution Philosophy

The runtime should execute:
- deterministic workflows
- retrieval pipelines
- generation pipelines
- validation systems
- optimization loops
- rendering systems
- orchestration-compatible operations

The runtime should avoid:
- hidden execution
- opaque state transitions
- uncontrolled side effects

Execution should remain:
- inspectable
- replayable
- traceable
- composable

---

# 5. Runtime Responsibilities

The runtime may handle:

- retrieval execution
- strategic scoring
- generation execution
- validation execution
- width optimization
- PDF generation
- LaTeX rendering
- artifact persistence
- workflow execution
- provider orchestration
- local caching
- observability emission
- replay execution
- MCP exposure

The runtime should remain:
- modular
- deterministic where possible
- composable

---

# 6. Runtime Boundaries

Important architectural principle:

```text
n8n orchestrates.
Linkright runtime executes intelligence.
```

Meaning:

The runtime owns:
- intelligence execution
- retrieval
- generation
- validation
- optimization
- artifact production
- scoring

The orchestration layer owns:
- triggers
- scheduling
- retries
- workflow coordination
- queues
- notifications
- event routing

This separation is critical.

---

# 7. Command Philosophy

CLI commands should eventually behave like:
- reusable workflow primitives
- orchestration-compatible operations
- agent-callable execution units

Commands should:
- have explicit contracts
- have explicit inputs
- have explicit outputs
- emit structured logs
- preserve replayability

Commands should avoid:
- hidden mutations
- uncontrolled global state

---

# 8. Command Structure

Commands may include:

```text
linkright capture
linkright score
linkright tailor
linkright critique
linkright fill
linkright prep
linkright explain
```

Commands should remain:
- composable
- modular
- inspectable
- automation-compatible

Commands should support:
- machine execution
- human execution
- orchestration execution
- future agent execution

---

# 9. Execution Contexts

Runtime execution should support multiple contexts.

Examples:
- local CLI execution
- orchestration-triggered execution
- extension-triggered execution
- MCP execution
- future API execution
- future autonomous-agent execution

Execution contexts should share:
- canonical memory
- canonical retrieval
- canonical workflows
- canonical observability

The system should avoid fragmented logic across execution contexts.

---

# 10. Local-First Philosophy

The runtime should prioritize local-first execution where practical.

Advantages:
- observability
- reproducibility
- lower latency
- privacy
- operational control
- offline compatibility where possible
- deterministic debugging

Local-first does not necessarily mean:
- fully offline

The runtime may still use:
- remote models
- cloud storage
- remote orchestration
- external APIs

But the execution substrate should remain controllable.

---

# 11. Provider Orchestration

The runtime may support multiple providers.

Examples:
- OpenAI
- Claude
- Gemini
- local models
- future custom models

Provider orchestration may consider:
- quality
- latency
- cost
- reliability
- context-window requirements
- strategic generation quality
- model-specific strengths

Provider orchestration should remain:
- observable
- configurable
- replayable

---

# 12. Hybrid Execution Philosophy

Different runtime stages may use:
- deterministic systems
- embeddings
- heuristics
- LLM reasoning
- semantic optimization loops
- retrieval pipelines
- rendering engines

The runtime should use:
- the best execution strategy for each stage

not:
- a single universal execution mechanism.

---

# 13. Artifact Runtime

The runtime should manage:
- artifact generation
- artifact persistence
- artifact lineage
- artifact retrieval
- artifact replayability
- artifact validation

Artifacts should remain:
- traceable
- reproducible
- inspectable

---

# 14. Run System

Every major execution should create a run.

Runs should preserve:
- inputs
- outputs
- workflow chain
- retrieval context
- provider usage
- validation outputs
- optimization loops
- generated artifacts
- timestamps
- replay metadata

Example:

```text
~/.linkright/runs/<id>/
```

The run system becomes the execution memory of Linkright.

---

# 15. Replayability

The runtime should support replay execution.

Replayability is critical for:
- debugging
- experimentation
- trust
- observability
- optimization tuning
- architecture iteration

Replayability should preserve:
- workflow chain
- retrieval chain
- provider selection
- validation outputs
- layout constraints
- profile versions

---

# 16. MCP Philosophy

Linkright should support MCP-compatible execution.

The runtime should expose:
- retrieval operations
- generation operations
- scoring operations
- artifact operations
- workflow operations
- explanation operations

This allows:
- external agents
- future autonomous systems
- workflow interoperability
- agent-tool ecosystems

The runtime should become:
- agent-compatible infrastructure

not merely:
- a closed application.

---

# 17. MCP Boundaries

MCP exposure should remain controlled.

The runtime should preserve:
- execution safety
- approval checkpoints
- observability
- traceability
- permission boundaries

Not all operations should become:
- unrestricted autonomous actions.

---

# 18. Observability

The runtime should emit:
- execution traces
- retrieval rationale
- provider usage
- optimization steps
- validation outputs
- timing information
- retry history
- artifact lineage
- error information

Observability is a first-class runtime concern.

---

# 19. Runtime Logging

Runtime logs should remain:
- structured
- replayable
- machine-readable
- human-inspectable

Logs should support:
- debugging
- workflow analysis
- optimization analysis
- retrieval explainability
- failure diagnosis

---

# 20. Runtime Failure Philosophy

Failures should remain visible.

The runtime should avoid:
- hidden retries
- silent corruption
- partial hidden state mutations
- opaque failures

Failures should preserve:
- logs
- partial outputs where useful
- retryability
- replayability

Users should understand:
- what failed
- why it failed
- what can be retried

---

# 21. Runtime Caching

The runtime may support:
- retrieval caching
- expression caching
- embedding caching
- artifact caching
- provider-response caching
- optimization caching

Caching should preserve:
- lineage
- invalidation semantics
- replayability
- explainability

---

# 22. Environment Handling

The runtime should support:
- API key management
- environment isolation
- profile-specific execution
- provider configuration
- execution configuration

Sensitive data handling should remain:
- explicit
- inspectable
- secure

---

# 23. Multi-Surface Compatibility

The runtime should support multiple operational surfaces:

- CLI
- browser extension
- MCP tools
- orchestration systems
- APIs
- future dashboards
- future autonomous agents

All surfaces should share:
- canonical workflows
- canonical memory
- canonical retrieval
- canonical observability

The runtime should avoid:
- duplicated intelligence logic
- fragmented execution semantics

---

# 24. Browser Automation Compatibility

The runtime may eventually integrate with:
- browser automation systems
- DOM interaction systems
- contextual execution systems
- UI automation systems

Examples:
- application autofill
- recruiter interaction assistance
- workflow-triggered browser actions
- contextual overlays

The runtime should remain compatible with:
- future automation surfaces
without tightly coupling them into the core.

---

# 25. Future Runtime Evolution

Future runtime evolution may include:
- autonomous execution loops
- distributed execution
- local agent swarms
- workflow simulation
- recruiter interaction automation
- social automation
- organizational intelligence systems
- contextual operating systems

These are future layers.

Phase 1 should prioritize:
- stable execution
- replayability
- observability
- modularity
- deterministic contracts

---

# 26. Runtime Boundaries

This document defines:
- execution philosophy
- CLI architecture
- runtime semantics
- MCP philosophy
- execution boundaries
- replayability philosophy

It does not define:
- ontology semantics
- retrieval internals
- layout-engine internals
- UI rendering implementation
- orchestration workflow implementation

Those belong to other documents.

---

# 27. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 07 — Deterministic Engines & Validation Systems

This document influences:
- DOC 09 — Browser Extension & Ambient Intelligence Layer
- DOC 10 — n8n Orchestration & Automation Architecture
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document should be treated as the canonical runtime and execution architecture reference for Linkright.

