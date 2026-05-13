# DOC 13 — Storage Infrastructure

## 1. Purpose

This document defines the storage infrastructure architecture for Linkright.

It specifies:

- storage philosophy
- local storage design and path conventions
- cloud storage design and encryption model
- sync protocol
- vector search architecture
- data boundary rules
- backup and restore strategy
- separation from website and Oracle systems

This document is part of Layer 5A — Infrastructure & Contracts.

It governs how data is stored, protected, synced, and recovered.

It does not define retrieval implementation, schema contracts, or rendering systems.

Those belong to DOC 15 and DOC 14 respectively.

---

## 2. Storage Philosophy

Linkright uses a two-tier storage model.

```text
Local JSON + SQLite          ← authoritative
MongoDB encrypted cloud      ← optional backup
```

The local tier is always authoritative.

The cloud tier is never the primary source of truth.

It exists for:
- disaster recovery
- multi-device continuity
- optional semantic search assistance

This design means:
- the system works fully offline
- the user owns their data at all times
- cloud sync is opt-in and encrypted
- cloud loss or unavailability does not break core workflows

This is consistent with the privacy-first and local-first principles in DOC 01.

---

## 3. Local Storage

### 3.1 Storage Location

All local Linkright data lives under:

```text
~/.linkright/
```

This directory is the user's authoritative data home.

It should be:
- created automatically on first run
- protected from accidental deletion
- excluded from shared file systems by default

### 3.2 Directory Structure

```text
~/.linkright/
  profile/
    canonical_profile.json         # current canonical profile state
    profile_history/               # versioned profile snapshots
      profile_v001.json
      profile_v002.json
      ...
  signals/
    signal_store.json              # all active signals with metadata
    signal_weights.json            # current weight state for retrieval ranking
  opportunities/
    opportunity_log.sqlite         # opportunity lifecycle tracking database
    <opportunity_id>/              # one directory per opportunity
      raw_jd.txt
      parsed_jd.json
      resume_versions/
      artifacts/
  outcomes/
    outcome_events.jsonl           # append-only outcome event log
  cache/
    embeddings/                    # local embedding cache
    retrieval/                     # retrieval result cache
  logs/
    run_logs/                      # structured execution logs per run
  config/
    user_config.json               # user settings and preferences
    provider_config.json           # LLM and embedding provider routing
  sync/
    sync_state.json                # cloud sync cursor and state
    pending_push.jsonl             # events queued for cloud push
```

### 3.3 What Lives in JSON vs SQLite

JSON is used for:
- canonical profile
- signals and weights
- configuration
- sync state
- outcome events (append-only log)

SQLite is used for:
- opportunity lifecycle tracking
- multi-field query needs
- structured event history
- run metadata

The distinction is:
- JSON for authoritative write-once or slow-evolving records
- SQLite for queryable, relational, multi-record state

---

## 4. Cloud Storage

### 4.1 When Cloud Sync Is Used

Cloud sync is optional.

A user activates it explicitly via:

```text
linkright sync enable
```

Once enabled:
- local changes push to MongoDB on a defined schedule
- the cloud stores encrypted blobs
- the user can restore from cloud to any device

Without enabling: the system remains fully local.

### 4.2 MongoDB as Cloud Tier

MongoDB Community Edition is used for cloud backup.

MongoDB is chosen because:
- document model matches Linkright's JSON-native data
- built-in vector search support (for optional cloud-assisted semantic search)
- operator-friendly self-hosted option
- adequate free tier for personal use

MongoDB is NOT used as a live operational database.

It is a backup and optional retrieval substrate.

### 4.3 Collections

```text
profiles             # encrypted canonical profile documents
signals              # encrypted signal store and weights
outcome_events       # encrypted outcome event log
opportunities        # encrypted opportunity records
vector_store         # document vectors (see section 6)
```

Each document in the encrypted collections is stored as:

```text
{
  user_id: <hash>,
  encrypted_blob: <AES-256-GCM ciphertext>,
  iv: <nonce>,
  schema_version: <version>,
  pushed_at: <timestamp>
}
```

Raw plaintext data is never written to MongoDB.

### 4.4 Encryption Design

End-to-end encryption is required for all cloud-stored data.

Design:
- the user generates and holds a master encryption key
- the key is stored locally at `~/.linkright/config/keyring.json` (or OS keychain)
- before any push, data is encrypted locally using AES-256-GCM
- MongoDB receives only encrypted blobs
- decryption happens locally after pull

The cloud cannot read user data.

MongoDB operators cannot access profile content, signals, outcomes, or opportunity details.

If the user loses their key:
- cloud data becomes unrecoverable
- this is a documented and explicit tradeoff
- the system should warn before key destruction

### 4.5 Sync Protocol

Push behavior:
- triggered manually via `linkright sync push`
- optionally triggered automatically on significant events (profile update, opportunity closed, outcome recorded)
- pushes incremental deltas using the sync cursor in `sync_state.json`
- pushes from `pending_push.jsonl` queue

