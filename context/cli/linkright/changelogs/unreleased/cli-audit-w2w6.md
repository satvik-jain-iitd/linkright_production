# CLI audit follow-ups — W2-W6 (resilience, privacy, perf, decoupling)

## Fixed

- **Oracle calls survive transient network blips (W2).** The Oracle VPS client (`rewrite`/`generate`/`embed`) now retries once with backoff on httpx network errors (timeouts, connection resets) — never on a non-200 status, which is deterministic. A co-tenant blip on the shared box no longer fails a request outright.
- **Telemetry no longer logs prompt/PII echoes (W3).** Raw provider error text could echo the prompt in the fallback-chain trace. Quoted spans are now redacted before the error is shortened for storage.

## Changed

- **`embed_batch` uses native batched encoding (W6).** When fastembed is the active tier, embeddings are now produced in one batched pass instead of one-by-one — markedly faster for multi-text embedding. Falls back to sequential for other tiers.
- **Stable embeddings facade (W5).** Non-resume pillars now import `embed`/`embed_batch` from `linkright.embeddings` instead of reaching into `resume.lib.embedder`, so the embedder can move without breaking `content/`.

## Notes

- **W4 (API keys in process env) is by design.** Env-var secrets are the 12-factor CLI norm (cf. `aws`/`gh`), readable only by same-user processes — the same trust boundary as the chmod-600 `.env` itself. No code change.
