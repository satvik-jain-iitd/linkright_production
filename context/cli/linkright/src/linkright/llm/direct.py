"""Groq + Gemini client wrappers.

Mirrors the call patterns from repo/worker/app/llm/ — same model IDs,
same request shapes, same defaults. No retries beyond the 1 retry the
real pipeline uses.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Optional

import httpx


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# 2026-05-01: 3 new free-tier providers added per Route 3 of free-forever plan
ZHIPU_URL = "https://api.z.ai/api/paas/v4/chat/completions"
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"
CLOUDFLARE_OPENAI_URL_TMPL = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"
)


# ── Iter-08 (2026-04-23): provider cooldowns to prevent cascade waste ──
# RCA showed 24/32 runs had <50% LLM success rate — repeated 429s to same providers.
# Track when a provider 429s → skip it for cooldown_s seconds on next calls.
# Reset on next successful call. Module-global (shared across all helpers).

_PROVIDER_COOLDOWNS: dict[str, float] = {}  # provider_name → unix_timestamp_when_available
_COOLDOWN_SECS = int(os.environ.get("LLM_COOLDOWN_SECS", "60"))
_CASCADE_MAX_PROVIDERS = int(os.environ.get("LLM_CASCADE_MAX", "3"))


def _collect_keys(primary_env: str, n: int = 4) -> list[tuple[str, str]]:
    """Collect rotation keys: primary + _1.._n. Dedupes. Returns [(label, key), ...].

    2026-05-01: enables multi-key rotation per provider. Each provider has up to
    4 free-tier accounts; rotating across them cools rate limits independently.
    """
    keys: list[tuple[str, str]] = []
    seen: set = set()
    primary = os.environ.get(primary_env)
    if primary:
        keys.append(("primary", primary))
        seen.add(primary)
    for i in range(1, n + 1):
        k = os.environ.get(f"{primary_env}_{i}")
        if k and k not in seen:
            keys.append((f"k{i}", k))
            seen.add(k)
    return keys


def _cached_tokens(data: dict) -> Optional[int]:
    """Extract `cached_tokens` from OpenAI-compatible response if present.

    Provider auto-caching surfaces via `usage.prompt_tokens_details.cached_tokens`.
    Confirmed for Groq (GPT-OSS only), Cerebras (qwen-3-235b/zai-glm-4.7/gpt-oss
    only), and OpenAI proper. Returns None when the field is missing or the
    provider/model isn't cache-eligible — callers should treat None as "no
    caching benefit on this call".

    Telemetry-only plumbing: knowing the cache-hit ratio per call site lets us
    later decide whether routing to a cache-eligible model is worth the speed
    trade-off. Without this data we'd have to guess.
    """
    details = (data.get("usage") or {}).get("prompt_tokens_details") or {}
    return details.get("cached_tokens")


def _is_cooling(provider: str) -> bool:
    """True if provider is in cooldown window (should be skipped)."""
    cool_until = _PROVIDER_COOLDOWNS.get(provider, 0)
    return cool_until > time.time()


def _mark_cooling(provider: str, reason: str = "429") -> None:
    """Mark provider as cooling for _COOLDOWN_SECS. Called on 429/quota error."""
    _PROVIDER_COOLDOWNS[provider] = time.time() + _COOLDOWN_SECS


def _clear_cooling(provider: str) -> None:
    """Clear cooldown (called on successful call to allow immediate retry)."""
    _PROVIDER_COOLDOWNS.pop(provider, None)


class LLMError(Exception):
    pass


def _log_token_usage(intent: str, usage: dict) -> None:
    """Print token counts to stderr after each tier_chat call.

    Shows actual prompt/completion/total tokens from the provider's usage
    dict (already normalised to prompt_tokens / completion_tokens /
    total_tokens across all providers). Silently skips if values are None
    (agent-mode or provider didn't return usage).
    """
    import sys as _sys
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    total = usage.get("total_tokens")
    provider = usage.get("provider", "?")
    if prompt is None and completion is None:
        return
    parts = []
    if prompt is not None:
        parts.append(f"in={prompt:,}")
    if completion is not None:
        parts.append(f"out={completion:,}")
    if total is not None:
        parts.append(f"total={total:,}")
    print(
        f"  [tokens] {intent}  {' | '.join(parts)}  ({provider})",
        file=_sys.stderr, flush=True,
    )


# ── Deterministic mode (Phase 2 — 2026-05-01) ──────────────────────────────
#
# When LR_DETERMINISTIC=1, every provider helper pins temperature=0.0 and
# (where supported) injects a seed=LR_SEED|42. This collapses LLM-internal
# variance so n=3 hypothesis tests can detect smaller true effects.
#
# Provider seed support:
#   Groq, Cerebras, OpenRouter: seed accepted (OpenAI-compat shape)
#   Gemini v1beta API: NO seed param — only temperature=0 reduces variance
#   agent_chat (CLI subprocess): temperature passes through; seed depends on backend
#
# For sites where determinism cannot be enforced, the per-call usage dict
# carries deterministic_seed_supported=False so telemetry can identify
# non-determinism sources after the run.

def _is_deterministic() -> bool:
    return os.environ.get("LR_DETERMINISTIC", "").lower() in ("1", "true", "yes")


def _det_seed() -> int:
    try:
        return int(os.environ.get("LR_SEED", "42"))
    except ValueError:
        return 42


def _apply_deterministic_overrides(payload: dict, *, gemini_shape: bool = False) -> bool:
    """Mutate `payload` in place if LR_DETERMINISTIC=1. Returns True on apply.

    For OpenAI-compat providers, sets payload["temperature"]=0.0 + payload["seed"].
    For Gemini v1beta shape (gemini_shape=True), sets nested
    payload["generationConfig"]["temperature"]=0.0 only — no seed support.
    """
    if not _is_deterministic():
        return False
    if gemini_shape:
        gc = payload.setdefault("generationConfig", {})
        gc["temperature"] = 0.0
    else:
        payload["temperature"] = 0.0
        payload["seed"] = _det_seed()
    return True


def groq_chat(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Groq chat with multi-key rotation. Tries up to 4 keys until one succeeds.

    2026-05-01 update: GROQ_API_KEY (primary) + GROQ_API_KEY_1..4 rotation slots.
    On 429/quota, marks specific key cooling and tries next.
    """
    keys = _collect_keys("GROQ_API_KEY")
    if not keys:
        raise LLMError("GROQ_API_KEY not set; cannot call Groq")
    model = model or os.environ.get("GROQ_MODEL_70B", "llama-3.3-70b-versatile")
    last_err: Optional[Exception] = None
    for label, api_key in keys:
        tag = f"groq_{label}"
        if _is_cooling(tag):
            continue
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        det_applied = _apply_deterministic_overrides(payload)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        t0 = time.time()
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(GROQ_URL, json=payload, headers=headers)
            dt = time.time() - t0
            if resp.status_code != 200:
                err = LLMError(f"Groq {resp.status_code}: {resp.text[:500]}")
                last_err = err
                if any(s in str(err) for s in ("429", "rate", "quota")):
                    _mark_cooling(tag)
                    continue  # try next key
                raise err
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = {
                "provider": "groq",
                "model": model,
                "api_key_label": label,
                "latency_s": round(dt, 2),
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens"),
                "cached_tokens": _cached_tokens(data),
                "deterministic_applied": det_applied,
                "deterministic_seed_supported": True,
            }
            _clear_cooling(tag)
            return text, usage
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_err = LLMError(f"Groq network error on {label}: {e}")
            continue
    raise last_err or LLMError("all Groq keys exhausted")


def gemini_chat(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_output_tokens: int = 8000,
) -> tuple[str, dict]:
    """Single Gemini generateContent call. Returns (text, usage_dict)."""
    api_key = os.environ["GEMINI_API_KEY"]
    model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = GEMINI_URL_TMPL.format(model=model, key=api_key)
    # Gemini uses a single contents array; system prompt goes in systemInstruction.
    payload = {
        "systemInstruction": {"role": "system", "parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "text/plain",
        },
    }
    headers = {"Content-Type": "application/json"}
    t0 = time.time()
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload, headers=headers)
    dt = time.time() - t0
    if resp.status_code != 200:
        raise LLMError(f"Gemini {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    # Defensive parsing — sometimes Gemini returns parts[] empty on MAX_TOKENS.
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        finish = (data.get("candidates") or [{}])[0].get("finishReason", "UNKNOWN")
        raise LLMError(
            f"Gemini returned no text (finish_reason={finish}): {json.dumps(data)[:500]}"
        ) from e
    usage = {
        "provider": "gemini",
        "model": model,
        "latency_s": round(dt, 2),
        "prompt_tokens": (data.get("usageMetadata") or {}).get("promptTokenCount"),
        "completion_tokens": (data.get("usageMetadata") or {}).get("candidatesTokenCount"),
        "total_tokens": (data.get("usageMetadata") or {}).get("totalTokenCount"),
        "cached_tokens": (data.get("usageMetadata") or {}).get("cachedContentTokenCount"),
    }
    return text, usage


def gemini_chat_best(
    system: str,
    user: str,
    temperature: float = 0.2,
    max_output_tokens: int = 8000,
) -> tuple[str, dict]:
    """Gemini Flash via all 3 keys (cost-guardrail: NEVER Pro).

    2026-04-23 cost cut: Pro permanently BANNED from this chain.
    Rotates through KEY_3 → KEY_1 → KEY_2 all on gemini-2.0-flash.
    Flash has 1M TPD free per key × 3 keys = 3M TPD; Pro is paid and
    burns 5-10K thinking tokens per call — too expensive.

    Fallback chain:
      Primary: gemini-2.0-flash via KEY_3
      Fallback 1: gemini-2.0-flash via KEY_1
      Fallback 2: gemini-2.0-flash via KEY_2
      Fallback 3: Cerebras qwen-235B
      Fallback 4: Groq 70B
    """
    # Iter-06 (2026-04-23): Flash Lite — cheapest Flash tier. 2x cheaper than
    # regular 2.0 Flash; quality nearly identical for narrow tasks.
    flash_model = "gemini-2.0-flash-lite"
    keys_to_try = [
        ("KEY_3", os.environ.get("GEMINI_API_KEY_3")),
        ("KEY_1", os.environ.get("GEMINI_API_KEY_1")),
        ("KEY_2", os.environ.get("GEMINI_API_KEY_2")),
    ]
    keys_to_try = [(label, k) for label, k in keys_to_try if k]

    attempts = []
    for label, api_key in keys_to_try:
        try:
            return _gemini_call(
                api_key=api_key, model=flash_model, system=system, user=user,
                temperature=temperature, max_output_tokens=min(max_output_tokens, 8000),
                provider_tag=f"gemini_flash_{label}",
            )
        except LLMError as e:
            err = str(e)
            attempts.append(f"{flash_model}@{label}: {err[:100]}")
            # 429 / quota → try next key; hard error → propagate
            if not any(sig in err for sig in ("429", "quota", "exhaust", "RESOURCE_EXHAUSTED", "rate")):
                raise

    # Final fall: Cerebras
    try:
        text, usage = cerebras_chat(system, user, temperature=temperature, max_tokens=min(max_output_tokens, 4000))
        usage["provider"] = "cerebras_fallback"
        usage["fallback_chain"] = attempts
        return text, usage
    except LLMError as e:
        attempts.append(f"cerebras: {str(e)[:100]}")

    # Final-final: Groq
    text, usage = groq_chat(system, user, temperature=temperature, max_tokens=min(max_output_tokens, 4000))
    usage["provider"] = "groq_fallback"
    usage["fallback_chain"] = attempts
    return text, usage


def _gemini_call(
    api_key: str, model: str, system: str, user: str,
    temperature: float, max_output_tokens: int, provider_tag: str,
    response_schema: Optional[dict] = None,
) -> tuple[str, dict]:
    """Internal: single Gemini request. Shared by gemini_chat + gemini_chat_best.

    Iter-06 (2026-04-23): `response_schema` arg enables structured-output mode.
    When provided, Gemini guarantees the response is a valid JSON object matching
    the schema. Eliminates commentary leaks ("I can only generate..." prose).
    """
    url = GEMINI_URL_TMPL.format(model=model, key=api_key)
    gen_config: dict = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
        "responseMimeType": "application/json" if response_schema else "text/plain",
    }
    if response_schema:
        gen_config["responseSchema"] = response_schema
    payload = {
        "systemInstruction": {"role": "system", "parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen_config,
    }
    det_applied = _apply_deterministic_overrides(payload, gemini_shape=True)
    headers = {"Content-Type": "application/json"}
    t0 = time.time()
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(url, json=payload, headers=headers)
    dt = time.time() - t0
    if resp.status_code != 200:
        raise LLMError(f"{model} {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        finish = (data.get("candidates") or [{}])[0].get("finishReason", "UNKNOWN")
        raise LLMError(f"{model} no text (finish={finish}): {json.dumps(data)[:500]}") from e
    meta = data.get("usageMetadata") or {}
    usage = {
        "provider": provider_tag,
        "model": model,
        "latency_s": round(dt, 2),
        "prompt_tokens": meta.get("promptTokenCount"),
        "completion_tokens": meta.get("candidatesTokenCount"),
        "thoughts_tokens": meta.get("thoughtsTokenCount"),
        "total_tokens": meta.get("totalTokenCount"),
        "cached_tokens": meta.get("cachedContentTokenCount"),
        "deterministic_applied": det_applied,
        "deterministic_seed_supported": False,  # Gemini v1beta has no seed param
    }
    return text, usage


def gemini_chat_json(
    system: str,
    user: str,
    response_schema: dict,
    temperature: float = 0.2,
    max_output_tokens: int = 8000,
    model: Optional[str] = None,
) -> tuple[str, dict]:
    """Structured-output Gemini call. Returns (json_text, usage).

    Iter-06 (2026-04-23): caller supplies a JSON schema; Gemini guarantees output
    conforms. No prose leaks, no _strip_commentary needed on the result.

    Rotates through KEY_3 → KEY_1 → KEY_2 on 429. All on Flash Lite by default.
    """
    if os.environ.get("LR_LLM_MODE", "").lower() == "agent":
        return agent_chat(system, user, temperature=temperature, max_tokens=max_output_tokens)
    flash_model = model or "gemini-2.0-flash-lite"
    keys_to_try = [
        ("KEY_3", os.environ.get("GEMINI_API_KEY_3")),
        ("KEY_1", os.environ.get("GEMINI_API_KEY_1")),
        ("KEY_2", os.environ.get("GEMINI_API_KEY_2")),
    ]
    keys_to_try = [(label, k) for label, k in keys_to_try if k]
    if not keys_to_try:
        raise LLMError("No Gemini API key available")
    attempts = []
    for label, api_key in keys_to_try:
        try:
            return _gemini_call(
                api_key=api_key, model=flash_model, system=system, user=user,
                temperature=temperature, max_output_tokens=max_output_tokens,
                provider_tag=f"gemini_flash_lite_json_{label}",
                response_schema=response_schema,
            )
        except LLMError as e:
            attempts.append(f"{flash_model}@{label}: {str(e)[:100]}")
            if not any(sig in str(e) for sig in ("429", "quota", "RESOURCE_EXHAUSTED", "rate")):
                raise
    raise LLMError(f"All Gemini keys exhausted for structured output: {attempts}")


def subst(template: str, **kwargs) -> str:
    """Replace {varname} placeholders without Python's format() (which chokes on JSON braces)."""
    out = template
    for k, v in kwargs.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def extract_json(text: str) -> str:
    """Strip markdown code fences if the LLM wrapped the JSON."""
    t = text.strip()
    if t.startswith("```"):
        # Drop first line ```json or ```
        lines = t.split("\n")
        t = "\n".join(lines[1:])
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


_AGENT_TIMEOUT_S = int(os.environ.get("LR_AGENT_TIMEOUT_S", "300"))

# ── Generic CLI-agent dispatch (no per-backend hardcoded functions) ─────────
#
# Adding a new LLM CLI = adding a spec entry below OR setting LR_AGENT_BIN/
# LR_AGENT_ARGS_JSON/LR_AGENT_PARSE env vars at runtime — no code change.
#
# Spec keys:
#   bin           : executable name (PATH-resolved or absolute)
#   args          : list of flags. By default the prompt is APPENDED as the
#                   last argv entry. To inject the prompt into a specific
#                   position, use the literal "{prompt}" placeholder somewhere
#                   in args (e.g. ["--message", "{prompt}", "--temp", "0.3"]).
#   prompt_via    : "args" (default) — prompt becomes argv (appended or via
#                   "{prompt}" placeholder) | "stdin" — prompt is piped to
#                   stdin (some CLIs accept only stdin input).
#   parser        : one of {plain_text, json_envelope, jsonl_events}
#   env           : optional dict of env vars to set just for this subprocess
#   For json_envelope:
#     text_field   : JSON path to response text (default "result")
#     cost_field   : JSON path to total cost USD (default "total_cost_usd")
#     usage_field  : JSON path to usage dict (default "usage")
#     error_field  : JSON path to error flag (default "is_error")
#
# Built-ins: claude (paid via subscription session, top quality, ~$0.11/call),
# opencode (free OSS, quality drops on >2KB prompts), gemini (free daily tier).
_AGENT_SPECS: dict[str, dict] = {
    "claude": {
        "bin": "claude",
        "args": ["-p", "--no-session-persistence", "--output-format", "json"],
        "parser": "json_envelope",
        "text_field": "result",
        "cost_field": "total_cost_usd",
        "usage_field": "usage",
        "error_field": "is_error",
    },
    "opencode": {
        "bin": "opencode",
        "args": ["run", "--format", "json"],
        "parser": "jsonl_events",
    },
    "gemini": {
        "bin": "gemini",
        "args": ["-p"],
        "parser": "plain_text",
    },
}


def _parse_json_envelope(spec: dict, stdout: str) -> tuple[str, dict]:
    """For CLIs that return a single JSON object on stdout (e.g. `claude --output-format json`)."""
    try:
        env = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"json_envelope: invalid JSON — {e}; head: {stdout[:200]}")
    if spec.get("error_field") and env.get(spec["error_field"]):
        raise LLMError(f"json_envelope: backend reports error — {env.get('api_error_status') or env}")
    text = env.get(spec.get("text_field", "result")) or ""
    if not text:
        raise LLMError(f"json_envelope: empty '{spec.get('text_field', 'result')}' field")
    u = env.get(spec.get("usage_field", "usage")) or {}
    inp = int(u.get("input_tokens") or 0)
    out = int(u.get("output_tokens") or 0)
    cc = int(u.get("cache_creation_input_tokens") or 0)
    cr = int(u.get("cache_read_input_tokens") or 0)
    return text, {
        "provider": f"agent_{spec['_name']}",
        "fallback_used": False,
        # Aliases for telemetry walker compatibility (it scans for prompt_tokens/completion_tokens)
        "prompt_tokens": inp + cc + cr,
        "completion_tokens": out,
        "input_tokens": inp,
        "output_tokens": out,
        "cache_creation_input_tokens": cc,
        "cache_read_input_tokens": cr,
        "total_tokens": inp + out + cc + cr,
        "cost_usd": float(env.get(spec.get("cost_field", "total_cost_usd")) or 0.0),
        "duration_ms": int(env.get("duration_ms") or 0),
    }


def _parse_jsonl_events(spec: dict, stdout: str) -> tuple[str, dict]:
    """For CLIs that emit one JSON event per line (e.g. `opencode --format json`).
    Concatenates `text` events and aggregates `step_finish` token counts."""
    text_parts: list[str] = []
    total = inp = out = 0
    cost = 0.0
    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        et = evt.get("type")
        part = evt.get("part") or {}
        if et == "text" and part.get("type") == "text":
            text_parts.append(part.get("text", ""))
        elif et == "step_finish":
            tk = part.get("tokens") or {}
            total += int(tk.get("total") or 0)
            inp += int(tk.get("input") or 0)
            out += int(tk.get("output") or 0)
            cost += float(part.get("cost") or 0.0)
    text = "".join(text_parts).strip()
    if not text:
        raise LLMError("jsonl_events: no text events in stdout")
    return text, {
        "provider": f"agent_{spec['_name']}",
        "fallback_used": False,
        "total_tokens": total, "input_tokens": inp, "output_tokens": out,
        "cost_usd": cost,
    }


def _parse_plain_text(spec: dict, stdout: str) -> tuple[str, dict]:
    """For CLIs that just print the response (e.g. gemini -p, ollama run, claude -p without --output-format)."""
    text = stdout.strip()
    # Strip common ANSI prefixes some CLIs emit
    if "\x1b[" in text:
        import re as _re
        text = _re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text).strip()
    if not text:
        raise LLMError("plain_text: empty stdout")
    return text, {
        "provider": f"agent_{spec['_name']}",
        "fallback_used": False,
        "raw_chars": len(text),
        "cost_usd": 0.0,
    }


