"""Local-model candidate generator for the width optimizer.

Produces rewrite candidates from a local model on the Oracle VPS via
oracle_rewrite (/lifeos/rewrite). The backend default is LFM2 (Liquid AI's small,
CPU-efficient model); pass ``model`` to route to a different allow-listed local
model, which is how we benchmark LFM variants against each other. One call
returns up to N variants near the target width; the optimizer then measures,
gates, and picks. The model never decides width, it only proposes language.
Numbers and banned words are caught downstream by the optimizer's metric guard
and content gate, so a small model is safe here.

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
    model: "str | None" = None,
) -> Callable[[str, object], list[str]]:
    """Build an llm_fn that asks the local model for width-targeted rewrites.

    ``model`` is None for the backend default (LFM2), or an allow-listed model
    tag to benchmark a specific variant.
    """
    from linkright.llm.oracle import oracle_rewrite, OracleUnavailable

    def llm_fn(html: str, m) -> list[str]:
        status = getattr(m, "status", "")
        pct = round(getattr(m, "fill_percentage", 0.0))
        if status == "OVERFLOW":
            ask = (
                f"This bullet is too long, at {pct}% of the line. Shorten it to land at "
                "95 to 100%. Cut filler and tighten the phrasing. Keep every number and "
                "every <b> tag exactly as they are."
            )
        else:
            ask = (
                f"This bullet is too short, at {pct}% of the line. Lengthen it so it lands "
                "slightly OVER the line, in the 100 to 110% range, by adding the method, "
                "the context, or the scope in words. Writing a little long is good, it will "
                "be tightened afterward. Do NOT add any number or metric that is not already "
                "in the bullet. Keep the existing numbers and <b> tags exactly as they are."
            )
        user = (
            f"{ask}\n"
            f"Bullet: {html}\n"
            "Return up to 3 rewrites, one per line, no commentary."
        )
        try:
            resp = oracle_rewrite(user=user, system=_SYSTEM,
                                  temperature=temperature, timeout_s=timeout_s,
                                  model=model)
        except OracleUnavailable:
            return []
        out: list[str] = []
        for ln in (resp.text or "").splitlines():
            ln = ln.strip().lstrip("-*0123456789. \t").strip()
            if len(ln) > 10 and ln not in out:
                out.append(ln)
        return out[:n]

    return llm_fn
