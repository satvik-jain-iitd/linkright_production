# Oracle: openclaw → Hermes Agent migration plan

> Saved 2026-05-01 for later execution. Triggered by Anthropic's April 4, 2026 policy change blocking Claude Pro/Max subscription tokens in 3rd-party tools (openclaw included).

## Context

Satvik runs `openclaw` on his Oracle VPS (CPU-only, no GPU) as a personal local-first AI assistant. Anthropic's April 2026 policy blocked subscription auth tokens in 3rd-party tools — openclaw's "use my Max plan" path now bills per-token. Hermes Agent (by Nous Research) is the natural successor with built-in `hermes claw migrate` for openclaw users.

## Verified facts (sources at end)

| Fact | Verified from |
|---|---|
| Anthropic Claude Pro/Max OAuth tokens **blocked in 3rd-party tools** (Apr 4 2026) | VentureBeat, mlq.ai |
| Token still works in Hermes BUT bills per-token; Max base allowance NOT consumed | Hermes Anthropic provider docs |
| `hermes claw migrate` is FIRST-CLASS support for openclaw → Hermes | Hermes CLI reference |
| OpenRouter free tier: 50 req/day, 20 RPM, **no credit card required** | OpenRouter FAQ + Pricing |
| OpenRouter has 11 verified free + tool-capable models | OpenRouter `/api/v1/models` direct |
| Nous Portal free plan: $0.10 credits/mo only; **Tool Gateway is paid-only** | Nous Portal docs |
| openclaw repo: github.com/openclaw/openclaw, MIT, by @steipete | openclaw.ai + GitHub |
| Steinberger joined OpenAI; openclaw remains OSS | openclaw.ai |
| Gemma 3:1B is 32K context (below Hermes 64K min) + no agentic capability | Ollama library page |

## Final approach (sourced)

**Stack:**
- **Runtime**: Hermes Agent (replaces openclaw)
- **Primary LLM**: OpenRouter free tier → `nvidia/nemotron-3-super-120b-a12b:free` (262K ctx, tools ✅)
- **Fallback chain**: Groq → Cerebras → Gemini (all from existing `e2e_diagnostic_run/.env` keys)
- **Last resort**: Anthropic API pay-per-token (only if all free quotas exhausted)
- **Skip**: Local Oracle Ollama (CPU-only, too slow), Anthropic Max OAuth (no longer free in 3rd-party), Nous Portal free (Tool Gateway paid-only)

## Pre-flight checklist

- [ ] Locate openclaw home dir on Oracle (typically `~/.openclaw/`)
- [ ] Backup openclaw config + skills + data (built into `hermes claw migrate` but manual backup good practice)
- [ ] Confirm OpenRouter signup (no CC required) — get API key
- [ ] Confirm Anthropic API key valid (existing or new) for last-resort fallback
- [ ] Note current openclaw version + last-used model

## Migration sequence (concrete commands)

```bash
# === ON ORACLE ===

# 1. Install Hermes Agent
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc

# 2. Verify install
hermes --version
hermes doctor   # should pass all checks

# 3. Dry-run migration (preview only, no changes)
hermes claw migrate --dry-run
# Review the output — what gets migrated, what gets skipped

# 4. Actual migration (with backup)
hermes claw migrate --migrate-secrets
# Default: keeps backup of openclaw dir before touching anything
# 30+ categories migrated: SOUL.md, MEMORY.md, skills, models, MCP, sandbox, API keys

# 5. Configure OpenRouter as primary
hermes auth add openrouter
# (paste OpenRouter API key when prompted)

hermes config set model openrouter/nvidia/nemotron-3-super-120b-a12b:free

# 6. Add fallback chain from your existing free API keys
# (~/.linkright is on Mac; copy keys from there to Oracle's ~/.hermes/.env)
hermes fallback add   # → groq (key: GROQ_API_KEY)
hermes fallback add   # → cerebras (paste 1 of CEREBRAS_API_KEYS, others go into credential pool)
hermes fallback add   # → gemini (paste GEMINI_API_KEY; other 3 into pool)
# OPTIONAL — last-resort paid fallback
hermes fallback add   # → anthropic api key

# 7. Configure credential pools for multi-key providers
hermes auth add cerebras --api-key <key2>
hermes auth add cerebras --api-key <key3>
hermes auth add cerebras --api-key <key4>
# Same for Gemini's 4 keys

# 8. Verify
hermes fallback list
hermes status --deep
hermes config show

# 9. First chat — sanity test
hermes chat -q "Reply OK in one word"

# 10. Full agentic test
hermes chat -q "List the files in my home directory and tell me which is the largest"

# 11. Persistent skill test
hermes skills list
# Confirm migrated openclaw skills are in ~/.hermes/skills/

# 12. Daemon / service (if openclaw was running as a service)
hermes gateway install   # only if you want it as systemd/launchd service
hermes gateway start
hermes gateway status
```