Pull behavior:
- triggered manually via `linkright sync pull`
- pulls all collections newer than the local sync cursor
- decrypts locally
- applies to local state using merge semantics (see section 4.6)

### 4.6 Conflict Resolution

If a push finds the cloud record is newer than expected:

The system should:
- detect the conflict
- surface both versions to the user
- apply no silent overwrite

Conflict resolution strategy:
- local profile always wins by default
- user may explicitly accept remote version
- both versions may be preserved with timestamps

This prevents silent data loss across devices.

---

## 5. Vector Search Architecture

### 5.1 Separation of Concerns

Vector search in Linkright separates:
- embedding generation (fastembed or Jina)
- vector storage (local cache or MongoDB)

No embedding model is bundled into Linkright itself.

The embedding provider is configured by the user at setup time.

### 5.2 Local Vector Search

For CLI-only use:
- embeddings are generated via fastembed (offline) or Jina API (online)
- vectors are cached under `~/.linkright/cache/embeddings/`
- search happens locally using cosine similarity over cached vectors
- no MongoDB required

This is the default path.

### 5.3 Cloud-Assisted Vector Search

When MongoDB sync is enabled:
- embeddings may be pushed to the `vector_store` collection
- MongoDB's built-in vector search is used for cloud-assisted semantic retrieval
- this supports future multi-device retrieval scenarios

Embedding generation always stays local.

MongoDB stores the vector output, not the embedding model.

### 5.4 Embedding Model Routing

Embedding generation follows the provider configuration:

```text
fastembed         # offline, free, no API key required
Jina API          # online, higher quality, free tier available
```

The embedding pipeline is defined in DOC 15.

This document only defines where vectors are stored and how they are managed.

---

## 6. Data Boundary Rules

### 6.1 What NEVER Goes to Cloud

The following should never be pushed to cloud storage, even encrypted:

- raw resume PDF files
- raw uploaded documents
- salary history unless explicitly encrypted and opted in by user
- interview notes containing third-party names without consent indication
- browser session tokens
- provider API keys
- local OS credentials

These remain permanently local.

### 6.2 What CAN Go to Cloud (Encrypted)

The following may be pushed if cloud sync is enabled:

- canonical profile (encrypted)
- signal store and weights (encrypted)
- outcome events (encrypted)
- opportunity log (encrypted, without raw JD HTML)
- generated artifact metadata and lineage (encrypted)

The user may selectively exclude categories during sync setup.

### 6.3 Website and Oracle Are Separate Systems

Linkright CLI storage does NOT interact with:

- Supabase (used by the website for user auth and PII)
- Oracle Postgres (used for jobs data and analytics)

These are entirely separate systems with separate schemas, credentials, and access patterns.

The CLI has no direct dependency on either.

If the CLI and website ever need to exchange profile data, that is a future integration concern requiring its own architecture review.

---

## 7. Backup and Restore

### 7.1 Local Backup

The simplest backup is a copy of `~/.linkright/`.

Users may:
- run `linkright backup export ~/linkright_backup.tar.gz` to produce a portable archive
- restore by running `linkright backup import ~/linkright_backup.tar.gz` on a new device

The archive includes:
- canonical profile
- signals and weights
- opportunity log
- outcome events
- configuration (without API keys)

The archive does NOT include:
- raw uploaded PDFs
- provider API keys (must be re-entered)
- OS keychain credentials

### 7.2 Cloud Restore

If cloud sync was active:
- run `linkright sync restore` on the new device
- enter the master encryption key
- the system pulls all encrypted collections and decrypts locally

This restores:
- canonical profile
- signals
- outcomes
- opportunity log

Raw documents and API keys must still be re-provided.

### 7.3 Disaster Recovery Philosophy

The system should assume:
- devices will fail
- local data will occasionally be lost
- cloud accounts may become inaccessible

Therefore:
- local export should be easy and friction-free
- cloud sync should not require a specific MongoDB host
- restore flows should be documented and tested
- the user should be encouraged to export at least once per sprint

---

## 8. Storage Governance

Storage decisions should remain conservative.

The system should avoid:
- writing sensitive plaintext to cloud
- allowing silent profile mutations without local confirmation
- growing the `~/.linkright/` directory without bounds
- retaining raw uploaded documents indefinitely without user permission

The system should support:
- storage size audit: `linkright storage audit`
- selective purge of old artifacts
- cache clearing without losing canonical data

---

## 9. Document Dependencies

This document depends on:
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 13A — Implementation Architecture Documentation Topology & Governance Plan

This document influences:
- DOC 14 — Canonical Schemas, Entity Contracts & State Models
- DOC 15 — Embeddings, Search, Hybrid Retrieval & Ranking Implementation
- DOC 17 — Security, Privacy, Permissions & Trust Architecture
- DOC 24 — Closed-Loop Learning System

This document should be treated as the canonical storage infrastructure reference for Linkright.
