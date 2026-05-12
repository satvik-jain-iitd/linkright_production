"""Interactive setup wizard — `linkright setup`.

Goal: zero-jargon onboarding for a new user. Four core decisions +
an optional API-key step:

  1. Groq API key  (legacy primary — now part of the multi-key step)
  2. Embedder tier (fastembed / sentence-transformers / Oracle)
  3. PDF render    (Playwright / skip)
  4. API keys step (multi-provider — primary + fallbacks)

After choices, we:
  - Verify the Groq key with a live API call
  - Install any missing pip packages silently
  - Run a smoke check on each picked tier (catches misconfig early)
  - Write picks to ~/.linkright/config.yaml
  - Write API keys atomically to ~/.linkright/.env via keys.env_writer
  - Print a 3-line "you're ready" summary with the exact next command

The user never sees pip output, Python tracebacks, or model download progress
unless something fails. That's the point of the wizard — abstraction over
ten minutes of manual setup steps.
"""

from __future__ import annotations

import logging as _logging_setup
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Suppress HuggingFace telemetry + tqdm progress-bars during the embedder
# smoke-test. These env vars are read at HF library import time; setting
# them after `from fastembed import TextEmbedding` is too late.
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

# Surgical filter — drop ONLY the HF_TOKEN warning record, leave real
# errors (network failures, disk-full, auth issues) visible.
_logging_setup.getLogger("huggingface_hub").addFilter(
    lambda r: "HF_TOKEN" not in r.getMessage()
)
# S-11: Also suppress via Python warnings module — huggingface_hub emits
# UserWarning (not just logging) for the HF_TOKEN prompt on some versions.
import warnings as _warnings_setup
_warnings_setup.filterwarnings(
    "ignore",
    message=r".*unauthenticated.*HF.*Hub.*",
    category=UserWarning,
    module=r"huggingface_hub.*",
)
_warnings_setup.filterwarnings(
    "ignore",
    message=r".*HF_TOKEN.*",
    category=UserWarning,
)
import questionary
import yaml


# ─────────────────────────────────────────────────────────────────────────
# Choice catalogues — single source of truth. Add to these dicts to expose
# new options to the wizard; no other code change needed.
# ─────────────────────────────────────────────────────────────────────────

def _plural(count: int, singular: str, plural_form: str | None = None) -> str:
    """Return count + singular or plural form."""
    if plural_form is None:
        plural_form = singular + "s"
    return f"{count} {singular if count == 1 else plural_form}"


EMBEDDER_OPTIONS = [
    {
        "key": "fastembed",
        "label": "fastembed  (~130 MB local, fast CPU, free, recommended)",
        "pip": "fastembed",
        "import_check": "fastembed",
        "recommended": True,
    },
    {
        "key": "sentence_transformers",
        "label": "sentence-transformers  (~700 MB torch, higher quality, slower install)",
        "pip": "sentence-transformers",
        "import_check": "sentence_transformers",
        "recommended": False,
    },
    {
        "key": "oracle",
        "label": "Oracle Ollama  (advanced — needs your own Oracle URL + secret)",
        "pip": None,
        "import_check": None,
        "recommended": False,
    },
]

PDF_OPTIONS = [
    {
        "key": "playwright",
        "label": "Yes — install Playwright Chromium  (~80 MB, recommended)",
        "recommended": True,
    },
    {
        "key": "skip",
        "label": "No — HTML only  (skip PDF render)",
        "recommended": False,
    },
]


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

# `_pick` moved to linkright.prompts.prompt_for_choice — single source of
# truth for the recommended-marker / Ctrl+C contract used across the CLI.
# Re-exported here so the wizard's existing call sites keep working.
from linkright.prompts import prompt_for_choice as _pick  # noqa: E402


def _check_bin(name: str) -> bool:
    return shutil.which(name) is not None


