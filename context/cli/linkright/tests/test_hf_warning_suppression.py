"""Tests for S1.7 — HuggingFace Hub / tokenizers warnings must not leak.

Root cause: huggingface_hub emits WARNING-level log messages during model
loading, and tqdm progress bars during download. Both surface in the user's
terminal and look like errors.

Fix: linkright/__init__.py sets HF_HUB_DISABLE_PROGRESS_BARS + TOKENIZERS_PARALLELISM
env vars (via setdefault — preserves user overrides) and raises the log level
of noisy third-party loggers to ERROR before any lazy import can trigger them.

AC1: HF_HUB_DISABLE_PROGRESS_BARS set to "1" after import
AC2: TOKENIZERS_PARALLELISM set to "false" after import
AC3: huggingface_hub logger level is ERROR or higher
AC4: tokenizers logger level is ERROR or higher
AC5: fastembed logger level is ERROR or higher
AC6: user override respected — setdefault does not clobber existing value
AC7: _noisy loop variable does not leak into module namespace
"""
from __future__ import annotations

import importlib
import logging
import os
import sys


def _fresh_import():
    """Re-import linkright after evicting it from sys.modules."""
    for key in list(sys.modules):
        if key == "linkright" or key.startswith("linkright."):
            del sys.modules[key]
    import linkright  # noqa: F401
    return linkright


# ── AC1: progress-bar env var set ────────────────────────────────────────────

def test_hf_hub_progress_bars_disabled():
    """HF_HUB_DISABLE_PROGRESS_BARS must be '1' after linkright import."""
    _fresh_import()
    assert os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS") == "1"


# ── AC2: tokenizers parallelism env var set ───────────────────────────────────

def test_tokenizers_parallelism_disabled():
    """TOKENIZERS_PARALLELISM must be 'false' after linkright import."""
    _fresh_import()
    assert os.environ.get("TOKENIZERS_PARALLELISM") == "false"


# ── AC3: huggingface_hub logger silenced ─────────────────────────────────────

def test_huggingface_hub_logger_silenced():
    """huggingface_hub logger level must be ERROR or higher."""
    _fresh_import()
    lvl = logging.getLogger("huggingface_hub").level
    assert lvl >= logging.ERROR, (
        f"huggingface_hub logger level {lvl} < ERROR ({logging.ERROR}) — "
        "HF warnings will leak to terminal"
    )


# ── AC4: tokenizers logger silenced ──────────────────────────────────────────

def test_tokenizers_logger_silenced():
    """tokenizers logger level must be ERROR or higher."""
    _fresh_import()
    lvl = logging.getLogger("tokenizers").level
    assert lvl >= logging.ERROR, (
        f"tokenizers logger level {lvl} < ERROR — parallelism warnings will leak"
    )


# ── AC5: fastembed logger silenced ────────────────────────────────────────────

def test_fastembed_logger_silenced():
    """fastembed logger level must be ERROR or higher."""
    _fresh_import()
    lvl = logging.getLogger("fastembed").level
    assert lvl >= logging.ERROR, (
        f"fastembed logger level {lvl} < ERROR — download logs will leak"
    )


# ── AC6: user override respected ─────────────────────────────────────────────

def test_user_override_not_clobbered():
    """setdefault must not clobber a pre-existing HF_HUB_DISABLE_PROGRESS_BARS."""
    saved = os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)
    try:
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
        _fresh_import()
        assert os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS") == "0", (
            "setdefault clobbered user-set HF_HUB_DISABLE_PROGRESS_BARS=0"
        )
    finally:
        if saved is not None:
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = saved
        else:
            os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)


# ── AC7: _noisy loop variable does not leak ───────────────────────────────────

def test_noisy_loop_variable_not_leaked():
    """_noisy must not appear in the linkright module's public namespace."""
    lr = _fresh_import()
    assert not hasattr(lr, "_noisy"), (
        "_noisy loop variable leaked into linkright module namespace"
    )
