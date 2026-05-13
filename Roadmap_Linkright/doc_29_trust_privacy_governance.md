# DOC 29 — Trust & Privacy Governance

## 1. Purpose

This document defines the trust model, privacy architecture, and data governance rules for Linkright.

It specifies:

- trust philosophy and design principles
- data classification tiers
- user control requirements
- encryption implementation
- audit trail design
- third-party data boundary rules
- AI authenticity layer
- data deletion behavior
- compliance design

This document governs every decision where user data, system behavior, and user trust intersect.

It should be treated as a constraint layer on all other implementation documents.

---

## 2. Trust Philosophy

Career data is among the most sensitive personal data a person holds.

It includes:
- employment history
- compensation signals
- rejection history
- career vulnerabilities
- professional relationships
- private reflections on work and colleagues

Systems that handle this data must earn trust through demonstrated behavior, not policy statements.

Linkright earns trust through:
- transparency about what is stored and why
- controls that are one command away, not buried in settings
- explicit confirmation before anything significant changes
- zero cloud dependency by default
- never sending more data to third parties than the current task strictly requires

Privacy policies do not create trust.
Behavior creates trust.

---

## 3. Data Classification Tiers

All data handled by Linkright falls into one of four tiers.

### Tier 1 — Never Leaves Device

Data that must never be transmitted to any external system under any circumstances.

Examples:
- raw resume PDFs and uploaded documents
- provider API keys (LLM and embedding providers)
- salary figures, compensation history, equity details
- OS keychain credentials
- browser session tokens
- interview notes containing third-party colleague names

These items are stored locally only.
No sync path, cloud path, or export path touches them.
They are explicitly excluded from backup archives in the default configuration.

### Tier 2 — Encrypted Cloud Only (User Decrypts)

Data that the user may optionally sync to cloud backup.

This tier is opt-in and requires explicit `linkright sync enable`.

Examples:
- canonical career profile
- signal store and weights
- outcome event log
- opportunity records (excluding raw JD HTML)
- artifact metadata and lineage

Cloud storage receives only AES-256-GCM ciphertext.
The decryption key never leaves the user's device.
Cloud operators cannot read this data.

### Tier 3 — Anonymized Analytics

Aggregate usage patterns that may be collected to improve the system.

This tier is opt-in, separate from cloud sync.

Rules:
- no PII included
- no individual run data linked to identity
- only aggregate shapes (e.g. average retrieval latency, signal category distribution)
- user may opt out at any time with no functional consequence

This tier is not active in Phase 1.
It is defined here as a governance constraint for when it is introduced.

### Tier 4 — Public (Explicit User Export)

Artifacts the user has explicitly chosen to export or share.

Examples:
- generated resume PDF exported for submission
- cover letter sent to recruiter
- autofill response submitted via browser extension

This tier is user-initiated only.
The system never automatically publishes or shares any artifact.
Export is a deliberate user action, not a background system behavior.

---

## 4. User Controls

The following controls must be available and must each be executable in a single command.

```text
linkright signal delete <signal_id>        — delete a specific signal + all its embeddings
linkright outcome delete <event_id>        — delete a specific outcome event
linkright profile export                   — export full canonical profile as JSON
linkright sync disable                     — revoke cloud sync and delete cloud copies
linkright reset identity                   — reset identity archetype to initial state
linkright storage audit                    — show what is stored and where
linkright backup export <path>             — create portable local archive
```

No control should require more than one command to initiate.
No destructive control should execute silently — confirmation is required for irreversible operations.

These controls are not optional features.
They are trust infrastructure.

---

## 5. Encryption Implementation

### 5.1 Algorithm

AES-256-GCM is the required algorithm for all encrypted cloud storage.

Properties:
- authenticated encryption (provides integrity check, not just confidentiality)
- nonce-per-operation (a fresh 96-bit nonce is generated for every encryption call)
- tag verification before any decryption is accepted

### 5.2 Key Management

The user holds a single master encryption key.

Key storage:
- macOS: stored in macOS Keychain via `security` CLI or `keyring` Python library
- Linux: stored in libsecret-backed secret service (GNOME Keyring / KWallet)
- Fallback: stored at `~/.linkright/config/keyring.json` with 0600 permissions

The key is never transmitted.
The key is never logged.
The key is never included in backup archives unless the user explicitly requests key export with a separate strong password.

Key loss behavior:
- encrypted cloud data becomes permanently unrecoverable
- local data is unaffected (local data is not encrypted at rest by default)
- the system warns before any key destruction operation
- a key export reminder is surfaced after sync enable

### 5.3 Cloud Encryption Envelope

Every document pushed to MongoDB is wrapped in an encryption envelope:

```text
user_id          string     SHA-256 hash of a user-controlled identifier (not email)
encrypted_blob   bytes      AES-256-GCM ciphertext
iv               bytes      96-bit nonce
tag              bytes      GCM authentication tag
schema_version   integer    schema version at time of push
pushed_at        datetime
```

Raw plaintext is never written to MongoDB at any point.

---

## 6. Audit Trail

Every mutation to the canonical profile, signals, or identity state is logged with full provenance.

### 6.1 What Is Logged

Each mutation log entry captures:

