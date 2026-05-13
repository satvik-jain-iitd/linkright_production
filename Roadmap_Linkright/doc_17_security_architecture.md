# DOC 17 — Security Architecture

## 1. Purpose

This document defines the security architecture for Linkright.

It specifies:

- threat model
- local data security
- LLM provider isolation
- prompt injection defense
- cloud encryption design
- CLI runtime safety
- audit and alerting
- key rotation
- non-goals

This document governs how Linkright protects user career data at rest, in transit, and during AI processing.

---

## 2. Security Philosophy

Linkright handles sensitive personal career data: work history, compensation signals, rejection history, interview performance, and private professional context.

The security model follows three principles:

- the user owns the data and the key
- the system never transmits more than a task requires
- local is the default; cloud is the opt-in exception

Security is not a compliance checkbox.

It is a prerequisite for user trust.

A system that exposes a user's salary history or rejection record to third-party providers — even incidentally — is not a credible career copilot.

---

## 3. Threat Model

The system defends against five primary threats.

### 3.1 Unauthorized Access to Local Career Data

An attacker with filesystem access (local or via malware) should not be able to read the user's career profile, signals, outcomes, or opportunity notes in plaintext.

Defense:
- `~/.linkright/` directory permissions set to 700 on creation (owner read/write/execute only)
- no sensitive data written in plaintext outside the local directory
- API keys and encryption keys stored in OS keychain, not in config JSON files
- config files contain only non-sensitive settings (routing preferences, provider names)

### 3.2 LLM Provider Seeing the Full Profile

When a generation call is made to an external LLM provider, only the minimum necessary context should travel outside the device.

Defense:
- prompt construction extracts task-relevant signals and the relevant JD fragment only
- full canonical profile is never serialized into a prompt
- salary data, rejection history, and outcome events are never included in any LLM call
- provider calls are scoped: a bullet generation call receives bullet-level context, not career-level context

This is consistent with the local-first philosophy in DOC 08 and the data boundary rules in DOC 13.

### 3.3 Cloud Backup Breach

If MongoDB cloud backup is compromised at the storage level, the attacker should find only encrypted blobs.

Defense:
- all data is encrypted locally before any push (AES-256-GCM)
- MongoDB receives ciphertext, initialization vectors, and schema versions only
- plaintext data never leaves the device
- the encryption key is stored in the user's OS keychain and is never transmitted
- if the cloud is breached, decryption without the user's key is computationally infeasible

### 3.4 Malicious JD Injection Into Prompts

A maliciously crafted job description could attempt to override system behavior via prompt injection — embedding instructions that manipulate resume generation, exfiltrate profile data, or alter LLM behavior.

Defense:
- JD content is treated as untrusted external input at all times
- JD text is sanitized before insertion into any prompt (control characters, unusual unicode, embedded instruction patterns removed)
- system prompt and user content are structurally separated — JD text is never placed in the system role
- JD-derived fields (keywords, requirements) are extracted deterministically before being used in generation calls, not passed as raw text

### 3.5 Exfiltration via Generated Artifacts

A generated resume or cover letter could theoretically be manipulated to encode or leak sensitive profile information in the artifact itself.

Defense:
- generated artifacts are validated against expected schema before export
- output validation checks for anomalous content length, unexpected sections, or metadata leakage
- artifact generation is a terminal step: the artifact receives formatted output only, not raw profile state

---

## 4. Local Security

Key rules for the local environment:

- `~/.linkright/` is created with permissions 700
- no API keys are written to any JSON config file; all credentials use the OS keychain
- `provider_config.json` stores provider names and routing preferences only
- `user_config.json` stores display and workflow preferences only
- no plaintext profile data is written to disk outside the authorized directory structure
- run logs and trace files do not contain raw API keys, encryption keys, or full profile snapshots

---

## 5. LLM Provider Isolation

LLM providers are external services.

The system must treat them as partially untrusted infrastructure.

Rules:
- each LLM call receives only the context required for that specific task
- bullet generation receives: bullet drafts, JD keywords, width constraints, archetype context
- it does NOT receive: full profile JSON, salary fields, outcome history, rejection data
- prompt templates are reviewed for inadvertent full-profile serialization before use
- if a generation task requires more context than a minimum-context design allows, the architecture should be decomposed into smaller calls rather than widening the context