## Rollback if needed

```bash
# Restore openclaw from backup
hermes claw migrate already created a backup at ~/.hermes/backups/openclaw-pre-migration-<timestamp>/
# Restore commands (if hermes-claw exit cleanup not enough):
mv ~/.openclaw ~/.openclaw.dead   # quarantine current state
# Then restore from your manual backup OR from hermes's auto-backup
```

## Skill compatibility check

Hermes 670-skill registry includes a built-in `openclaw` skill: _"Configure, extend, or contribute to OpenClaw"_ — meaning Hermes treats openclaw as a recognized peer and can help if you need to talk to your old openclaw setup post-migration.

After migration:
```bash
hermes skills check   # check for upstream updates on installed skills
hermes curator status # background skill maintenance status
```

## Smoke test plan

Before declaring migration successful, run these in order:

| Test | Pass criterion |
|---|---|
| `hermes chat -q "Reply OK"` | Returns "OK" via OpenRouter free model |
| `hermes chat -q "Search web for 'Anthropic policy April 2026'"` | Tool-call (web_search) executes, returns recent results |
| `hermes skills install official/security/1password` (or any built-in) | Skill installs without error |
| `hermes cron list` | Shows migrated cron jobs (if any from openclaw) |
| `hermes memory status` | MEMORY.md and USER.md present, content migrated |
| `hermes doctor --fix` | All checks pass |
| Quota probe: 5 successive chats | None hit OpenRouter 50/day limit |

## Cost projection (per Satvik's "$0 minimum")

| Usage pattern | Daily cost | Notes |
|---|---|---|
| <50 requests/day | **$0** | Within OpenRouter free tier |
| 51-200 requests/day | **~$0** if Groq/Gemini/Cerebras quotas have headroom | Fallback chain catches overflow |
| 200-1000 requests/day | $0 if buy $10 OpenRouter credits one-time → 1000 RPD on free models | $10 one-time, never expires |
| >1000 requests/day | Per-token rates kick in via fallback | Anthropic API last resort |

## Known unknowns (verify during execution)

- Exact UX of `hermes claw migrate` interactive prompts (skill conflict resolution etc.)
- Latency of OpenRouter free models from Oracle's region (Singapore by default per worker render.yaml)
- Whether existing openclaw skills work as-is in Hermes (file format compatible per docs but real test needed)
- Whether MCP servers Satvik had configured in openclaw (if any) get migrated cleanly

## Sources

- [Anthropic Ends Paid Access for Claude in Third-Party Tools (mlq.ai)](https://mlq.ai/news/anthropic-ends-paid-access-for-claude-in-third-party-tools-like-openclaw/)
- [Anthropic cuts off Claude subscriptions with OpenClaw and third-party AI agents (VentureBeat)](https://venturebeat.com/technology/anthropic-cuts-off-the-ability-to-use-claude-subscriptions-with-openclaw-and)
- [Anthropic Charging Per Token for Third-Party Tools on Max and Pro (RelayPlane)](https://relayplane.com/blog/anthropic-extra-usage-third-party-tools)
- [Hermes Agent — AI Providers Docs (Anthropic auth methods)](https://hermes-agent.nousresearch.com/docs/integrations/providers)
- [Hermes Agent — Tool Gateway Feature (paid-only confirmed)](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway)
- [OpenRouter FAQ (free tier policy)](https://openrouter.ai/docs/faq)
- [OpenRouter Rate Limits (Zendesk)](https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know)
- [openclaw.ai (canonical openclaw homepage)](https://openclaw.ai/)
- [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- [Ollama gemma3:1b model page (32K context confirmed)](https://ollama.com/library/gemma3:1b)
- [Hermes Agent installation docs](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