```text
event_id         string     unique identifier
entity_type      string     profile | signal | fact | identity | outcome
entity_id        string     the specific entity changed
mutation_type    enum       created | updated | deleted | merged | stale_marked
source           string     ingestion_workflow | manual_edit | learning_system | sync_pull
prior_version    integer    version before mutation
new_version      integer    version after mutation
changed_fields   []string   field names that changed
user_confirmed   boolean    whether user explicitly confirmed this change
timestamp        datetime
```

### 6.2 User Inspection

The user can inspect the mutation history of any entity:

```text
linkright audit show signal <signal_id>
linkright audit show profile
linkright audit show identity
```

The output answers: why did my profile change, when did it change, and what triggered the change.

This is critical for trust.
Users who cannot understand why their profile changed will not trust the system.

---

## 7. Third-Party Data Boundary

Linkright integrates with external LLM providers (Groq, Claude, Cerebras, Jina, etc.) for generation and embedding tasks.

The following rules govern what data may be sent to external providers.

### 7.1 What May Be Sent

Per-call, only the minimum required for the current task:

- the relevant subset of signals and facts for the current generation task
- the parsed JD (not the raw HTML)
- explicit user-authored prompt context

### 7.2 What Must Never Be Sent

- the full canonical profile as a wholesale dump
- salary or compensation data
- raw uploaded documents
- outcome event history
- identity archetype evolution history
- recruiter contact names or email addresses
- signals not relevant to the current generation task

### 7.3 Enforcement Mechanism

LLM call construction must extract only the relevant subset for the current step.

The retrieval pipeline (DOC 15) exists in part to enforce this boundary.
By retrieving only the signals and facts relevant to the current opportunity before generation, the system naturally limits the context sent to external providers.

This is not just a performance optimization.
It is a trust boundary.

---

## 8. AI Authenticity Layer

Linkright uses LLMs to generate resume bullets, cover letter paragraphs, autofill responses, and interview story seeds.

This creates an obligation to distinguish what came from the user's stated experience versus what was generated.

### 8.1 Provenance Marking

Every generated Expression entity carries:

```text
source_signal_ids    []string   signals that contributed
source_fact_ids      []string   facts that grounded the content
generated            boolean    true for all LLM-generated outputs
user_edited          boolean    true if user modified the generated content
user_edited_version  text       the user's version if edited
```

Generated content that the user has not reviewed is visually marked in the CLI output.

### 8.2 Fabrication Prevention

The generation system operates within constrained semantic space (DOC 05, Section 16).

The system must not:
- invent metrics not present in any source fact
- claim experiences not traceable to at least one evidence entity
- generate signal assertions with zero supporting facts

If the system cannot ground a claim, it must surface it as a placeholder with explicit low-confidence marking.

The metric placeholder system (linkright resume fill-metrics) exists specifically for this case: the user provides real numbers, the system does not manufacture them.

### 8.3 Authenticity Guard

Before finalizing any generated output, the system checks:

- every factual claim is traceable to a fact with `user_confirmed = true`
- no metric value appears in the output unless it appears in a source fact
- no role, company, or project name appears unless it matches the canonical profile

Violations surface as warnings, not silent failures.
The user reviews and resolves before the artifact is finalized.

This design is consistent with the AI-era authenticity principles established in the research corpus: generated content amplifies the user's real experience; it does not replace or fabricate it.

---

## 9. Data Deletion

### 9.1 Full Cascade Delete

When a user initiates `linkright profile delete --full`, the system executes:

1. Delete all JSON files under `~/.linkright/`
2. Drop all SQLite tables
3. Clear the embedding cache
4. Clear the retrieval cache
5. Clear all run logs
6. If cloud sync is active: delete all documents from all MongoDB collections for this user
7. Remove the encryption key from the OS keychain

The operation is irreversible.
The system requires explicit confirmation with a typed phrase before executing.

### 9.2 No Soft-Delete Retention

Linkright does not retain soft-deleted data in hidden collections or backup slots after a user-initiated delete.

There is no 30-day grace period.
There is no recovery path after confirmed deletion.
This is by design.

The user owns the data.
When they delete it, it is gone.

### 9.3 Partial Delete

Users may delete individual entities without full profile deletion:

```text
linkright signal delete <id>      — removes signal + embeddings + all expressions referencing it
linkright outcome delete <id>     — removes one outcome event
linkright evidence delete <id>    — removes evidence entity + all derived facts marked stale
```

Cascade rules ensure no orphaned references remain after partial deletion.

---

## 10. Compliance Design

Linkright satisfies GDPR right-to-erasure and data portability requirements by architecture, not by process.

**Right to erasure:**
Local-first means the user already holds all their data.
`linkright profile delete --full` executes a complete cascade delete across local and cloud.
No request to a data controller is required.

**Data portability:**
`linkright profile export` produces a complete, machine-readable JSON export of the canonical profile, signals, facts, and outcome history.
This export is in an open format with documented schemas (DOC 14).

**Purpose limitation:**
Data collected for career navigation is not used for any other purpose.
No analytics are run against user data without explicit opt-in.
No user data is used to train models or improve external provider outputs.

---

## 11. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 13 — Storage Infrastructure
- DOC 14 — Canonical Schemas, Entity Contracts & State Models

This document influences:
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 15 — Retrieval Implementation
- DOC 24 — Closed-Loop Learning System

This document should be treated as the canonical trust and privacy governance reference for Linkright.
