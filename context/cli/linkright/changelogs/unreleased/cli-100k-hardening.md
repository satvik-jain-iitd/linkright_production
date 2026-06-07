# CLI 100k-user hardening — security + scale fixes

## Fixed

- **API key no longer leaks in stack traces (B1).** The Gemini key was embedded in the request URL (`?key=`); any httpx/network exception could surface it in a traceback or log. It now travels in the `x-goog-api-key` header and never appears in the URL.
- **No more retry stampede at scale (B3).** Provider cooldowns after a 429 were a fixed 60s with zero jitter, so independent CLI processes that hit a rate limit at the same moment all retried at the same moment. Cooldowns are now randomly jittered and honor the server's `Retry-After` header (capped so a hostile value can't freeze a provider).
- **Session JWT stored in the OS keychain (B2).** The login token was written to `~/.linkright/session.json` in plaintext (chmod-600 only). It now goes to the OS keychain (macOS Keychain / Linux Secret Service / Windows Credential Manager) via `keyring`, with automatic one-time migration of any existing plaintext session. Falls back to the prior chmod-600 file on headless/CI boxes with no keychain backend; opt out with `LR_NO_KEYRING=1`.

## Added

- **$0-promise spend guard (W1).** OpenRouter (the only paid provider in the fallback cascade) is now **disabled by default** — it requires an explicit `LR_ALLOW_PAID=1` opt-in, and even then a rolling monthly budget (`LR_MONTHLY_BUDGET_CENTS`, default 500 = $5) caps spend. Fails closed, so users on their own keys never get a surprise bill at scale. New module `llm/budget.py`.
