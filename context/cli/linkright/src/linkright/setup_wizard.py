"""Interactive setup wizard — `linkright setup`.

Goal: zero-jargon onboarding for a new user. Three core decisions, each as a
single-keystroke arrow-select (questionary):

  1. LLM tool (claude / opencode / gemini / ollama / custom)
  2. Embedder tier (fastembed / sentence-transformers / Oracle / advanced)
  3. PDF render (Playwright / skip)

For each decision, we mark ONE option as `(recommended)` based on the
quality + cost balance Satvik wants users to default to. Recommendations
update as the ecosystem changes — rev this file, not user docs.

After choices, we:
  - Install any missing pip packages silently
  - Run a smoke check on each picked tier (catches misconfig early)
  - Write picks to ~/.linkright/config.yaml
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
from typing import Optional

import questionary
import yaml


# ─────────────────────────────────────────────────────────────────────────
# Choice catalogues — single source of truth. Add to these dicts to expose
# new options to the wizard; no other code change needed.
# ─────────────────────────────────────────────────────────────────────────

LLM_OPTIONS = [
    {
        "key": "opencode",
        "label": "opencode  (free OSS, $0/run, recommended for first-time users)",
        "bin": "opencode",
        "install_hint": "https://github.com/sst/opencode  →  curl -fsSL https://opencode.ai/install | bash",
        "recommended": True,
    },
    {
        "key": "claude",
        "label": "claude  (premium quality, ~$1.20/run, uses your Claude Code subscription)",
        "bin": "claude",
        "install_hint": "https://docs.anthropic.com/en/docs/claude-code  →  brew install anthropic/claude/claude  (or via npm)",
        "recommended": False,
    },
    {
        "key": "gemini",
        "label": "gemini-cli  (free Google daily tier, $0 within quota)",
        "bin": "gemini",
        "install_hint": "https://github.com/google-gemini/gemini-cli  →  npm install -g @google/gemini-cli",
        "recommended": False,
    },
    {
        "key": "ollama",
        "label": "ollama  (fully local, $0, offline-capable, ~6 GB disk)",
        "bin": "ollama",
        "install_hint": "https://ollama.com  →  brew install ollama  (and pull a model: ollama pull llama3.1:8b)",
        "recommended": False,
    },
    {
        "key": "custom",
        "label": "custom  (define your own CLI in ~/.linkright/agents.yaml)",
        "bin": None,
        "install_hint": "Edit ~/.linkright/agents.yaml; see docs/agents-yaml.md for spec",
        "recommended": False,
    },
]

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

SKILL_OPTIONS = [
    {"key": "product_manager", "label": "Product Manager  (recommended)", "recommended": True},
    {"key": "swe", "label": "Software Engineer", "recommended": False},
    {"key": "ds", "label": "Data Scientist / ML", "recommended": False},
    {"key": "designer", "label": "Designer", "recommended": False},
    {"key": "generic", "label": "Generic / mixed roles", "recommended": False},
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


def _smoke_llm(opt: dict) -> tuple[bool, str]:
    if opt["key"] == "custom":
        return True, "skipped (custom backend — verify manually)"
    if not opt.get("bin"):
        return False, "no bin defined"
    if not _check_bin(opt["bin"]):
        return False, f"`{opt['bin']}` not in PATH"
    return True, f"`{opt['bin']}` found"


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
    print("║   LinkRight setup — pick how you want to run       ║")
    print("╚════════════════════════════════════════════════════╝")
    print()
    print("3 quick choices. Defaults are ⭐ recommended for new users.")
    print()

    # ── Decision 1: LLM ────────────────────────────────────────────
    llm = _pick("1/3 — Which LLM tool would you like to use?", LLM_OPTIONS)

    # ── Decision 2: Embedder ───────────────────────────────────────
    embedder = _pick("2/3 — Which embedder?", EMBEDDER_OPTIONS)

    # ── Decision 3: PDF render ─────────────────────────────────────
    pdf = _pick("3/3 — Render PDFs from generated resumes?", PDF_OPTIONS)

    # ── Optional: skill mode ───────────────────────────────────────
    skill = _pick("Default skill mode (used unless overridden via --mode)?", SKILL_OPTIONS)

    print()
    print("──────────────────────────────────────────────────────")
    print(f"Picks  →  LLM: {llm['key']}  •  embedder: {embedder['key']}  •  PDF: {pdf['key']}  •  skill: {skill['key']}")
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
    ok_llm, msg_llm = _smoke_llm(llm)
    print(f"  LLM ({llm['key']}):       {'✓' if ok_llm else '✗'}  {msg_llm}")
    ok_emb, msg_emb = _smoke_embedder(embedder)
    print(f"  Embedder ({embedder['key']}): {'✓' if ok_emb else '✗'}  {msg_emb}")
    if pdf["key"] == "playwright":
        ok_pdf, msg_pdf = _smoke_pdf()
        print(f"  PDF (playwright):     {'✓' if ok_pdf else '✗'}  {msg_pdf}")
    else:
        ok_pdf = True
        print("  PDF:                  — skipped (HTML-only output)")

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
        "default_llm_mode": "agent",
        "default_skill_mode": skill["key"],
        "agent_backend": llm["key"],
        "embedder_tier": embedder["key"],
        "render_pdf": pdf["key"] == "playwright",
        "schema_version": 2,
    })
    cfg_path.write_text(yaml.safe_dump(existing, sort_keys=False))
    print()
    print(f"Saved config →  {cfg_path}")

    # ── Final report ────────────────────────────────────────────────
    print()
    if failures or not ok_llm or not ok_emb or not ok_pdf:
        print("⚠️  Setup completed with warnings.")
        if not ok_llm:
            print(f"   • LLM `{llm['key']}` not yet usable. Install: {llm.get('install_hint')}")
        if not ok_emb:
            print(f"   • Embedder `{embedder['key']}` smoke failed.")
        if not ok_pdf:
            print(f"   • PDF render not ready — try `python -m playwright install chromium`")
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
    print(f"Config:  {cfg_path}")
    print(f"  LLM:       {cfg.get('agent_backend', '(unset)')}")
    print(f"  Embedder:  {cfg.get('embedder_tier', '(unset)')}")
    print(f"  PDF:       {'playwright' if cfg.get('render_pdf') else 'skip'}")
    print(f"  Skill:     {cfg.get('default_skill_mode', '(unset)')}")
    print()
    print("Smoke checks:")

    # LLM
    llm_key = cfg.get("agent_backend")
    llm_opt = next((o for o in LLM_OPTIONS if o["key"] == llm_key), None)
    if llm_opt:
        ok, msg = _smoke_llm(llm_opt)
        print(f"  LLM:       {'✓' if ok else '✗'}  {msg}")

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
