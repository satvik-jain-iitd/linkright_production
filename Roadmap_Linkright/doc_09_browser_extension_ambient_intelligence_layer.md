# DOC 09 — Browser Extension & Ambient Intelligence Layer

## 1. Purpose

This document defines the browser-extension architecture, contextual intelligence surfaces, ambient assistance philosophy, and browser-interaction layer of Linkright.

It specifies:

- extension philosophy
- contextual intelligence overlays
- browser interaction architecture
- contextual retrieval behavior
- ATS integrations
- autofill systems
- Gmail overlays
- LinkedIn integrations
- browser automation compatibility
- contextual observability
- copilot interaction models
- future ambient-agent evolution

This document defines the ambient intelligence layer of Linkright.

---

# 2. Extension Philosophy

The browser extension is not the core intelligence engine.

The extension should primarily behave as:
- contextual sensor layer
- contextual rendering layer
- lightweight command surface
- contextual copilot

Core intelligence should remain inside:
- runtime layer
- retrieval systems
- orchestration systems
- memory systems
- validation systems

This separation is critical.

---

# 3. Ambient Intelligence Philosophy

Linkright should eventually behave like:

```text
Ambient professional intelligence.
```

Meaning:
- intelligence appears contextually
- workflows adapt to user context
- assistance appears where useful
- friction remains low

The system should reduce:
- context switching
- cognitive overhead
- repetitive work
- retrieval effort

The system should increase:
- strategic leverage
- response quality
- contextual awareness
- workflow continuity

---

# 4. Copilot-First Philosophy

Phase 1 should prioritize:

```text
Active copilot behavior
```

The extension should:
- assist
- recommend
- explain
- accelerate
- contextualize

The extension should not initially:
- silently automate
- aggressively take control
- perform opaque autonomous behavior

Autonomy should increase gradually after:
- workflow stability
- observability maturity
- user trust
- operational reliability

---

# 5. Extension Responsibilities

The extension may handle:

- JD capture
- page-context extraction
- contextual overlays
- autofill assistance
- recruiter-context rendering
- contextual retrieval requests
- quick workflow launching
- opportunity-state visibility
- quick artifact access
- lightweight observability views
- contextual AI assistance

The extension should avoid:
- owning core intelligence logic
- fragmented retrieval logic
- hidden orchestration behavior

---

# 6. Contextual Intelligence Surfaces

The extension should provide contextual intelligence based on:
- current page
- current workflow
- opportunity state
- user profile
- recruiter context
- retrieval context

Examples:

LinkedIn:
- opportunity scoring
- fit analysis
- resume recommendations
- recruiter-risk indicators
- quick tailoring actions

ATS forms:
- autofill assistance
- answer suggestions
- retrieval-backed responses
- confidence visibility

Gmail:
- recruiter context
- response drafting
- opportunity linkage
- communication history

---

# 7. Context Awareness

The extension should adapt behavior based on:
- active website
- current workflow stage
- user intent
- opportunity lifecycle state
- active retrieval context

Examples:

LinkedIn page:
- opportunity intelligence

Gmail:
- recruiter interaction intelligence

ATS page:
- autofill copilot

Interview calendar event:
- prep guidance

Contextual adaptation is a foundational ambient-intelligence capability.

---

# 8. JD Capture System

The extension should support JD capture workflows.

Possible capabilities:
- structured extraction
- metadata extraction
- company extraction
- compensation extraction if available
- location extraction
- skills extraction
- opportunity creation
- duplicate detection

Capture workflows should support:
- batching
- passive capture
- explicit approval flows
- observability

---

# 9. Passive Capture Mode

The extension may support passive-capture workflows.

Example:

```text
User activates capture mode
→ browses multiple JDs
→ opportunities automatically created
→ opportunities queued for scoring
```

Passive capture should remain:
- visible
- controllable
- interruptible

The system should avoid:
- invisible mass collection
- hidden automation

---

# 10. Opportunity Overlay System

Opportunity pages may display:

- fit score
- recruiter-fit analysis
- strategic recommendations
- missing signals
- role archetype analysis
- resume recommendations
- company intelligence
- workflow status
- artifact availability

Overlays should:
- remain lightweight
- avoid visual overload
- prioritize high-value information

---

# 11. Contextual Retrieval

The extension should support contextual retrieval.

Meaning:
retrieval should incorporate:
- current page
- opportunity context
- current workflow
- current artifact
- active recruiter interaction

The extension should not independently implement retrieval logic.

Instead:
- contextual signals
should be passed into:
- runtime retrieval systems

---

# 12. Autofill Assistance

The extension may support:
- AI-assisted autofill
- retrieval-backed answers
- one-click insertion
- confidence visibility
- answer explanations
- recruiter-aware adaptation

Autofill systems should optimize for:
- speed
- defensibility
- recruiter readability
- identity consistency

