# LinkRight CLI — Production-Grade / 100k-User Scalability Audit

Sprint brief (Satvik, 2026-06-07): Product QA with full backend + infra focus to
make the **linkright CLI** (only — NOT sync-resume-engine) a scalable,
production-grade, modular SaaS-style platform that supports 100k users easily.
Analyze the codebase using the 3-engineer setup (Sonu / Aman / Sanika) properly.

---

## ━━━ STEP 1 — ANALYSIS (Sonu leads) ━━━

### Reframe: what "100k users" means for a CLI

A PyPI CLI has **no server concurrency** — each user runs their own process on
their own machine. "100k users" therefore tests four properties, not request
throughput:

1. **No central bottleneck** every user funnels through.
2. **Graceful degradation** when shared infra is down.
3. **Clean per-user data isolation** (no shared mutable state).
4. **$0-default cost** — infra cost must not scale with user count.

The audit's spine question: **how hard does the CLI depend on the single shared
Oracle VPS** (4-core ARM Ollama box, `NUM_PARALLEL=1`, shared with
n8n/PG/Mongo/Postiz — already infra-audited 2026-06-07)?

### Grounded findings — COMPACTED (full detail → SYNTHESIS table below)
Sonu spine recon (config/embedder/oracle): default path fully local ($0,
fastembed, per-user `~/.linkright/`, no central bottleneck) → scales to 100k.
Gaps G1 (no Oracle-path retry), G3 (sequential embed_batch), G4 (shared-creds
risk) carried into the synthesis table as W2/W6/open-Q. G2 (Mongo) → resolved OK.

### WHY (airtight)
Users need a career tool that works on any laptop, free, offline-capable, and
never degrades because a shared server is overloaded. The current default path
already delivers this; the risk is the opt-in Oracle path lacking client
resilience and an unclear-but-mandatory Mongo dependency.

### Audit dimensions (full scope) + 3-engineer division of labor

| Dim | Area | Owner | Why |
|-----|------|-------|-----|
| A | Spine: Oracle dependency hardness, fallback, default-local proof | **Sonu** (done above) | arch call |
| B | `llm/direct.py` (1659 LOC) — provider dispatch, retry, rate-limit, key handling, cost guards | **Sanika** (Gemini 1M ctx) | too big for main ctx |
| C | `db/` + Mongo centrality — is Mongo required for onboard/tailor? migration path to file-only | **Aman** (OpenCode) | planner/solutioning |
| D | `telemetry.py` (694) + cost model — does $0 hold at scale, any phone-home | **Sanika** | big file |
| E | `auth/` + `keys/` modules — secret storage, multi-key rotation, leak surface | **Aman** | review |
| F | Modularity — pillar separation (resume/jobsearch/interview/content), import coupling | **Aman** | arch review |
| G | Resilience — add retry/backoff/circuit-breaker to `oracle.py` + `embedder.py` | **Sonu** decides, Sanika implements later | G1 fix |

### ━━ Step-1 SYNTHESIS (Sonu, after Aman + Sanika deep-dives, 2026-06-07 22:1x) ━━

Verdict: **architecture is fundamentally sound for 100k** (local-first default,
$0, per-user isolated, no central bottleneck on the default path). Real risks
are 3 BLOCKERS (2 security + 1 scale) + a cost-at-scale gap. All concrete/fixable.

Consolidated, severity-ranked (owner who found it):

| # | Sev | Finding | Evidence | Found |
|---|-----|---------|----------|-------|
| B1 | BLOCK | API key leaks in stack trace (Gemini key in URL, no exception handling on httpx post) | `direct.py:332` | Sanika |
| B2 | BLOCK | No encryption at rest — `session.json` (JWT) + `.env` plaintext, chmod-600 only; leak vector on shared/CI boxes | `auth/__init__.py:43-54` | Aman |
| B3 | BLOCK | Thundering-herd — per-client in-memory cooldowns, no jitter/shared state; 100k clients slam rate-limited APIs on startup | `direct.py:53` | Sanika |
| W1 | WARN | $0 model breaks at scale — paid OpenRouter fallback fires when free tiers exhaust | `telemetry.py:217`, `direct.py:876` | Sanika |
| W2 | WARN | No client retry/backoff on shared-Oracle path | `oracle.py`, `embedder.py` | Sonu(G1) |
| W3 | WARN | PII risk — `fallback_chain` logs raw LLM error text (may echo prompt) | `telemetry.py:347` | Sanika |
| W4 | WARN | API keys land in process env (`/proc/self/environ` readable) | `config.py:20-56` | Aman |
| W5 | WARN | Cross-pillar coupling: content→`resume.lib.embedder`, resume→`jobsearch.cli` | `content/grounding.py:96` | Aman |
| W6 | WARN | `embed_batch` sequential despite native batching | `embedder.py:221` | Sonu(G3) |

