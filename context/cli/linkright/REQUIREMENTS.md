# LinkRight CLI — User Requirements & Performance Spec

> What users need on their laptop to run LinkRight CLI for resume tailoring (Pillar 1).
> Status: 2026-05-01 — based on agent-mode pipeline + fastembed embeddings + claude CLI dispatch.

---

## TL;DR

| Requirement | Minimum | Recommended |
|---|---|---|
| **OS** | macOS 12+, Linux (Ubuntu 22+), Windows 10+ (with WSL2 for Linux-style shell) | macOS Apple Silicon |
| **CPU** | Any 64-bit (x86_64 / ARM64). 2 cores. | 4+ cores |
| **RAM** | 4 GB free during run | 8 GB |
| **Disk** | 1.5 GB free for one-time installs | 5 GB |
| **Network** | Required for first install + LLM CLI calls | Stable broadband |
| **Python** | 3.10+ | 3.12 / 3.13 |
| **Node.js** | 18+ (only for Playwright PDF rendering) | 20+ |
| **At least ONE LLM CLI tool** | claude / opencode / gemini / ollama | claude (best quality) |

---

## 1. Software prerequisites (one-time install)

### Required

| Component | Size | Why needed | Install |
|---|---|---|---|
| **Python 3.10+** | ~50 MB (system / pyenv) | Pipeline runtime | `brew install python@3.13` (Mac), apt/dnf on Linux, python.org Windows |
| **Node.js 18+** | ~80 MB | Playwright headless Chromium for PDF render | `brew install node`, nvm, or installer |
| **LinkRight CLI** | ~10 MB | The pipeline itself | `pip install -e .` from the repo |
| **fastembed** | ~50 MB pip + ~80 MB ONNX model (cached on first use, ~/.cache/fastembed/) | Local CPU embeddings — no API key, no GPU needed | `pip install fastembed` |
| **Playwright Chromium** | ~80 MB | PDF render at step 15 | `python -m playwright install chromium` |

### At least ONE LLM CLI (pick what suits you)

| CLI tool | Cost | Quality | Notes |
|---|---|---|---|
| **claude** (Claude Code) | Subscription user pays Anthropic (~$20/mo or pay-as-you-go) | **Top tier** | Each pipeline run ~$1.20 of claude credits |
| **opencode** (sst/opencode, OSS) | **$0** | Acceptable for short prompts; degrades on >2 KB inputs | Free model `nemotron-3-super-free` works out-of-box |
| **gemini-cli** (Google) | $0 free daily quota | Good | May hit "no capacity" sometimes |
| **ollama** + a chat model (e.g. `llama3.1:8b`) | $0 (local) | Quality varies by model | Heavy on RAM — needs 6+ GB free |

The CLI auto-detects via env var `LR_AGENT_BACKEND=claude|opencode|gemini` and runs the corresponding subprocess. Custom CLIs can be added without code changes via `~/.linkright/agents.yaml`.

### Optional (if you have it)

| Component | Why | Notes |
|---|---|---|
| Oracle Ollama VPS or self-hosted Ollama with `nomic-embed-text` | Best embedding quality (768-dim semantic) | Set `ORACLE_BACKEND_URL` + `ORACLE_BACKEND_SECRET` env vars |
| `sentence-transformers` (PyTorch) | Higher-quality embeddings | ~700 MB torch — heavy. Activate via `LR_USE_SENTENCE_TRANSFORMERS=1` |

---

## 2. First-run download budget (zero-cost path)

If user has only Python + opencode (zero paid services):

```
pip install fastembed                    →  ~50 MB pip cache
fastembed downloads BAAI/bge-small...    →  ~80 MB ONNX model (auto, on first embed call)
python -m playwright install chromium    →  ~80 MB headless Chromium
opencode (already installed standalone)  →   0 (uses session)
```

**Total first-run download: ~210 MB.** Subsequent runs: 0 download (everything cached).

---

## 3. Speed & latency expectations

### Per-resume wall-clock (one JD, one resume)