Autofill should remain:
- inspectable
- editable
- interruptible

---

# 13. Ask-AI Interaction Layer

The extension may support contextual Ask-AI workflows.

Examples:

```text
What should I say in HR intro?
```

```text
Why is this role a good fit?
```

```text
Generate concise answer for this field.
```

Ask-AI should use:
- opportunity context
- profile context
- retrieval systems
- canonical memory
- workflow context

Ask-AI should avoid:
- generic stateless answers
- isolated prompt-only reasoning

---

# 14. Gmail Integration Philosophy

Gmail integration should likely arrive after:
- stable opportunity workflows
- stable observability
- strong trust foundations

Reasons:
- permission sensitivity
- privacy sensitivity
- onboarding complexity
- trust burden

Future Gmail support may include:
- recruiter threading
- response drafting
- opportunity linkage
- communication tracking
- interview coordination

---

# 15. LinkedIn Integration

The extension may support:
- opportunity capture
- recruiter-context overlays
- networking context
- quick-tailor workflows
- fit analysis
- company intelligence

The extension should avoid:
- brittle DOM assumptions
- excessive coupling to platform-specific layouts

---

# 16. ATS Integration Philosophy

ATS integrations should prioritize:
- reliability
- contextual usefulness
- low-friction workflows
- explainability

ATS integrations may include:
- autofill assistance
- answer retrieval
- application tracking
- field-aware generation
- application-state synchronization

The extension should avoid:
- unsafe hidden automation
- silent submissions

---

# 17. Extension Observability

The extension should expose lightweight observability.

Examples:
- workflow progress
- retrieval rationale
- opportunity state
- artifact status
- autofill confidence
- workflow logs

Users should understand:
- what the extension is doing
- why it is doing it
- which workflows were triggered

---

# 18. Logging Philosophy

Extension actions should emit:
- capture events
- workflow triggers
- contextual metadata
- interaction metadata
- overlay actions
- autofill actions
- approval actions

Logs should remain:
- structured
- replayable where useful
- inspectable

---

# 19. UI Philosophy

The extension UI should prioritize:
- low cognitive load
- contextual usefulness
- minimal disruption
- fast access
- observability

Possible interaction models:
- overlays
- side panels
- command palette
- lightweight popups
- contextual inline actions

The extension should avoid:
- clutter
- excessive persistent UI
- noisy automation

---

# 20. Keyboard-First Support

The extension should eventually support:
- keyboard workflows
- quick actions
- command-palette interaction
- power-user navigation

Examples:

```text
Ctrl+Shift+L
→ open Linkright command palette
```

Power-user ergonomics may become important later.

---

# 21. Browser Automation Compatibility

The extension should remain compatible with:
- future browser automation systems
- DOM automation systems
- agentic browser workflows
- MCP-triggered browser actions

Examples:
- application autofill
- recruiter-message drafting
- application-state synchronization
- contextual UI augmentation

However:
Phase 1 should prioritize:
- contextual assistance
not:
- aggressive autonomous control

---

# 22. Ambient Agent Evolution

Future evolution may include:
- proactive recommendations
- recruiter-response drafting
- contextual interview prep
- workflow prediction
- opportunity prioritization
- automated follow-ups
- contextual career coaching

This becomes:
- ambient professional intelligence

But this should evolve gradually.

Trust and observability remain critical.

---

# 23. Privacy & Trust Philosophy

The extension should:
- minimize unnecessary permissions
- preserve user visibility
- preserve explicit control
- preserve approval boundaries

The extension should avoid:
- opaque background actions
- uncontrolled browsing analysis
- hidden external transmission

Trust is foundational.

---

# 24. Multi-Surface Coordination

The extension should coordinate with:
- runtime layer
- orchestration systems
- canonical memory
- retrieval systems
- artifact systems
- observability systems

The extension should not create:
- fragmented memory
- fragmented retrieval
- fragmented workflows

---

# 25. Future Extension Evolution

Future extension capabilities may include:
- contextual negotiation support
- networking intelligence
- recruiter-behavior analysis
- career trajectory guidance
- organization-specific overlays
- multi-tab workflow coordination
- relationship intelligence
- ambient interview preparation

These are future layers.

Phase 1 should prioritize:
- JD capture
- contextual overlays
- autofill support
- workflow visibility
- observability
- low-friction interaction

---

# 26. Extension Boundaries

This document defines:
- browser-extension philosophy
- contextual intelligence architecture
- ambient-assistance philosophy
- contextual interaction systems

It does not define:
- retrieval internals
- ontology semantics
- deterministic layout engines
- runtime internals
- orchestration implementation

Those belong to other documents.

---

# 27. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 08 — CLI Runtime, MCP & Execution Layer

This document influences:
- DOC 10 — n8n Orchestration & Automation Architecture
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document should be treated as the canonical browser-extension and ambient-intelligence reference for Linkright.