OK / resolved: Mongo NOT required for core (lazy+graceful, only optional pillars)
→ **G2 closed**. Telemetry local-only, no phone-home. Default path local/$0/isolated.
Good hygiene: secret-not-in-YAML, atomic key-writer, 429 cooldown, cost-guard bans pro models.

### RESOLVED (Satvik, 2026-06-07): local-only / BYO. G4 closed.
End-users never get shared Oracle creds → VPS only serves Satvik (1 user),
infinite headroom. 100k = 100k local fastembed + each user's own free keys.
Capacity note (INFERRED): single VPS as a shared backend caps at ~10-30
concurrent / ~1-2k light DAU due to `NUM_PARALLEL=1` serialization — ~50-100×
short of 100k. Scale path IF ever hosted: vLLM continuous batching + serverless
GPU scale-to-zero + async queue (pay per paid-user-second, no idle fleet).
Not needed for local-first CLI. → 100k question = purely the cloud-key path
(B1-B3 + W1).

### Sign-off status — Step 1: Aman ✅  Sanika ✅  Sonu ✅ (Satvik resolved G4).

---

## ━━━ STEP 2 — PLANNING (Aman leads, + Sonu critique) ━━━

Fix plan (Aman drafted root-cause/fix/files/effort/risk/test each; Sonu sharpened):

| Fix | Approach (post-Sonu critique) | Files | Effort | Test |
|-----|------|-------|--------|------|
| **B1** key-leak | Move Gemini key to `x-goog-api-key` HEADER (not `?key=` URL) + wrap httpx post, redact on error | `direct.py:~332` | S | exc msg has no key |
| **B3** herd | `random.uniform` jitter in `_mark_cooling` + parse `Retry-After` (cap at cooldown) across providers | `direct.py:38,86-89,+providers` | S | two cool calls differ; Retry-After honored |
| **W1** cost | New `llm/budget.py` (SQLite rolling counter). **Default FREE-ONLY** — paid needs `LR_ALLOW_PAID=1`, fail closed | `direct.py:1412,1648`, `budget.py`(new), `cli.py` | M | over-budget → LLMError, no paid call |
| **B2** creds | **OS keychain via `keyring`** (not DIY file-crypto = theater). Re-ranked BLOCK→**WARN** (chmod-600 plaintext = CLI norm: aws/gh/docker) | `auth/__init__.py`, `keys/` | M | session read/write via keyring |

Ship order: **B1 → B3 → W1 → B2(optional)**. B1/B3 cheap+safe; W1 protects $0 promise; B2 is polish.

Sonu critique deltas vs Aman draft: (1) B1 header-relocate not just wrap; (2) W1 default=$0 free-only opt-in, not $5; (3) B2 keyring not DIY-crypto, and BLOCK→WARN.

### Sign-off status — Step 2: Aman ✅(draft) · Sonu ✅(critique folded) · Satvik ✅ approve-all.

---

## ━━━ STEP 4 IMPLEMENT + STEP 5 REVIEW — DONE (PR #190) ━━━

Branch `fix/cli-100k-hardening` (worktree), commit `fe8dd66`, PR #190 → main.
Sonu implemented all four (security-sensitive → #1 coder); Sanika adversarial review.

- B1 key→header, B3 jitter+Retry-After, W1 `llm/budget.py` (free-only default,
  fail-closed, model-aware), B2 keyring+file-fallback+migration. `keyring>=24` dep.
- 14 tests in `test_cli_hardening.py`, all pass. 0 regressions vs base.
- Sanika adversarial caught 5 (jitter<Retry-After, budget model-bypass, budget
  race, unlink crash, stale-plaintext-on-failed-migration) → ALL fixed.

Sign-off — Step 4/5: Sonu ✅ Sanika ✅(review). Awaiting: Satvik merge of #190.
Remaining audit WARNs (W2-W6: Oracle retry, PII-in-logs, env-keys, pillar
coupling, embed_batch) = follow-up, non-blocking for 100k.
