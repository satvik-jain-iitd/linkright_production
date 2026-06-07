"""Local-model candidate generator for the width optimizer.

Produces rewrite candidates from the local gemma3:1b on the Oracle VPS via
oracle_rewrite (/lifeos/rewrite). One call returns up to N variants near the
target width; the optimizer then measures, gates, and picks. The model never
decides width, it only proposes language. Numbers and banned words are caught
downstream by the optimizer's metric guard and content gate, so a weak 1b is
safe here.

Returns an ``llm_fn(html, measure_result) -> list[str]`` to inject into
optimize_bullet. On any Oracle failure it returns an empty list, so the optimizer
falls back to rules plus accept-relaxed, fully local, no cloud.
"""
from __future__ import annotations

from typing import Callable

_BANNED = "utilize, leverage, ensure, robust, scalable, spearhead, champion, delve"

_SYSTEM = (
    "You rewrite ONE resume bullet to hit a target line width. "
    "Keep the exact meaning. Keep every number exactly as given, do not add or change a number. "
    "Keep the <b> tags around metrics. Start with a strong past-tense action verb. "
    f"Never use these words: {_BANNED}. "
    "Return up to 3 rewrites, one per line, nothing else, no numbering, no commentary."
)


def make_oracle_llm_fn(
    *,
    temperature: float = 0.3,
    timeout_s: float = 8.0,
    n: int = 3,
) -> Callable[[str, object], list[str]]:
    """Build an llm_fn that asks the local model for width-targeted rewrites."""
    from linkright.llm.oracle import oracle_rewrite, OracleUnavailable

    def llm_fn(html: str, m) -> list[str]:
        direction = "shorter" if getattr(m, "status", "") == "OVERFLOW" else "longer"
        pct = round(getattr(m, "fill_percentage", 0.0))
        user = (
            f"This bullet is at {pct}% of the line. Make it {direction} so it lands at 95 to 100%.\n"
            f"Bullet: {html}\n"
            "Return up to 3 rewrites, one per line, each with the same numbers and <b> tags."
        )
        try:
            resp = oracle_rewrite(user=user, system=_SYSTEM,
                                  temperature=temperature, timeout_s=timeout_s)
        except OracleUnavailable:
            return []
        out: list[str] = []
        for ln in (resp.text or "").splitlines():
            ln = ln.strip().lstrip("-*0123456789. \t").strip()
            if len(ln) > 10 and ln not in out:
                out.append(ln)
        return out[:n]

    return llm_fn