The goal is not paranoia.

The goal is discipline: every provider call should be inspectable and its data footprint should be explainable.

---

## 6. Prompt Injection Defense

JD content originates from external sources (scrapers, user paste, browser extension captures).

It must be treated as untrusted input.

Defense layers:
- sanitization at ingest: JD text is normalized on capture, not at prompt construction time
- structural separation: JD text is never injected into the system role of any prompt; it always occupies clearly bounded user content fields
- field extraction before use: keywords, requirements, and signals are extracted from JD text deterministically; raw JD text is used only for display and diagnostic purposes
- anomaly detection: prompt construction logs warning if JD-derived content exceeds expected field lengths or contains high-entropy token sequences

---

## 7. Cloud Encryption Design

Cloud sync is governed by end-to-end encryption with user-held keys.

The full encryption model is defined in DOC 13.

Security-relevant summary:
- encryption algorithm: AES-256-GCM
- key storage: OS keychain exclusively; never in any file
- key transmission: never; the key never leaves the device
- MongoDB receives: encrypted blob, nonce (IV), schema version, and a non-reversible user hash
- decryption: happens locally after pull; the cloud layer has no decryption capability
- TLS: all MongoDB communication uses TLS in transit

Loss of the encryption key means cloud data is permanently unrecoverable.

The system must warn explicitly before any key destruction operation.

---

## 8. CLI Runtime Safety

The CLI runtime should not introduce code execution vulnerabilities.

Rules:
- no `eval()` or equivalent dynamic code execution in command handling
- subprocess calls use argument arrays, not shell strings; shell injection is not possible by construction
- file path inputs from users are validated and canonicalized before use
- no dynamic module loading from user-supplied paths
- plugin or extension interfaces (future) require explicit user permission grants, not ambient execution

---

## 9. Audit and Alerting

The system should maintain a local access audit log.

The audit log records:
- bulk export operations
- cloud sync push/pull events
- encryption key access events
- profile mutation events (especially batch changes)
- LLM call metadata (provider, task type, timestamp — not content)

Anomalous patterns that should surface warnings to the user:
- unusually large number of profile mutations in a short window
- bulk export followed immediately by external network activity (future detection)
- repeated failed decryption attempts (suggests wrong key or key mismatch)

The user can review the audit log:

```text
linkright audit log
linkright audit log --since <date>
```

The audit log does not contain prompt content or profile data.

It is a structural event record only.

---

## 10. Key Rotation

The user can rotate their encryption key at any time.

Rotation procedure:
1. user runs `linkright security rotate-key`
2. system decrypts all local encrypted data with the old key
3. system re-encrypts all data with the new key
4. if cloud sync is enabled, system pushes re-encrypted blobs to MongoDB
5. system updates the OS keychain with the new key
6. system purges the old key from the keychain after verifying successful re-encryption

Rotation is an atomic local operation.

The old key is not deleted until the new key has successfully re-encrypted and verified all data.

If rotation fails partway through, the system preserves the old key and surfaces a recovery path.

---

## 11. Non-Goals

This document explicitly does not cover:

- multi-user security models: Linkright is a single-user local tool; there is no user-separation, role-based access control, or tenant isolation
- enterprise SSO: authentication is handled via OS keychain and direct API key management; no SAML, OIDC, or enterprise identity integration
- zero-trust network architecture: the system uses standard TLS and does not implement mTLS, service meshes, or network-level segmentation
- malware defense beyond standard filesystem permissions: Linkright does not provide anti-malware, endpoint protection, or process isolation

The security model is appropriate for a local-first personal tool.

It is not designed for shared infrastructure, organizational deployment, or adversarial multi-tenant environments.

---

## 12. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 13 — Storage Infrastructure

This document influences:
- DOC 14 — Canonical Schemas, Entity Contracts & State Models
- DOC 24 — Closed-Loop Learning System

This document should be treated as the canonical security architecture reference for Linkright.