def _try_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def _pip_install(package: str, stream: bool = False) -> bool:
    """Install a pip package. Returns True on success.

    If ``stream`` is True the subprocess stdout/stderr is not captured so the
    user sees live pip output (used for large packages like sentence-transformers
    where silent progress would leave the terminal frozen for minutes).
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install", package, "--progress-bar", "on"]
        if stream:
            proc = subprocess.run(cmd, timeout=600)
        else:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return proc.returncode == 0
    except Exception:
        return False


def _playwright_install() -> bool:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=600,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _write_env_key(key_name: str, value: str) -> None:
    """Write/update a single key in ~/.linkright/.env (chmod 600, in-place update).

    DEPRECATED for multi-key use — kept for backward compat with _ask_groq_key.
    New code uses keys.env_writer.write_keys() instead.
    """
    env_path = Path.home() / ".linkright" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if env_path.exists():
        lines = [l for l in env_path.read_text().splitlines() if l]  # drop blank lines
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key_name}=") or line.startswith(f"{key_name} ="):
            lines[i] = f"{key_name}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key_name}={value}")
    env_path.write_text("\n".join(lines) + "\n")
    env_path.chmod(0o600)


def _smoke_groq_key(key: str) -> tuple[bool, str]:
    """Make a live Groq API call to verify the key works. Returns (ok, message)."""
    try:
        import httpx
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            },
            timeout=10.0,
        )
        if resp.status_code == 200:
            return True, "key valid"
        if resp.status_code == 401:
            return False, "Invalid key (401 Unauthorized)"
        if resp.status_code == 404:
            return True, "Key valid (model name may have changed — harmless)"
        if resp.status_code == 429:
            return True, "Rate-limited but key is valid (429)"
        return False, f"Unexpected status {resp.status_code}"
    except Exception as e:
        return False, f"Network error: {type(e).__name__}: {str(e)[:80]}"


def _ask_groq_key() -> tuple[str, bool, str]:
    """Prompt user for Groq key, validate format, save to .env, run smoke test.

    Key is saved to ~/.linkright/.env as soon as format is valid — the smoke
    test is advisory only (network may be down during setup on VPN/firewall).
    Returns (key, smoke_ok, msg).
    """
    print("  Get a free key at: https://console.groq.com → API Keys → Create key")
    print("  (Free tier: 14,400 req/day — enough for hundreds of resumes)")
    print()
    key = questionary.password("Paste your Groq API key:").ask()
    if key is None:
        sys.exit(1)
    key = key.strip()
    if not key.startswith("gsk_") or len(key) < 20:
        return key, False, "Key format invalid (should start with 'gsk_')"
    # Save immediately — format is valid; don't gate on network reachability
    _write_env_key("GROQ_API_KEY", key)
    print("  ✓  Saved GROQ_API_KEY → ~/.linkright/.env")
    print("  Verifying key with a live Groq call…")
    ok, msg = _smoke_groq_key(key)
    if ok:
        print("  ✓  Key valid")
    else:
        print(f"  ✗  Invalid key — {msg}")
    return key, ok, msg


def _smoke_embedder(opt: dict) -> tuple[bool, str]:
    key = opt["key"]
    if key == "fastembed":
        try:
            from fastembed import TextEmbedding
            m = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            v = list(next(m.embed(["smoke test"])))
            return True, f"OK — dim {len(v)}"
        except Exception as e:
            return False, f"failed: {type(e).__name__}: {str(e)[:120]}"
    if key == "sentence_transformers":
        try:
            from sentence_transformers import SentenceTransformer
            m = SentenceTransformer(os.environ.get("LR_ST_MODEL", "all-mpnet-base-v2"))
            v = m.encode("smoke test")
            return True, f"OK — dim {len(v)}"
        except Exception as e:
            return False, f"failed: {type(e).__name__}: {str(e)[:120]}"
    if key == "oracle":
        url = os.environ.get("ORACLE_BACKEND_URL")
        secret = os.environ.get("ORACLE_BACKEND_SECRET")
        if not url or not secret:
            return False, "ORACLE_BACKEND_URL and/or ORACLE_BACKEND_SECRET not set"
        return True, "env vars present (no live call performed)"
    return False, f"unknown embedder: {key}"


def _smoke_pdf() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True, "Chromium launches OK"
    except Exception as e:
        return False, f"failed: {type(e).__name__}: {str(e)[:120]}"


# ─────────────────────────────────────────────────────────────────────────
# Step 4: Multi-key API setup
# ─────────────────────────────────────────────────────────────────────────

def _validate_key_format(spec, key_val: str) -> tuple[bool, str]:
    """Validate key format against provider spec. Returns (ok, message)."""
    if len(key_val) < spec.key_min_len:
        return False, (
            f"Key too short ({len(key_val)} chars, expected ≥{spec.key_min_len}). "
            f"Did you paste the full key?"
        )
    if spec.key_prefix and not key_val.startswith(spec.key_prefix):
        return False, (
            f"Expected format: `{spec.key_prefix}...` for {spec.name}. "
            f"Got: `{key_val[:4]}...` — check you copied the right key."
        )
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.")
    bad_chars = set(key_val) - allowed
    if bad_chars:
        return False, f"Unexpected characters in key: {bad_chars}"
    return True, "OK"


def run_api_keys_step(existing_groq_key: str = "") -> dict[str, str]:
    """Run the interactive API keys wizard step.

    Returns a dict of {env_var: value} to write via env_writer.write_keys().
    If user skips, returns {}.

    `existing_groq_key` — if user already entered a Groq key in the old step,
    pre-populate it so we don't ask twice.
    """
    from linkright.keys.catalogue import PROVIDERS, resilience_score
    from linkright.keys.env_writer import mask_key

    print()
    print("────────────────────────────────────────────────────")
    print("3 quick choices: embedder \u2022 PDF render \u2022 API keys")
    print("3/3 — API Keys (Direct mode LLM cascade)")
    print("────────────────────────────────────────────────────")
    print()
    print("  LinkRight cascades through 7 free-tier providers.")
    print("  Add 1+ keys now for redundancy — no credit cards needed for most.")
    print("  Skip if you'll use Agent mode (Claude Code / Cursor) only.")
    print()

    MODE_OPTIONS = [
        {"key": "interactive", "label": "Add keys interactively  (guided, ~2 min)", "recommended": True},
        {"key": "agent",       "label": "Skip — I'll use Agent mode only (Claude Code / Cursor)"},
        {"key": "later",       "label": "Skip — I'll add keys later via `linkright keys`"},
    ]
    mode = _pick("How would you like to add API keys?", MODE_OPTIONS)
    if mode["key"] != "interactive":
        if mode["key"] == "agent":
            print()
            print("  OK — Agent mode uses your LLM CLI tool directly.")
            print("  You can add direct-mode keys anytime: `linkright keys add groq`")
            if not shutil.which("claude"):
                print()
                print("  \u26a0 claude not found on PATH \u2014 install Claude Code first:")
                print("    https://claude.ai/code")
                print("  Or add a direct-mode key: linkright keys add groq")
        else:
            print()
            print("  OK — add keys anytime: `linkright keys add <provider>`")
        return {}

    # Interactive per-provider flow
    updates: dict[str, str] = {}

    # If user already entered Groq in the legacy step, pre-populate
    if existing_groq_key and existing_groq_key.startswith("gsk_"):
        updates["GROQ_API_KEY"] = existing_groq_key

    total_providers = len(PROVIDERS)
    for idx, spec in enumerate(PROVIDERS, start=1):
        print()
        print(f"  ────────────────────────────────────────────────")
        badge = "⭐ recommended" if spec.recommended else ""
        print(f"  {idx}/{total_providers} ▶ {spec.name}  {badge}")
        print()
        print(f"  What it is:  {spec.description}")
        print(f"  Free tier:   {spec.free_tier}")
        print(f"  Signup:      {spec.signup_url}")
        if not spec.signup_url_verified:
            print(f"  (URL unconfirmed — check provider's docs if link doesn't work)")
        print()

        # Check if primary already set (from legacy step)
        if updates.get(spec.primary_env):
            masked = mask_key(updates[spec.primary_env])
            print(f"  Primary key already set: {masked}")
            add_more = questionary.confirm(
                f"  Add a fallback key for {spec.name}?", default=False
            ).ask()
            if not add_more:
                continue
            # Find next slot for fallback
            slot_vars = spec.extra_envs
            fallback_count = 0
            for slot_var in slot_vars:
                if updates.get(slot_var):
                    fallback_count += 1
                    continue
                if fallback_count >= 3:
                    break
                ok, new_updates = _prompt_key_for_slot(spec, slot_var, fallback_count + 1, updates)
                updates.update(new_updates)
                if not ok:
                    break
                add_another = questionary.confirm(
                    f"  Add another fallback key for {spec.name}?", default=False
                ).ask()
                if not add_another:
                    break
                fallback_count += 1
            continue

        # Normal flow — ask if they want to add this provider
        PROVIDER_OPTIONS = [
            {"key": "add",  "label": f"Add primary key for {spec.name}"},
            {"key": "skip", "label": f"Skip {spec.name}"},
        ]
        action = _pick(f"Configure {spec.name}?", PROVIDER_OPTIONS, default_recommended=True)
        if action["key"] == "skip":
            continue

        # Prompt primary key
        _, new_updates = _prompt_key_for_slot(spec, spec.primary_env, 0, updates)
        updates.update(new_updates)
        if not updates.get(spec.primary_env):
            continue  # User aborted this provider

        # Offer fallbacks (up to 3)
        for fb_num, slot_var in enumerate(spec.extra_envs, start=1):
            if fb_num > 3:
                break
            add_fb = questionary.confirm(
                f"  Add fallback key {fb_num} for {spec.name}? (helps avoid rate limits)",
                default=False,
            ).ask()
            if not add_fb:
                break
            ok, new_updates = _prompt_key_for_slot(spec, slot_var, fb_num, updates)
            updates.update(new_updates)
            if not ok:
                break

    # Summary table
    if updates:
        print()
        print("  ── Keys saved ───────────────────────────────────")
        key_count = 0
        provider_count = 0
        for spec in PROVIDERS:
            provider_keys = [(v, updates[v]) for v in spec.all_env_vars if updates.get(v)]
            if provider_keys:
                provider_count += 1
                key_count += len(provider_keys)
                print(f"  ✓  {spec.name:<20}  {_plural(len(provider_keys), 'key')}")
            else:
                print(f"  —  {spec.name:<20}  (skipped)")

        score = resilience_score(key_count, provider_count)
        score_color = "\033[32m" if score in ("EXCELLENT", "GOOD") else "\033[33m"
        print()
        print(f"  {_plural(key_count, 'key')} across {_plural(provider_count, 'provider')}  |  "
              f"Cascade resilience: {score_color}{score}\033[0m")
        print()
        print("  Run `linkright keys test` to verify live status.")
    else:
        print()
        print("  No keys added. Run `linkright keys add groq` when ready.")

    # ── Path A educational note — other free providers not yet in cascade ──
    print()
    print("  ─" * 26)
    print("  ℹ  Other free LLM providers exist (not yet in cascade):")
    print()
    print("     • Mistral La Plateforme — console.mistral.ai/api-keys")
    print("     • DeepSeek              — platform.deepseek.com/api_keys")
    print("     • Together AI           — api.together.ai/settings/projects/~current/api-keys")
    print("     • HuggingFace           — huggingface.co/settings/tokens")
    print()
    print("  To request adding any of these to the cascade, open an issue:")
    print("  https://github.com/satvik-jain-iitd/linkright_production/issues/new")
    print()

    return updates


def _prompt_key_for_slot(
    spec, slot_var: str, slot_num: int, existing_updates: dict[str, str]
) -> tuple[bool, dict[str, str]]:
    """Prompt for a single key + optional paired value (Cloudflare).

    Returns (success, {var: value} updates).
    slot_num=0 means primary, 1..3 means fallback.
    """
    from linkright.keys.env_writer import mask_key

    slot_label = "primary key" if slot_num == 0 else f"fallback key {slot_num}"
    key_val = questionary.password(
        f"  Paste {spec.name} {slot_label}:"
    ).ask()
    if key_val is None:
        return False, {}
    key_val = key_val.strip()
    if not key_val:
        return False, {}

    ok, msg = _validate_key_format(spec, key_val)
    if not ok:
        print(f"  \033[33m⚠ Format warning: {msg}\033[0m")
        proceed = questionary.confirm("  Save anyway?", default=False).ask()
        if not proceed:
            print("  Skipped — key not saved.")
            return False, {}

    updates: dict[str, str] = {slot_var: key_val}
    print(f"  ✓  {slot_var} saved")

    # Cloudflare needs a paired account_id
    if spec.paired_env:
        if slot_num == 0:
            pair_var = spec.paired_env
        else:
            pair_var = f"{spec.paired_env}_{slot_num}"
        acct_id = questionary.text(
            f"  Cloudflare Account ID (find at dash.cloudflare.com → Overview → Account ID):"
        ).ask()
        if acct_id and acct_id.strip():
            updates[pair_var] = acct_id.strip()
            print(f"  ✓  {pair_var} saved")

    return True, updates


# ─────────────────────────────────────────────────────────────────────────
# Wizard entry
# ─────────────────────────────────────────────────────────────────────────

def run_wizard() -> int:
    """Returns shell exit code (0 OK, 1 user-cancel, 2 install/smoke fail)."""
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║   LinkRight setup wizard                           ║")
    print("╚════════════════════════════════════════════════════╝")
    print()

    # ── Detect existing config (for migration prompt) ──────────────
    cfg_path = Path.home() / ".linkright" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    old_mode = None
    if cfg_path.exists():
        try:
            existing = yaml.safe_load(cfg_path.read_text()) or {}
            old_mode = existing.get("default_llm_mode")
        except Exception:
            existing = {}

    # ── v0.4.0 migration: detect old agent-mode config from 0.3.0 wizard ──
    # Done BEFORE Decision 1 so agent-mode users who decline can skip the
    # Groq key prompt entirely (no point asking for a key they won't use).
    migrate = True  # default for new installs / non-agent configs
    if old_mode == "agent":
        print("⚠ Detected: your existing config uses agent mode (claude/opencode/gemini-cli).")
        print("  v0.4.0 default is direct mode (free Groq llama-3.1-8b — 14,400 req/day).")
        print()
        migrate = questionary.confirm(
            "Switch to direct mode? (recommended)",
            default=True,
        ).ask()
        if migrate is None:
            sys.exit(1)
        if migrate:
            existing.pop("agent_backend", None)
            existing.pop("default_skill_mode", None)
            print("  ✓ Migrating to direct mode (your old agent_backend is removed).")
            print()
        else:
            print("  ✓ Keeping agent mode. Skipping Groq key step.")
            print("  Tip: edit ~/.linkright/config.yaml to switch later.")
            print()

    needs_groq = not (old_mode == "agent" and not migrate)
    # Total visible steps: embedder + pdf + api-keys (Groq is now inside api-keys)
    total_steps = 3
    print(f"You'll see {total_steps} quick choices: embedder \u2022 PDF render \u2022 API keys")
    print("\u2b50 = recommended choice")
    print()

    # ── No dedicated Groq step — Groq appears as first provider in API keys step ──
    groq_key, ok_groq, msg_groq = "", True, "skipped (enter in API keys step)"

    # ── Decision 1: Embedder ───────────────────────────────────────
    embedder = _pick(f"1/{total_steps} \u2014 Which embedder?", EMBEDDER_OPTIONS)
    print()  # visual separator between decisions

    # ── Decision 2: PDF render ─────────────────────────────────────
    pdf = _pick(f"2/{total_steps} \u2014 Render PDFs from generated resumes?", PDF_OPTIONS)

    # ── Decision 4 (hidden): Skill mode (legacy — defaults to "auto") ─
    skill_mode_key = "auto"

    print()
    print("──────────────────────────────────────────────────────")
    mode_label = "direct (Groq)" if needs_groq else "agent (kept from 0.3.0)"
    emb_display = embedder['key'].replace("_", "-")
    print(f"Picks so far  \u2192  LLM: {mode_label}  \u2022  embedder: {emb_display}  \u2022  PDF: {pdf['key']}")
    print("──────────────────────────────────────────────────────")

    # ── Decision 5: Multi-provider API keys ───────────────────────
    # S-6 fix: always pass groq_key so step 4 does not re-prompt for it.
    # ok_groq failing (smoke/network) must not erase what the user already typed.
    api_key_updates = run_api_keys_step(existing_groq_key=groq_key if groq_key else "")

    print()
    print("──────────────────────────────────────────────────────")
    print("Installing missing pieces (pip, models, browsers)…")
    failures: list[str] = []

    # Embedder pip
    if embedder.get("pip"):
        if embedder.get("import_check") and not _try_import(embedder["import_check"]):
            large_pkg = embedder.get("key") == "sentence_transformers"
            if large_pkg:
                print(f"  ⬇  Installing {embedder['pip']} (~700 MB, ~2-3 min)…")
            else:
                print(f"  ⬇  pip install {embedder['pip']}  …")
            if not _pip_install(embedder["pip"], stream=large_pkg):
                failures.append(f"pip install {embedder['pip']}")
                print("     ✗ failed — see install hint at end")
            else:
                print("     ✓ done")
        else:
            print(f"  ✓  {embedder['pip']} already installed")

    # PDF render
    if pdf["key"] == "playwright":
        # Try import; if missing pip install playwright first
        if not _try_import("playwright"):
            print("  ⬇  pip install playwright  …")
            if not _pip_install("playwright"):
                failures.append("pip install playwright")
                print("     ✗ failed")
        # Browser
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                p.chromium.launch().close()
            print("  ✓  Playwright Chromium ready")
        except Exception:
            print("  ⬇  playwright install chromium  (~80 MB, ~30 s)…")
            if not _playwright_install():
                failures.append("playwright install chromium")
                print("     ✗ failed")
            else:
                print("     ✓ done")

    print()
    print("Smoke-testing your picks…")
    print(f"  Groq API key:        {'✓ valid' if ok_groq else '✗'}  {msg_groq if not ok_groq else ''}")
    # Lead-in only on fresh setup — the wizard path may trigger a model
    # download. `linkright setup --check` (which also calls _smoke_embedder
    # at line ~733) hits the cache, so we don't claim a download there.
    # Cache path matches fastembed's `define_cache_dir()`:
    # FASTEMBED_CACHE_PATH env var > tempfile.gettempdir()/fastembed_cache
    # (NOT ~/.cache/fastembed — fastembed never writes there by default).
    if embedder["key"] == "fastembed":
        _fastembed_cache = Path(
            os.getenv("FASTEMBED_CACHE_PATH")
            or os.path.join(tempfile.gettempdir(), "fastembed_cache")
        )
        # OSError-safe: permission denied, race, etc. → assume not cached
        # so we print the lead-in (better to over-explain than silent pause).
        try:
            _cached = _fastembed_cache.exists() and any(_fastembed_cache.iterdir())
        except OSError:
            _cached = False
        if not _cached:
            print("  Downloading fastembed model from HuggingFace (~67 MB, one-time)…")
    ok_emb, msg_emb = _smoke_embedder(embedder)
    print(f"  Embedder ({embedder['key']}): {'✓' if ok_emb else '✗'}  {msg_emb}")
    if pdf["key"] == "playwright":
        ok_pdf, msg_pdf = _smoke_pdf()
        print(f"  PDF (playwright):    {'✓' if ok_pdf else '✗'}  {msg_pdf}")
    else:
        ok_pdf = True
        print("  PDF:                 — skipped (HTML-only output)")

    # ── Write API keys atomically ────────────────────────────────────
    if api_key_updates:
        try:
            from linkright.keys.env_writer import write_keys
            write_keys(api_key_updates)
            print(f"  ✓  API keys → ~/.linkright/.env")
        except Exception as e:
            print(f"  ✗  Failed to write API keys: {e}")
            failures.append("api-key write")

    # ── Write config (existing/old_mode/migrate detected earlier in flow) ──
    update_dict = {
        "user_id": existing.get("user_id", "local"),
        "embedder_tier": embedder["key"],
        "render_pdf": pdf["key"] == "playwright",
        "schema_version": 2,
    }
    # Only write default_llm_mode if not preserving user's choice to keep agent mode
    if not (old_mode == "agent" and not migrate):
        update_dict["default_llm_mode"] = "direct"
    existing.update(update_dict)
    cfg_path.write_text(yaml.safe_dump(existing, sort_keys=False))
    print()
    print(f"Saved config →  {cfg_path}")

    # ── Final report ────────────────────────────────────────────────
    print()
    if failures or not ok_groq or not ok_emb or not ok_pdf:
        print("⚠️  Setup completed with warnings.")
        if not ok_groq:
            if "format invalid" in msg_groq:
                print("   • Groq key format invalid — re-run `linkright setup` with a valid gsk_... key.")
            else:
                print(f"   • Groq smoke test failed ({msg_groq}). Key is saved — try `linkright setup --check` once network is available.")
        if not ok_emb:
            print(f"   • Embedder `{embedder['key']}` smoke failed.")
        if not ok_pdf:
            print("   • PDF render not ready — try `python -m playwright install chromium`")
        print()
        print("Once those are fixed, you can run resumes. Smoke check anytime with:")
        print("   linkright setup --check")
        return 2

    print("✅  Setup complete.")
    print()
    print("Recommended next step (one-time, ~30s):")
    print("   linkright profile create")
    print("   → caches your resume so every tailor run is 30-60s faster")
    print()
    print("Then tailor for any job:")
    print("   linkright tailor -j path/to/jd.md")
    print("   (profile cache means -r is optional after first setup)")
    print()
    print("To re-run the wizard later:  linkright setup")
    print("To check current setup:      linkright setup --check")
    print("To manage API keys:          linkright keys")
    return 0


def run_check() -> int:
    """Non-interactive smoke check of current config — `linkright setup --check`."""
    cfg_path = Path.home() / ".linkright" / "config.yaml"
    if not cfg_path.exists():
        print("No config found. Run `linkright setup` first.")
        return 1
    cfg = yaml.safe_load(cfg_path.read_text()) or {}

    # S1.4: load managed .env FIRST — same source the pipeline reads at runtime.
    # os.environ alone is a false-negative: keys stored in ~/.linkright/.env are
    # not exported to the shell, so the check showed "✗ not set" even though the
    # pipeline worked fine.
    try:
        from linkright.keys.env_writer import read_all_managed
        _managed = read_all_managed()
    except ImportError:
        _managed = {}

    # Groq key: prefer shell env (user-exported) then managed .env file.
    groq_key = os.environ.get("GROQ_API_KEY") or _managed.get("GROQ_API_KEY", "")
    masked = (groq_key[:6] + "…" + groq_key[-4:]) if len(groq_key) > 12 else "(not set)"

    # Warn if user is still on legacy agent mode (v0.3.0 default)
    if cfg.get("default_llm_mode") == "agent":
        print()
        print("⚠ You are on agent mode (legacy from 0.3.0).")
        print("  v0.4.0 default is direct mode (Groq BYOK — free 14,400 req/day).")
        print("  Re-run `linkright setup` to migrate.")
        print()

    print(f"Config:  {cfg_path}")
    print(f"  LLM mode:  {cfg.get('default_llm_mode', '(unset)')} (Groq key: {masked})")
    print(f"  Embedder:  {cfg.get('embedder_tier', '(unset)')}")
    print(f"  PDF:       {'playwright' if cfg.get('render_pdf') else 'skip'}")
    print()
    print("Smoke checks:")

    # Groq key
    if groq_key:
        ok, msg = _smoke_groq_key(groq_key)
        print(f"  Groq key:  {'✓' if ok else '✗'}  {msg}")
    else:
        print("  Groq key:  ✗  not set — run `linkright keys add groq`")

    # Embedder
    emb_key = cfg.get("embedder_tier")
    emb_opt = next((o for o in EMBEDDER_OPTIONS if o["key"] == emb_key), None)
    if emb_opt:
        ok, msg = _smoke_embedder(emb_opt)
        print(f"  Embedder:  {'✓' if ok else '✗'}  {msg}")

    # PDF
    if cfg.get("render_pdf"):
        ok, msg = _smoke_pdf()
        print(f"  PDF:       {'✓' if ok else '✗'}  {msg}")

    # Multi-key status (reuse _managed — avoids second .env read)
    try:
        from linkright.keys.catalogue import PROVIDERS, resilience_score
        total = sum(1 for p in PROVIDERS for v in p.all_env_vars if _managed.get(v))
        pcount = sum(1 for p in PROVIDERS if any(_managed.get(v) for v in p.all_env_vars))
        if total:
            score = resilience_score(total, pcount)
            print(f"  API keys:  ✓  {_plural(total, 'key')} across {_plural(pcount, 'provider')} — {score}")
        else:
            print("  API keys:  ✗  none configured — run `linkright keys add groq`")
    except ImportError:
        pass

    return 0