_AGENT_PARSERS = {
    "json_envelope": _parse_json_envelope,
    "jsonl_events": _parse_jsonl_events,
    "plain_text": _parse_plain_text,
}


def _load_user_agents_yaml() -> dict:
    """Optional user-defined agents at ~/.linkright/agents.yaml. Each top-level
    key under 'agents:' is a backend name; structure mirrors _AGENT_SPECS.
    Silently skipped if file missing OR PyYAML not installed."""
    path = os.path.expanduser("~/.linkright/agents.yaml")
    if not os.path.exists(path):
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return data.get("agents") or {}
    except Exception:
        return {}


def _resolve_agent_spec() -> dict:
    """Resolve active spec — checks user YAML, built-ins, then env-var overrides.
    Override priority (highest wins): env vars > user YAML > built-ins."""
    name = os.environ.get("LR_AGENT_BACKEND", "claude").lower()
    user_specs = _load_user_agents_yaml()
    spec = dict(user_specs.get(name) or _AGENT_SPECS.get(name) or {})
    # Per-call env overrides — any subset supported, missing keys inherit
    overrides = {
        "bin": "LR_AGENT_BIN",
        "parser": "LR_AGENT_PARSE",
        "prompt_via": "LR_AGENT_PROMPT_VIA",   # "args" | "stdin"
        "text_field": "LR_AGENT_TEXT_FIELD",
        "cost_field": "LR_AGENT_COST_FIELD",
        "usage_field": "LR_AGENT_USAGE_FIELD",
        "error_field": "LR_AGENT_ERROR_FIELD",
    }
    for k, ev in overrides.items():
        if (v := os.environ.get(ev)):
            spec[k] = v
    if (env_args := os.environ.get("LR_AGENT_ARGS_JSON")):
        try:
            spec["args"] = json.loads(env_args)
        except json.JSONDecodeError as e:
            raise LLMError(f"LR_AGENT_ARGS_JSON: invalid JSON — {e}")
    if (env_envjson := os.environ.get("LR_AGENT_ENV_JSON")):
        try:
            spec["env"] = json.loads(env_envjson)
        except json.JSONDecodeError as e:
            raise LLMError(f"LR_AGENT_ENV_JSON: invalid JSON — {e}")
    if not spec.get("bin"):
        raise LLMError(
            f"agent_chat: no spec for LR_AGENT_BACKEND='{name}'. "
            f"Built-ins: {sorted(_AGENT_SPECS)}. Add to ~/.linkright/agents.yaml "
            "or override via LR_AGENT_BIN + LR_AGENT_ARGS_JSON + LR_AGENT_PARSE."
        )
    spec["_name"] = name
    return spec


