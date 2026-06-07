"""$0-promise spend guard for paid LLM providers (audit fix W1).

LinkRight is free-by-default. OpenRouter is the only PAID provider in the
fallback cascade. This module enforces two things, failing CLOSED:

  1. Paid providers are OFF unless the user explicitly opts in with
     LR_ALLOW_PAID=1. Without it, ``ensure_paid_allowed`` raises and the
     cascade simply skips the paid tier — no surprise spend, ever. This is
     what makes the $0 promise hold at 100k users on their own keys.
  2. Even when opted in, a rolling monthly budget (LR_MONTHLY_BUDGET_CENTS,
     default 500 = $5) caps spend. Over budget → raise, skip the paid call.

State is a tiny JSON file at ``~/.linkright/cache/budget.json`` keyed by month.
Single-user CLI, so no locking needed; bookkeeping failures never break a call.
"""
from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path
from typing import Optional


class BudgetError(Exception):
    """Raised when a paid call is disallowed (opt-out) or over the monthly budget."""


# Per-model rates (USD cents per 1M tokens), (prompt, completion). The cascade's
# default OpenRouter model is llama-3.3-70b ($0.07/$0.25 per 1M). An UNKNOWN model
# falls back to a deliberately HIGH estimate so the budget cap trips early rather
# than late — a cost guard must fail-safe by over-counting, never under-counting.
_DEFAULT_OPENROUTER_RATE = (7.0, 25.0)
_UNKNOWN_PAID_RATE = (300.0, 1500.0)  # ~frontier-class; intentionally pessimistic


def _rate_for(provider: str, model: Optional[str]) -> tuple[float, float]:
    if provider != "openrouter":
        return (0.0, 0.0)
    if not model or "llama-3.3-70b" in model.lower():
        return _DEFAULT_OPENROUTER_RATE
    return _UNKNOWN_PAID_RATE  # unknown/overridden model → assume expensive


def _home() -> Path:
    return Path(os.environ.get("LINKRIGHT_HOME", str(Path.home() / ".linkright")))


def _budget_path() -> Path:
    return _home() / "cache" / "budget.json"


def _month_key(now: Optional[float] = None) -> str:
    return time.strftime("%Y-%m", time.gmtime(now if now is not None else time.time()))


def _load() -> dict:
    try:
        return json.loads(_budget_path().read_text())
    except Exception:
        return {}


def _spent_this_month() -> float:
    return float(_load().get(_month_key(), 0.0))


def paid_allowed() -> bool:
    """True only if the user explicitly enabled paid providers."""
    return os.environ.get("LR_ALLOW_PAID", "").strip().lower() in ("1", "true", "yes")


def _monthly_cap_cents() -> int:
    try:
        return int(os.environ.get("LR_MONTHLY_BUDGET_CENTS", "500"))
    except ValueError:
        return 500


def ensure_paid_allowed(provider: str) -> None:
    """Gate a paid provider call. Raises BudgetError if paid is off or over budget."""
    if not paid_allowed():
        raise BudgetError(
            f"{provider} is a PAID provider, disabled by default. "
            f"Set LR_ALLOW_PAID=1 to enable it (free providers are always tried first)."
        )
    cap = _monthly_cap_cents()
    spent = _spent_this_month()
    if spent >= cap:
        raise BudgetError(
            f"{provider} skipped: monthly paid budget reached "
            f"(${spent/100:.2f} / ${cap/100:.2f}). Raise LR_MONTHLY_BUDGET_CENTS to allow more."
        )


def estimate_cents(provider: str, model: Optional[str],
                   prompt_tokens: int, completion_tokens: int) -> float:
    p_rate, c_rate = _rate_for(provider, model)
    return (prompt_tokens * p_rate + completion_tokens * c_rate) / 1_000_000.0


@contextlib.contextmanager
def _locked(path: Path):
    """Best-effort exclusive lock via a sidecar lockfile (POSIX). No-op without fcntl."""
    try:
        import fcntl
    except ImportError:
        yield  # Windows / no fcntl → best-effort, no lock
        return
    f = open(path.with_suffix(".lock"), "w")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()


def record_spend(provider: str, model: Optional[str],
                 prompt_tokens: int, completion_tokens: int) -> None:
    """Add the estimated cost of a completed paid call to this month's tally.

    Uses an exclusive file lock so concurrent CLI processes (e.g. `linkright
    watch` alongside a normal command) don't clobber each other's totals.
    """
    cents = estimate_cents(provider, model, prompt_tokens, completion_tokens)
    if cents <= 0:
        return
    try:
        p = _budget_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with _locked(p):
            data = _load()
            mk = _month_key()
            data[mk] = round(float(data.get(mk, 0.0)) + cents, 4)
            p.write_text(json.dumps(data))
    except Exception:
        pass  # never break a successful call on a bookkeeping error
