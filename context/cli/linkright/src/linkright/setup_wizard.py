"""Interactive setup wizard — `linkright setup`.

Goal: zero-jargon onboarding for a new user. Three core decisions:

  1. Groq API key  (powers the 16-step resume pipeline — free at console.groq.com)
  2. Embedder tier (fastembed / sentence-transformers / Oracle)
  3. PDF render    (Playwright / skip)

After choices, we:
  - Verify the Groq key with a live API call
  - Install any missing pip packages silently
  - Run a smoke check on each picked tier (catches misconfig early)
  - Write picks to ~/.linkright/config.yaml and Groq key to ~/.linkright/.env
  - Print a 3-line "you're ready" summary with the exact next command

The user never sees pip output, Python tracebacks, or model download progress
unless something fails. That's the point of the wizard — abstraction over
ten minutes of manual setup steps.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
import questionary
import yaml


# ─────────────────────────────────────────────────────────────────────────
# Choice catalogues — single source of truth. Add to these dicts to expose
# new options to the wizard; no other code change needed.
# ─────────────────────────────────────────────────────────────────────────

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

def _format_choice(opt: dict) -> str:
    """Add a (recommended) badge to the label if marked."""
    if opt.get("recommended"):
        return f"⭐ {opt['label']}"
    return f"   {opt['label']}"


def _pick(question: str, options: list[dict], *, default_recommended: bool = True) -> dict:
    """Single-select prompt; returns the chosen option dict."""
    default = next((o for o in options if o.get("recommended")), options[0]) if default_recommended else options[0]
    choice_label = questionary.select(
        question,
        choices=[_format_choice(o) for o in options],
        default=_format_choice(default),
        instruction="(↑/↓ to navigate, enter to confirm)",
    ).ask()
    if choice_label is None:
        # User pressed Ctrl-C
        sys.exit(1)
    for o in options:
        if _format_choice(o) == choice_label:
            return o
    return default


def _check_bin(name: str) -> bool:
    return shutil.which(name) is not None


def _try_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def _pip_install(package: str) -> bool:
    """Install a pip package quietly. Returns True on success."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "--quiet"],
            capture_output=True, text=True, timeout=600,
        )
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
    """Write/update a single key in ~/.linkright/.env (chmod 600, in-place update)."""
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
            return True, "Groq API key valid ✓"
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
# Wizard entry
# ─────────────────────────────────────────────────────────────────────────

def run_wizard() -> int:
    """Returns shell exit code (0 OK, 1 user-cancel, 2 install/smoke fail)."""
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║   LinkRight setup — 3 quick choices                ║")
    print("╚════════════════════════════════════════════════════╝")
    print()
    print("First: a free Groq API key powers the resume pipeline.")
    print("Then: embedder + PDF renderer choices (⭐ = recommended).")
    print()

    # ── Decision 1: Groq API key ───────────────────────────────────
    print("1/3 — Groq API key (powers the 16-step resume pipeline)")
    print()
    groq_key, ok_groq, msg_groq = _ask_groq_key()

    # ── Decision 2: Embedder ───────────────────────────────────────
    print()
    embedder = _pick("2/3 — Which embedder?", EMBEDDER_OPTIONS)

    # ── Decision 3: PDF render ─────────────────────────────────────
    pdf = _pick("3/3 — Render PDFs from generated resumes?", PDF_OPTIONS)

    print()
    print("──────────────────────────────────────────────────────")
    print(f"Picks  →  LLM: direct (Groq)  •  embedder: {embedder['key']}  •  PDF: {pdf['key']}")
    print("──────────────────────────────────────────────────────")
    print()

    # ── Install missing pieces ─────────────────────────────────────
    print("Installing missing pieces (pip, models, browsers)…")
    failures: list[str] = []

    # Embedder pip
    if embedder.get("pip"):
        if embedder.get("import_check") and not _try_import(embedder["import_check"]):
            print(f"  ⬇  pip install {embedder['pip']}  …")
            if not _pip_install(embedder["pip"]):
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
    print(f"  Groq API key:        {'✓' if ok_groq else '✗'}  {msg_groq}")
    ok_emb, msg_emb = _smoke_embedder(embedder)
    print(f"  Embedder ({embedder['key']}): {'✓' if ok_emb else '✗'}  {msg_emb}")
    if pdf["key"] == "playwright":
        ok_pdf, msg_pdf = _smoke_pdf()
        print(f"  PDF (playwright):    {'✓' if ok_pdf else '✗'}  {msg_pdf}")
    else:
        ok_pdf = True
        print("  PDF:                 — skipped (HTML-only output)")

    # ── Write config ────────────────────────────────────────────────
    cfg_path = Path.home() / ".linkright" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if cfg_path.exists():
        try:
            existing = yaml.safe_load(cfg_path.read_text()) or {}
        except Exception:
            existing = {}
    existing.update({
        "user_id": existing.get("user_id", "local"),
        "default_llm_mode": "direct",
        "embedder_tier": embedder["key"],
        "render_pdf": pdf["key"] == "playwright",
        "schema_version": 2,
    })
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

    print("✅  Setup complete. Try this:")
    print()
    print("   linkright resume tailor -r path/to/resume.pdf -j path/to/jd.md")
    print()
    print("To re-run the wizard later:  linkright setup")
    print("To check current setup:      linkright setup --check")
    return 0


def run_check() -> int:
    """Non-interactive smoke check of current config — `linkright setup --check`."""
    cfg_path = Path.home() / ".linkright" / "config.yaml"
    if not cfg_path.exists():
        print("No config found. Run `linkright setup` first.")
        return 1
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    groq_key = os.environ.get("GROQ_API_KEY", "")
    masked = (groq_key[:6] + "…" + groq_key[-4:]) if len(groq_key) > 12 else "(not set)"
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
        print("  Groq key:  ✗  not set — run `linkright setup` to configure")

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
    return 0