def _expand_args(args: list, *, prompt: str, system: str, user: str,
                 model: str | None, temperature: float, max_tokens: int) -> tuple[list, bool]:
    """Walk argv replacing placeholder tokens. Returns (new_args, prompt_was_placed).
    Placeholders: {prompt} {system} {user} {model} {temperature} {max_tokens}."""
    placed = False
    out = []
    for a in args:
        if not isinstance(a, str):
            out.append(a)
            continue
        if "{prompt}" in a:
            a = a.replace("{prompt}", prompt); placed = True
        if "{system}" in a: a = a.replace("{system}", system or "")
        if "{user}" in a: a = a.replace("{user}", user or "")
        if "{model}" in a and model: a = a.replace("{model}", model)
        if "{temperature}" in a: a = a.replace("{temperature}", str(temperature))
        if "{max_tokens}" in a: a = a.replace("{max_tokens}", str(max_tokens))
        out.append(a)
    return out, placed


def agent_chat(
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Generic CLI-subprocess LLM dispatch — no per-backend hardcoded paths.

    Active when LR_LLM_MODE=agent. Maximum user control via three layers:

    1. Built-in specs: claude, opencode, gemini (in _AGENT_SPECS).
    2. User YAML: ~/.linkright/agents.yaml — define unlimited backends.
       Example:
         agents:
           gpt5:
             bin: my-gpt5-cli
             args: [chat, --model, gpt-5, --json]
             parser: json_envelope
             text_field: response
           local_ollama:
             bin: ollama
             args: [run, llama3, "{prompt}"]
             parser: plain_text
    3. Per-run env vars (override anything):
         LR_AGENT_BACKEND=...           pick which spec to use
         LR_AGENT_BIN=...               override the binary path
         LR_AGENT_ARGS_JSON='[...]'     override args (JSON list)
         LR_AGENT_PARSE=...             plain_text|json_envelope|jsonl_events
         LR_AGENT_PROMPT_VIA=args|stdin how prompt reaches the CLI
         LR_AGENT_TEXT_FIELD=...        for json_envelope: text path
         LR_AGENT_COST_FIELD=...        for json_envelope: cost path
         LR_AGENT_ENV_JSON='{"K":"V"}'  extra env vars for the subprocess
         LR_AGENT_MODEL=...             value substituted into '{model}' arg slots
         LR_AGENT_TIMEOUT_S=...         subprocess timeout (default 300)

    Args (flags) support placeholder tokens {prompt} {system} {user} {model}
    {temperature} {max_tokens} — substituted at call time. If args contains no
    {prompt} placeholder, the prompt is appended as the last argv entry
    (works for claude/opencode/gemini etc.).

    Free-first: 'opencode' free OSS, 'claude' uses logged-in subscription,
    'gemini' free daily tier. Add Ollama / vllm / mlx / any local CLI as a
    spec — no code change required.
    """
    # Phase 2 — deterministic override. Each CLI backend honors temperature
    # via the {temperature} placeholder substitution in its args. Subprocess
    # backends typically don't expose seed; we surface
    # deterministic_seed_supported=False in usage so telemetry can flag this
    # as a potential non-determinism source.
    det_applied = False
    if _is_deterministic():
        temperature = 0.0
        det_applied = True

    spec = _resolve_agent_spec()
    combined = (system.strip() + "\n\n" + user.strip()) if system else user
    model = os.environ.get("LR_AGENT_MODEL")

    expanded, placed = _expand_args(
        list(spec.get("args", [])),
        prompt=combined, system=system or "", user=user or "",
        model=model, temperature=temperature, max_tokens=max_tokens,
    )
    cmd = [spec["bin"]] + expanded
    prompt_via = (spec.get("prompt_via") or "args").lower()
    if prompt_via == "args" and not placed:
        cmd.append(combined)
    stdin_input = combined if prompt_via == "stdin" else None

    # Subprocess env: inherit + per-spec overrides
    env = None
    if spec.get("env"):
        env = {**os.environ, **{str(k): str(v) for k, v in (spec["env"] or {}).items()}}

    timeout = int(os.environ.get("LR_AGENT_TIMEOUT_S", _AGENT_TIMEOUT_S))
    try:
        proc = subprocess.run(
            cmd, input=stdin_input, capture_output=True, text=True,
            timeout=timeout, check=False, env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise LLMError(f"agent_chat[{spec['_name']}]: {type(e).__name__}: {e}")
    if proc.returncode != 0 or not proc.stdout:
        raise LLMError(
            f"agent_chat[{spec['_name']}]: {spec['bin']} exit {proc.returncode}; "
            f"stderr={proc.stderr[:300]}"
        )
    parser = _AGENT_PARSERS.get(spec.get("parser", "plain_text"))
    if not parser:
        raise LLMError(
            f"agent_chat[{spec['_name']}]: unknown parser '{spec.get('parser')}'. "
            f"Built-in parsers: {sorted(_AGENT_PARSERS)}."
        )
    text, usage = parser(spec, proc.stdout)
    usage["deterministic_applied"] = det_applied
    usage["deterministic_seed_supported"] = False  # CLI subprocesses don't expose seed
    return text, usage


def openrouter_chat(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """OpenRouter chat completion — routes to meta-llama/llama-3.3-70b-instruct.
    Same model class as prod Groq, so quality matches.

    2026-05-06: migrated to _collect_keys rotation (OPENROUTER_API_KEY + _1.._4),
    matching the pattern used by Groq/Cerebras/SambaNova/Z.ai. On per-key 429 or
    402-credits-exhausted, marks that key cooling and tries the next one.
    """
    keys = _collect_keys("OPENROUTER_API_KEY")
    if not keys:
        raise LLMError("OPENROUTER_API_KEY not set; cannot call OpenRouter")
    model = model or os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    last_err: Optional[Exception] = None
    for label, api_key in keys:
        tag = f"openrouter_{label}"
        if _is_cooling(tag):
            continue
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        det_applied = _apply_deterministic_overrides(payload)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        t0 = time.time()
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(OPENROUTER_URL, json=payload, headers=headers)
            # Iter-08 (2026-04-23): adaptive 402 — OpenRouter error often says
            # "can only afford N tokens". Parse N and retry with reduced max_tokens.
            if resp.status_code == 402:
                import re as _re402
                body = resp.text or ""
                m = _re402.search(r"can only afford\s+(\d+)", body)
                if m:
                    new_max = max(500, int(m.group(1)) - 50)  # leave 50-token buffer
                    payload["max_tokens"] = new_max
                    with httpx.Client(timeout=120.0) as client:
                        resp = client.post(OPENROUTER_URL, json=payload, headers=headers)
                if resp.status_code == 402:
                    # Credits exhausted on this key — cool it and try next
                    _mark_cooling(tag, "402-credits")
                    last_err = LLMError(f"OpenRouter {tag} 402: credits exhausted")
                    continue
            dt = time.time() - t0
            if resp.status_code == 429:
                _mark_cooling(tag, "429")
                last_err = LLMError(f"OpenRouter {tag} 429: rate limited")
                continue
            if resp.status_code != 200:
                raise LLMError(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
            _clear_cooling(tag)
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = {
                "provider": f"openrouter_{label}",
                "model": model,
                "latency_s": round(dt, 2),
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens"),
                "cached_tokens": _cached_tokens(data),
                "deterministic_applied": det_applied,
                "deterministic_seed_supported": True,
            }
            return text, usage
        except LLMError:
            raise
        except Exception as e:
            last_err = LLMError(f"OpenRouter {tag}: {type(e).__name__}: {str(e)[:200]}")
    raise last_err or LLMError("OpenRouter: all keys exhausted or cooling")


def cerebras_chat(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Cerebras Cloud chat completion (OpenAI-compatible). Llama 3.3 70B, same model as prod Groq.

    Used as the tertiary fallback when Groq and Gemini are both rate-limited.
    """
    if os.environ.get("LR_LLM_MODE", "").lower() == "agent":
        return agent_chat(system, user, temperature=temperature, max_tokens=max_tokens)
    keys = _collect_keys("CEREBRAS_API_KEY")
    if not keys:
        raise LLMError("CEREBRAS_API_KEY not set; skipping cerebras provider")
    # 2026-05-01: per Cerebras docs free tier = llama3.1-8b (prod-reliable),
    # qwen-3-235b (preview, often 429). Use llama3.1-8b as safe default.
    model = model or os.environ.get("CEREBRAS_MODEL", "llama3.1-8b")
    last_err: Optional[Exception] = None
    for label, api_key in keys:
        tag = f"cerebras_{label}"
        if _is_cooling(tag):
            continue
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        det_applied = _apply_deterministic_overrides(payload)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        t0 = time.time()
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(CEREBRAS_URL, json=payload, headers=headers)
            dt = time.time() - t0
            if resp.status_code != 200:
                err = LLMError(f"Cerebras {resp.status_code}: {resp.text[:500]}")
                last_err = err
                if any(s in str(err) for s in ("429", "rate", "quota", "high traffic")):
                    _mark_cooling(tag)
                    continue
                raise err
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = {
                "provider": "cerebras",
                "model": model,
                "api_key_label": label,
                "latency_s": round(dt, 2),
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens"),
                "cached_tokens": _cached_tokens(data),
                "deterministic_applied": det_applied,
                "deterministic_seed_supported": True,
            }
            _clear_cooling(tag)
            return text, usage
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_err = LLMError(f"Cerebras network error on {label}: {e}")
            continue
    raise last_err or LLMError("all Cerebras keys exhausted")


def cerebras_8b_chat(
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 2000,
) -> tuple[str, dict]:
    """Cerebras Llama 3.1 8B — ~2200 tok/s, FREE tier, lightweight.

    Iter-06 (2026-04-23): ideal for atomic sub-second tasks:
      - step_12 atomic_pad, atomic_polish (per-bullet rewrites)
      - step_13 Pass D width tuning (filler word adjust)
      - Any simple rewrite where 8B reasoning is sufficient.

    NOT suitable for structured JSON (use Gemini Flash Lite + schema for that),
    heavy reasoning (use Groq 70B / Cerebras 235B), or long-form generation.

    Rate limits on free tier: approx 250K TPM, 1K RPM (as of 2026-04-23).
    """
    return cerebras_chat(
        system=system, user=user,
        model=os.environ.get("CEREBRAS_8B_MODEL", "llama3.1-8b"),
        temperature=temperature, max_tokens=max_tokens,
    )


def cerebras_qwen_chat(
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Cerebras Qwen 3 235B (preview) — high-quality, free tier but rate-limited.

    2026-05-01 update: Cerebras's qwen-3-235b is currently a PREVIEW model with
    reduced free-tier rate limits (per inference-docs.cerebras.ai). Frequent 429s.
    Pattern: try qwen-235b first (best quality); on 429, fall back to llama3.1-8b
    (production tier, more reliable). Caller still gets a working response.
    """
    try:
        return cerebras_chat(
            system=system, user=user,
            model="qwen-3-235b-a22b-instruct-2507",
            temperature=temperature, max_tokens=max_tokens,
        )
    except LLMError as e:
        # 429 / 503 = preview model overloaded → fall back to production-tier 8B
        if "429" in str(e) or "high traffic" in str(e).lower() or "503" in str(e):
            return cerebras_chat(
                system=system, user=user,
                model="llama3.1-8b",
                temperature=temperature, max_tokens=max_tokens,
            )
        raise


# ── Route 3 (2026-05-01): 3 new free-tier providers ─────────────────────────
#
# All 3 added as cascade fallbacks for sustained $0 operation. None require a
# subscription; each has a free signup. Wire into chat_with_fallback below.
#   - zhipu_chat       → Z.ai GLM-4.5-Flash (free unlimited per docs, OpenAI-compat)
#   - sambanova_chat   → SambaNova Cloud Llama-3.3-70B (20 RPM free)
#   - cloudflare_chat  → Cloudflare Workers AI (10K Neurons/day free, OpenAI-compat)


def zhipu_chat(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Z.ai (Zhipu) GLM chat completion. OpenAI-compatible API.

    Free tier: GLM-4.5-Flash and similar; signup at z.ai.
    Env: ZHIPU_API_KEY (or Z_AI_API_KEY). Model override: ZHIPU_MODEL.
    """
    if os.environ.get("LR_LLM_MODE", "").lower() == "agent":
        return agent_chat(system, user, temperature=temperature, max_tokens=max_tokens)
    keys = _collect_keys("ZHIPU_API_KEY")
    if not keys:
        # legacy alias support
        alt = os.environ.get("Z_AI_API_KEY")
        if alt:
            keys = [("primary", alt)]
        else:
            raise LLMError("ZHIPU_API_KEY (or Z_AI_API_KEY) not set; skipping Z.ai")
    model = model or os.environ.get("ZHIPU_MODEL", "glm-4.5-flash")
    last_err: Optional[Exception] = None
    for label, api_key in keys:
        tag = f"zhipu_{label}"
        if _is_cooling(tag):
            continue
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        det_applied = _apply_deterministic_overrides(payload)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        t0 = time.time()
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(ZHIPU_URL, json=payload, headers=headers)
            dt = time.time() - t0
            if resp.status_code != 200:
                err = LLMError(f"Z.ai {resp.status_code}: {resp.text[:500]}")
                last_err = err
                if any(s in str(err) for s in ("429", "rate", "quota")):
                    _mark_cooling(tag)
                    continue
                raise err
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = {
                "provider": "zhipu",
                "model": model,
                "api_key_label": label,
                "latency_s": round(dt, 2),
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens"),
                "cached_tokens": _cached_tokens(data),
                "deterministic_applied": det_applied,
                "deterministic_seed_supported": True,
            }
            _clear_cooling(tag)
            return text, usage
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_err = LLMError(f"Z.ai network error on {label}: {e}")
            continue
    raise last_err or LLMError("all Z.ai keys exhausted")


def sambanova_chat(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """SambaNova Cloud chat completion. OpenAI-compatible API.

    Free tier: Llama-3.3-70B at 20 RPM. Signup at cloud.sambanova.ai.
    Env: SAMBANOVA_API_KEY. Model override: SAMBANOVA_MODEL.
    """
    if os.environ.get("LR_LLM_MODE", "").lower() == "agent":
        return agent_chat(system, user, temperature=temperature, max_tokens=max_tokens)
    keys = _collect_keys("SAMBANOVA_API_KEY")
    if not keys:
        raise LLMError("SAMBANOVA_API_KEY not set; skipping SambaNova")
    model = model or os.environ.get("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")
    last_err: Optional[Exception] = None
    for label, api_key in keys:
        tag = f"sambanova_{label}"
        if _is_cooling(tag):
            continue
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        det_applied = _apply_deterministic_overrides(payload)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        t0 = time.time()
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(SAMBANOVA_URL, json=payload, headers=headers)
            dt = time.time() - t0
            if resp.status_code != 200:
                err = LLMError(f"SambaNova {resp.status_code}: {resp.text[:500]}")
                last_err = err
                if any(s in str(err) for s in ("429", "rate", "quota")):
                    _mark_cooling(tag)
                    continue
                raise err
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = {
                "provider": "sambanova",
                "model": model,
                "api_key_label": label,
                "latency_s": round(dt, 2),
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens"),
                "cached_tokens": _cached_tokens(data),
                "deterministic_applied": det_applied,
                "deterministic_seed_supported": True,
            }
            _clear_cooling(tag)
            return text, usage
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_err = LLMError(f"SambaNova network error on {label}: {e}")
            continue
    raise last_err or LLMError("all SambaNova keys exhausted")


def cloudflare_chat(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Cloudflare Workers AI chat completion. OpenAI-compatible endpoint.

    Free tier: 10K Neurons/day. Signup at workers.cloudflare.com.
    Env: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID. Model override: CLOUDFLARE_MODEL.
    Default model: Llama-3.3-70b-instruct-fp8-fast (per CF Workers AI catalog).
    """
    if os.environ.get("LR_LLM_MODE", "").lower() == "agent":
        return agent_chat(system, user, temperature=temperature, max_tokens=max_tokens)
    # Paired rotation: token + account_id together (Cloudflare-specific shape)
    pairs: list[tuple[str, str, str]] = []
    seen: set = set()
    pt = os.environ.get("CLOUDFLARE_API_TOKEN")
    pa = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if pt and pa:
        pairs.append(("primary", pt, pa))
        seen.add(pt)
    for i in range(1, 5):
        t = os.environ.get(f"CLOUDFLARE_API_TOKEN_{i}")
        a = os.environ.get(f"CLOUDFLARE_ACCOUNT_ID_{i}")
        if t and a and t not in seen:
            pairs.append((f"k{i}", t, a))
            seen.add(t)
    if not pairs:
        raise LLMError(
            "CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID not set; skipping Cloudflare"
        )
    model = model or os.environ.get(
        "CLOUDFLARE_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    last_err: Optional[Exception] = None
    for label, api_token, account_id in pairs:
        tag = f"cloudflare_{label}"
        if _is_cooling(tag):
            continue
        url = CLOUDFLARE_OPENAI_URL_TMPL.format(account_id=account_id)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        det_applied = _apply_deterministic_overrides(payload)
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        t0 = time.time()
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(url, json=payload, headers=headers)
            dt = time.time() - t0
            if resp.status_code != 200:
                err = LLMError(f"Cloudflare {resp.status_code}: {resp.text[:500]}")
                last_err = err
                if any(s in str(err) for s in ("429", "rate", "quota", "neuron")):
                    _mark_cooling(tag)
                    continue
                raise err
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = {
                "provider": "cloudflare",
                "model": model,
                "api_key_label": label,
                "latency_s": round(dt, 2),
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens"),
                "cached_tokens": _cached_tokens(data),
                "deterministic_applied": det_applied,
                "deterministic_seed_supported": True,
            }
            _clear_cooling(tag)
            return text, usage
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_err = LLMError(f"Cloudflare network error on {label}: {e}")
            continue
    raise last_err or LLMError("all Cloudflare account pairs exhausted")


def chat_with_fallback(
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 4000,
    prefer: str = "groq_70b",
) -> tuple[str, dict]:
    """Call Groq 70B → Gemini Flash rotation (KEY_1/2/3) → Cerebras → OpenRouter,
    cascading on 429/5xx. All Pro routing removed 2026-04-23 (cost-guardrail).

    Iter-05 (2026-04-23): Gemini 2.5 Pro permanently REMOVED from fallback chain.
    Pro's thinking tokens (5-10K per call) burn real money. Flash only.

    2026-05-01: when LR_LLM_MODE=agent, route through agent_chat (opencode subprocess)
    instead of the API cascade. This bypasses API keys entirely. See agent_chat docstring.
    """
    if os.environ.get("LR_LLM_MODE", "").lower() == "agent":
        return agent_chat(system, user, temperature=temperature, max_tokens=max_tokens)
    attempts: list[dict] = []
    # Iter-08 (2026-04-23): cascade cap to prevent wasted retries.
    # Each attempted provider counts; once _CASCADE_MAX_PROVIDERS reached, bail.
    providers_tried = 0

    if prefer == "groq_70b" and not _is_cooling("groq_70b"):
        providers_tried += 1
        try:
            text, usage = groq_chat(system, user, temperature=temperature, max_tokens=max_tokens)
            usage["fallback_used"] = False
            _clear_cooling("groq_70b")
            return text, usage
        except LLMError as e:
            attempts.append({"provider": "groq_70b", "error": str(e)[:200]})
            if "429" in str(e):
                _mark_cooling("groq_70b", "429")
            elif "rate" in str(e).lower() or "quota" in str(e).lower():
                _mark_cooling("groq_70b", "rate/quota")
            elif "not set" in str(e):
                pass  # missing key — fall through to next provider in cascade
            else:
                raise
    elif _is_cooling("groq_70b"):
        attempts.append({"provider": "groq_70b", "error": "skipped (cooling)"})
    # 2026-05-01: Gemini block MOVED to position 6 (just before OpenRouter) —
    # Gemini Flash Lite is PAID ($0.075/$0.30 per 1M tok), so we exhaust all
    # FREE providers first (Cerebras → SambaNova → Cloudflare → Z.ai) before
    # incurring any cost. Per Jane instruction: "gemini last me use krna wo paid hai abhi".

    # Tertiary: Cerebras qwen-235B (skip if still in cascade cap or cooling)
    if providers_tried < _CASCADE_MAX_PROVIDERS and not _is_cooling("cerebras"):
        providers_tried += 1
        try:
            text, usage = cerebras_chat(system, user, temperature=temperature, max_tokens=max_tokens)
            usage["fallback_used"] = True
            usage["fallback_chain"] = attempts + [{"provider": "cerebras", "error": None}]
            _clear_cooling("cerebras")
            return text, usage
        except LLMError as e:
            attempts.append({"provider": "cerebras", "error": str(e)[:200]})
            if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                _mark_cooling("cerebras", "429/queue")
            elif "not set" in str(e):
                pass  # missing key — fall through to next provider in cascade
            else:
                raise
    elif _is_cooling("cerebras"):
        attempts.append({"provider": "cerebras", "error": "skipped (cooling)"})

    # Iter-05 (2026-04-23): Gemini 2.5 Pro REMOVED — cost guardrail.
    # Pro's thinking tokens cost real money (~₹5-15 per call). Flash only.

    # 2026-05-01 — Route 3: 3 new free-tier providers inserted before OpenRouter.
    # Each gracefully raises LLMError if its API key is missing (auto-cascade).

    # Free tier (insert order chosen for quality + reliability):
    # SambaNova (Llama-70B at 20 RPM, free)
    if not _is_cooling("sambanova"):
        try:
            text, usage = sambanova_chat(system, user, temperature=temperature, max_tokens=max_tokens)
            usage["fallback_used"] = True
            usage["fallback_chain"] = attempts + [{"provider": "sambanova", "error": None}]
            _clear_cooling("sambanova")
            return text, usage
        except LLMError as e:
            attempts.append({"provider": "sambanova", "error": str(e)[:200]})
            if any(s in str(e) for s in ("429", "rate", "quota")):
                _mark_cooling("sambanova", "rate-limit")
            elif "not set" not in str(e):
                # Real error other than missing key — log but continue cascade
                pass
    elif _is_cooling("sambanova"):
        attempts.append({"provider": "sambanova", "error": "skipped (cooling)"})

    # Cloudflare Workers AI (10K Neurons/day free, multi-model menu)
    if not _is_cooling("cloudflare"):
        try:
            text, usage = cloudflare_chat(system, user, temperature=temperature, max_tokens=max_tokens)
            usage["fallback_used"] = True
            usage["fallback_chain"] = attempts + [{"provider": "cloudflare", "error": None}]
            _clear_cooling("cloudflare")
            return text, usage
        except LLMError as e:
            attempts.append({"provider": "cloudflare", "error": str(e)[:200]})
            if any(s in str(e) for s in ("429", "rate", "quota")):
                _mark_cooling("cloudflare", "rate-limit")
    elif _is_cooling("cloudflare"):
        attempts.append({"provider": "cloudflare", "error": "skipped (cooling)"})

    # Z.ai GLM (high-quality tail, free Flash tier)
    if not _is_cooling("zhipu"):
        try:
            text, usage = zhipu_chat(system, user, temperature=temperature, max_tokens=max_tokens)
            usage["fallback_used"] = True
            usage["fallback_chain"] = attempts + [{"provider": "zhipu", "error": None}]
            _clear_cooling("zhipu")
            return text, usage
        except LLMError as e:
            attempts.append({"provider": "zhipu", "error": str(e)[:200]})
            if any(s in str(e) for s in ("429", "rate", "quota")):
                _mark_cooling("zhipu", "rate-limit")
    elif _is_cooling("zhipu"):
        attempts.append({"provider": "zhipu", "error": "skipped (cooling)"})

    # 2026-05-01: Gemini Flash Lite — PAID ($0.075/$0.30 per 1M tok). Position 6
    # in cascade because all FREE providers above (Groq, Cerebras, SambaNova,
    # Cloudflare, Z.ai) get tried first. Rotates through 4 keys on 429/quota.
    gemini_keys = [
        ("KEY_default", os.environ.get("GEMINI_API_KEY")),
        ("KEY_1", os.environ.get("GEMINI_API_KEY_1")),
        ("KEY_2", os.environ.get("GEMINI_API_KEY_2")),
        ("KEY_3", os.environ.get("GEMINI_API_KEY_3")),
    ]
    gemini_keys = [(label, k) for label, k in gemini_keys if k]
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
    for label, api_key in gemini_keys:
        if providers_tried >= _CASCADE_MAX_PROVIDERS:
            attempts.append({"provider": f"gemini_{label}", "error": "skipped (cascade cap)"})
            break
        key_tag = f"gemini_{label}"
        if _is_cooling(key_tag):
            attempts.append({"provider": key_tag, "error": "skipped (cooling)"})
            continue
        providers_tried += 1
        try:
            text, usage = _gemini_call(
                api_key=api_key, model=gemini_model, system=system, user=user,
                temperature=temperature, max_output_tokens=min(max_tokens, 8000),
                provider_tag=f"gemini_{label}",
            )
            usage["fallback_used"] = True
            usage["fallback_chain"] = attempts + [{"provider": f"gemini_{label}", "error": None}]
            _clear_cooling(key_tag)
            return text, usage
        except LLMError as e:
            attempts.append({"provider": f"gemini_{label}", "error": str(e)[:100]})
            if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                _mark_cooling(key_tag, "429/quota")
            else:
                break  # non-rate-limit failure → stop Gemini, fall through to OpenRouter

    # Last resort: OpenRouter — SKIP on persistent 402 (credits exhausted)
    try:
        text, usage = openrouter_chat(system, user, temperature=temperature, max_tokens=max_tokens)
        usage["fallback_used"] = True
        usage["fallback_chain"] = attempts + [{"provider": "openrouter", "error": None}]
        return text, usage
    except LLMError as e:
        attempts.append({"provider": "openrouter", "error": str(e)[:200]})
        # Detect "no keys configured" pattern — every attempt failed with "API_KEY not set".
        # This usually means the user pip-installed but never ran `linkright setup`.
        # Match any "<KEY_NAME> not set" / "API_TOKEN not set" / parenthetical-alias
        # variant — covers Groq/Cerebras (API_KEY), Cloudflare (API_TOKEN), Z.ai
        # ("ZHIPU_API_KEY (or Z_AI_API_KEY) not set"). Substring match instead of
        # full-pattern equality so any provider's "<NAME> not set" message qualifies.
        all_no_key = all(
            "not set" in (a.get("error") or "")
            for a in attempts
        ) and len(attempts) > 0
        if all_no_key:
            raise LLMError(
                "No LLM API keys configured. Run `linkright setup` to add a free Groq key "
                "(https://console.groq.com — covers ~14,400 tailoring requests/day on the "
                "llama-3.1-8b free tier)."
            )
        # If it's a 402 credits error, the whole cascade is blocked. Surface clearly.
        if "402" in str(e) or "credits" in str(e).lower():
            raise LLMError(
                "All LLM providers exhausted: Groq/Gemini rate-limited, Cerebras unavailable, "
                f"OpenRouter out of credits. Attempts: {attempts}"
            )
        raise


# ── Tier router (Phase 1 — 2026-05-01) ─────────────────────────────────────
#
# Per-call-site quality routing. Each LLM call site declares its `klass`
# (A/B/C/D) and `intent` (short label). tier_chat picks the right primary
# provider for that quality tier, falls through to chat_with_fallback's
# cascade on failure, and tags usage dict with klass + intent so telemetry
# can roll up cost and quality per-tier and per-site.
#
# The 4 classes capture the reasoning-depth axis:
#   A — extraction / presence checks (structured, low judgment)
#   B — surgical edit / summary / condense / synonym (format-aware rewrite)
#   C — generation / conversational (creative coherence)
#   D — judgment / multi-step reasoning (today's full cascade preserved)
#
# Why this isn't a full registry: chat_with_fallback already implements the
# free-tier cascade discipline. tier_chat is a thin selector on top — it just
# picks the entry point.

TIER_POLICY: dict[str, list[str]] = {
    # 2026-05-01 small-first principle: smaller models first (better RPM/TPD
    # availability), upgrade to 70B only when quality demands it. Per Jane:
    # "preference small models pr hi rakho unless usse quality na aa rhi ho".
    "A": ["groq_8b", "cerebras_8b", "cloudflare_3b", "cloudflare_8b"],
    "B": ["groq_8b", "cerebras_8b", "cloudflare_8b", "groq_70b", "cloudflare_70b"],
    "C": ["groq_8b", "cloudflare_8b", "groq_70b"],
    "D": ["groq_8b", "groq_70b", "cloudflare_70b"],
}

TIER_TEMPERATURE: dict[str, float] = {
    "A": 0.1,
    "B": 0.2,
    "C": 0.5,
    "D": 0.3,
}


def _try_provider(provider: str, system: str, user: str,
                  temperature: float, max_tokens: int) -> tuple[str, dict]:
    """Single attempt against a named provider. Raises LLMError on failure.

    2026-05-01: extended to dispatch small-first model tags
    (groq_8b, cloudflare_3b, cloudflare_8b, cloudflare_70b) per small-model
    preference policy.
    """
    if _is_cooling(provider):
        raise LLMError(f"{provider} cooling")
    try:
        if provider == "groq_8b":
            text, usage = groq_chat(
                system=system, user=user,
                model=os.environ.get("GROQ_MODEL_8B", "llama-3.1-8b-instant"),
                temperature=temperature, max_tokens=max_tokens,
            )
        elif provider == "cerebras_8b":
            text, usage = cerebras_8b_chat(
                system=system, user=user,
                temperature=temperature, max_tokens=max_tokens,
            )
        elif provider == "cerebras_qwen":
            text, usage = cerebras_qwen_chat(
                system=system, user=user,
                temperature=temperature, max_tokens=max_tokens,
            )
        elif provider == "cloudflare_3b":
            text, usage = cloudflare_chat(
                system=system, user=user,
                model="@cf/meta/llama-3.2-3b-instruct",
                temperature=temperature, max_tokens=max_tokens,
            )
        elif provider == "cloudflare_8b":
            text, usage = cloudflare_chat(
                system=system, user=user,
                model="@cf/meta/llama-3.1-8b-instruct",
                temperature=temperature, max_tokens=max_tokens,
            )
        elif provider == "cloudflare_70b":
            text, usage = cloudflare_chat(
                system=system, user=user,
                model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                temperature=temperature, max_tokens=max_tokens,
            )
        elif provider == "groq_70b":
            text, usage = chat_with_fallback(
                system=system, user=user,
                temperature=temperature, max_tokens=max_tokens,
                prefer="groq_70b",
            )
        else:
            raise LLMError(f"Unknown provider in tier policy: {provider}")
        _clear_cooling(provider)
        return text, usage
    except LLMError as e:
        if any(sig in str(e) for sig in ("429", "quota", "rate", "RESOURCE_EXHAUSTED")):
            _mark_cooling(provider)
        raise


def _resolve_tier_override(intent: str) -> Optional[str]:
    """Phase 3 — check for env-var override for this intent.

    Order: exact match `LR_TIER_OVERRIDE_<intent>` → prefix matches walking
    down the underscore-separated parts (longest prefix wins). Lets hypothesis
    tests target a single call site OR all sites under a step prefix.

    Examples:
      LR_TIER_OVERRIDE_step_09_summary=cerebras_qwen     # single site
      LR_TIER_OVERRIDE_step_10=groq_70b                  # all step_10 variants
    """
    direct = os.environ.get(f"LR_TIER_OVERRIDE_{intent}", "").strip()
    if direct:
        return direct
    parts = intent.split("_")
    for i in range(len(parts) - 1, 0, -1):
        prefix = "_".join(parts[:i])
        candidate = os.environ.get(f"LR_TIER_OVERRIDE_{prefix}", "").strip()
        if candidate:
            return candidate
    return None


def tier_chat(
    system: str,
    user: str,
    *,
    klass: str,
    intent: str,
    temperature: Optional[float] = None,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Route an LLM call by quality tier with telemetry tagging.

    Args:
      system, user: prompt parts
      klass: "A" / "B" / "C" / "D" — quality tier (see module-top comment)
      intent: short site label (e.g. "step_09_summary"); logged for per-site queries
      temperature: optional caller override; tier-default if None
      max_tokens: completion cap

    Returns:
      (text, usage) — usage dict carries `klass` and `intent` fields plus the
      provider's standard token/latency/cost data.

    LR_LLM_MODE=agent shortcircuit happens at the underlying helpers'
    layer (cerebras_chat, chat_with_fallback both honor it), so agent-mode
    is automatic — no special handling here.

    Phase 3 — env var `LR_TIER_OVERRIDE_<intent>` (or step-prefix variant)
    forces this site to a specific provider, skipping the tier policy. Used
    by the hypothesis-test command for single-variable experiments.
    """
    if klass not in TIER_POLICY:
        raise ValueError(f"Unknown tier class: {klass!r}. Expected A/B/C/D.")

    if temperature is None:
        temperature = TIER_TEMPERATURE[klass]

    # Phase 3 — per-intent override (hypothesis-test enabler).
    override = _resolve_tier_override(intent)
    if override:
        try:
            text, usage = _try_provider(
                override, system, user, temperature, max_tokens,
            )
            usage["klass"] = klass
            usage["intent"] = intent
            usage["tier_override"] = override
            return text, usage
        except LLMError:
            # Fall through to standard tier policy on override failure.
            pass

    # Token counter — estimate before send (4 chars ≈ 1 token, rough but instant)
    _input_est = (len(system) + len(user)) // 4
    import sys as _sys
    print(
        f"  [tokens] {intent}  sending ~{_input_est:,} input tokens …",
        file=_sys.stderr, flush=True,
    )

    last_err: Optional[Exception] = None
    for provider in TIER_POLICY[klass]:
        try:
            text, usage = _try_provider(
                provider, system, user, temperature, max_tokens,
            )
            usage["klass"] = klass
            usage["intent"] = intent
            _log_token_usage(intent, usage)
            return text, usage
        except LLMError as e:
            last_err = e
            continue

    # Final safety net: full chat_with_fallback cascade — guarantees we land
    # on SOMETHING (paid OpenRouter at worst) before raising.
    text, usage = chat_with_fallback(
        system=system, user=user,
        temperature=temperature, max_tokens=max_tokens,
        prefer="groq_70b",
    )
    usage["klass"] = klass
    usage["intent"] = intent
    usage["tier_fallback"] = True
    _log_token_usage(intent, usage)
    return text, usage
