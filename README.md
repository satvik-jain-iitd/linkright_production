# LinkRight Production Runtime

This repository is intentionally trimmed to only the code required to run `https://sync.linkright.in`.

## Services in Scope

- `website/` - Next.js frontend and API routes
- `worker/` - Python async processing pipeline
- `oracle-backend/` - Python backend for oracle/session workflows

## Out of Scope

Documentation, archived experiments, test-only suites, and legacy/non-runtime modules are intentionally excluded.

## Deployment Notes

The platform depends on environment variables connecting `website` to `worker` and `oracle-backend`:

- `WORKER_URL`
- `WORKER_SECRET`
- `ORACLE_BACKEND_URL`
- `ORACLE_BACKEND_SECRET`

Set service-specific environment variables in each service before starting.