| Backend | Wall-clock | Cost per run |
|---|---|---|
| **claude CLI** | ~5–6 minutes | ~$1.20 (against user's Claude subscription) |
| **opencode** (free) | ~10–15 minutes | $0 |
| **gemini CLI** | ~6–8 minutes | $0 (within free tier) |
| **Direct API mode** (Groq/Gemini/Cerebras keys) | ~2–3 minutes | $0–0.01 (free tier) |
| **ollama local** (depends on model size) | ~8–20 minutes | $0 (uses local CPU/GPU) |

### Per-step latency breakdown (claude backend, typical run)

| Step | Action | Time |
|---|---|---|
| 0 | PDF → text (pypdf or unpdf) | 1–2 s |
| 1 | Parse resume to JSON | ~10 s |
| 2 | Extract 15–20 nuggets | ~15 s |
| 3 | Embed nuggets (fastembed batch) | ~2 s |
| 5 | Embed JD requirements | ~1 s |
| 6 | Score per-role cosine | <1 s |
| 7 | JD parse strategy (P1+P2 prompt) | ~10 s |
| 8 | Retrieve nuggets per role | <1 s |
| 9 | Professional summary | ~10 s |
| 10 | Verbose bullets (per role) | ~30–60 s |
| 11 | Rank bullets | ~5 s |
| 12 | Condense bullets to 95–110 chars | ~30 s |
| 13 | Width tune (Pass D) | ~10–20 s |
| 14 | Assemble HTML | <1 s |
| 15 | Playwright PDF render | ~5–10 s |
| 16 | Telemetry rollup | <1 s |
| **Total** | | **~3–5 min** |

agent-mode adds ~10s per LLM call vs direct API → 11 calls × extra 5–10s ≈ 1–2 min slower.

### Batch throughput (24 jobs)

| Backend | Sequential | Parallel × 3 |
|---|---|---|
| claude CLI | ~2.5 hours | ~50 min |
| opencode | ~5 hours | ~1.5 hours |
| Direct API | ~1.5 hours | ~30 min |

**Note:** Per Jane's "one resume at a time" + "diversity-pattern" RCA discipline, batch runs should NOT be the default workflow. The 24-job corpus is for sampling diverse patterns SEQUENTIALLY with full RCA between each — not for parallel benchmarking.

---

## 4. Quality expectations

### Pipeline output (per resume)

| Dimension | Range | Target | Notes |
|---|---|---|---|
| Total bullets | 8–16 | 10–14 | Pipeline auto-fits to 1-page |
| Page count | 1 | 1 | Hard guarantee via `fit_loop` |
| PDF size | 100–300 KB | <250 KB | depends on bullet density |
| **JD requirement coverage** | 70–95% | **99%** | The 5-day-plan target |
| Bullet length | 95–110 chars | 100–105 | Width-tuned via `width_poc` |
| Hallucination rate | 0 (with v8/v9 guards) | 0 | jd_keyphrase + metric_extract guards |
| Years signaling | matches resume data | honest | Won't fabricate years |

### Hard guarantees (won't violate)

- **No fabrication** — v8/v9 fabrication guards reject bullets with metrics absent from source nuggets, or JD-keyword "fishing" with no nugget grounding.
- **1-page PDF** — fit_loop iterates until page=1 OR exhausts strategies (final fallback: best-effort).
- **XYZ format** — bullets follow "Impact X, achieving Y, by doing Z" structure.
- **No PII leakage** — pipeline never sends OS-level files outside the run directory's input/.

### Soft expectations (target via iteration)

- **JD coverage ≥ 99%** — Pillar 1's 5-day plan target. Currently ~75–85% on first iteration; closes gap via H1 (threshold tuning), H2 (per-req re-rank), H3 (nugget extraction prompt tweak).
- **Verb diversity** — top resumes don't repeat verbs (Architected/Drove/Led/Compressed/Secured all distinct).
- **Metric density** — every bullet has ≥1 quantifier (%, $, x, number).

---

## 5. Cost expectations

### Per resume (single run)

| Backend | Hard cost | Hidden cost |
|---|---|---|
| claude CLI subscription | **$1.20–1.50** (deducted from Claude API budget) | None — subscription is sunk |
| opencode | **$0** | None — free OSS model |
| gemini CLI free tier | **$0** | Risk of "no capacity" mid-run; rerun |
| Direct API (Groq/Gemini free) | **~$0–0.01** | Daily quota limits |
| ollama local | **$0** | CPU/RAM during inference |

### Per 24-job corpus (full diversity sweep)

| Backend | Total cost |
|---|---|
| claude CLI | ~$30 |
| opencode / gemini / ollama | $0 |
| Direct API free tier | ~$0–0.20 |

### Recommendation for users

- **First-time / occasional users**: opencode (truly free, no setup beyond install)
- **Power users with Claude subscription**: claude backend (best quality, $1.20/run)
- **Privacy-focused / offline**: ollama local
- **Speed-focused**: direct API mode with own Groq/Gemini free-tier keys

---

## 6. Network requirements

### Required online

- **First install**: pip downloads (~50 MB), fastembed model (~80 MB), Playwright Chromium (~80 MB)
- **Each LLM call**: depending on backend (claude → Anthropic API, opencode → its provider, gemini → Google, etc.)

### Works fully offline AFTER first install

- Embedding (fastembed cached locally)
- PDF parse (pypdf or unpdf — local)
- HTML assembly
- PDF render (Playwright local)

If user picks **ollama** as LLM backend → fully offline after first install + ollama model download (~5–8 GB depending on model).

---

## 7. Configuration (everything tunable)

### Environment variables

```bash
# LLM dispatch
LR_LLM_MODE=agent                    # agent (CLI subprocess) | direct (API keys)
LR_AGENT_BACKEND=claude              # claude | opencode | gemini | <custom>
LR_AGENT_BIN=/path/to/cli            # override binary
LR_AGENT_ARGS_JSON='[...]'           # override args (JSON list)
LR_AGENT_PARSE=json_envelope         # plain_text | json_envelope | jsonl_events
LR_AGENT_MODEL=...                   # value for {model} placeholder
LR_AGENT_TIMEOUT_S=300               # subprocess timeout (default 5 min)
LR_AGENT_ENV_JSON='{"K":"V"}'        # extra env for the subprocess

# Embedder
ORACLE_BACKEND_URL=...               # if you have Oracle Ollama set up
ORACLE_BACKEND_SECRET=...
LR_USE_SENTENCE_TRANSFORMERS=1       # opt-in heavier ST embeddings instead of fastembed
LR_ST_MODEL=all-mpnet-base-v2        # which ST model

# Pipeline
COSINE_THRESHOLD=0.50                # retrieval cutoff (lower = more recall)
COSINE_THRESHOLD_LOOSE=0.35          # secondary pass threshold
ENABLE_RERANKER=1                    # turn on cross-encoder reranker
ENABLE_WIDTH_POC=1                   # turn on width tuning loop
ENABLE_BATCH_STEP_10=1               # batched verbose bullet gen
DISABLE_EXPAND_TO_FILL=1             # disable bullet padding to width target
PREFER_PRO=0                         # never use Gemini Pro (cost guardrail)
```

### Configuration files

- `~/.linkright/config.yaml` — user defaults (`default_llm_mode`, `default_skill_mode`, MongoDB URI, etc.)
- `~/.linkright/agents.yaml` — user-defined LLM CLI specs (extends built-in claude/opencode/gemini)

---

## 8. What this CLI does NOT need

- ❌ No GPU
- ❌ No Docker
- ❌ No cloud account (any pillar works locally; LLM CLIs use their own auth)
- ❌ No always-on internet (after first install)
- ❌ No specific shell (works on bash, zsh, fish, PowerShell)
- ❌ No Anthropic API key in env (uses claude CLI session if you pick that backend)

---

## 9. Known limitations / known issues

- **Variance per run**: same JD + resume can produce 75–85% coverage across runs due to LLM sampling temperature. Single-run measurements are noisy; n=3 + median is more robust for serious benchmarking.
- **agent-mode latency**: each subprocess call has ~5s overhead vs direct API (~0.5s). Adds 1–2 min total per resume.
- **Mac sandbox edge cases**: Claude Code's Bash tool may block reads of `Documents/` subdirs intermittently. Fallback paths (pypdf, fastembed, agent-mode) handle these gracefully.
- **First-run latency**: fastembed downloads ~80 MB on first call, adding ~10–30 s to first resume run only. Subsequent runs: cache hit, <50 ms.

---

## 10. Quick verification (after install)

```bash
# 1. Pipeline imports OK?
python -c "from linkright.resume import orchestrator; print(orchestrator.__file__)"

# 2. fastembed works?
python -c "from fastembed import TextEmbedding; m = TextEmbedding(model_name='BAAI/bge-small-en-v1.5'); v = next(m.embed(['hello'])); print(f'OK dim={len(list(v))}')"

# 3. Playwright Chromium present?
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); b.close(); p.stop(); print('OK')"

# 4. claude CLI works?
echo "Reply OK" | claude -p

# 5. Smoke pipeline (1 resume, 1 JD)
linkright resume tailor -r resume.pdf -j jd.md --llm-mode agent --yes
```

If all 5 pass, you're ready. If any fails, the error message points to which install step is missing.
