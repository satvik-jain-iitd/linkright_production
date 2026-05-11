"""Append-only logbook helper for vision.md.

Every entry to vision.md MUST be prefixed with a fenced code block of the shape:

    ```text
    [<ISO timestamp UTC>] <step_name> — <phase>
    context: <one sentence — what we are doing and why>
    ```

This module is the ONLY writer to vision.md from the pipeline. It never
rewrites prior content; every call appends.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Optional

# Default: top-level vision.md (legacy). run_pipeline.py calls set_path() at
# startup to point this at the active run's vision.md inside runs/<run_id>/.
_VISION_PATH: Path = Path(__file__).resolve().parent.parent / "vision.md"


# 2026-05-01: friendly verbs per step for terminal progress emission. Mapped
# to step name prefix so retry/sub-phase variants share the same verb.
_STEP_VERBS: dict[str, str] = {
    "run_start": "🚀 Starting pipeline",
    "step_00":  "📄 Reading resume PDF",
    "step_01":  "🧩 Parsing resume structure",
    "step_02":  "✨ Extracting career achievements",
    "step_03":  "🧠 Indexing achievements semantically",
    "step_05":  "🎯 Embedding job requirements",
    "step_06":  "📊 Scoring role-fit by company",
    "step_07":  "🔍 Analyzing job description",
    "step_08":  "🤝 Matching achievements to JD requirements",
    "step_09":  "✍️  Drafting professional summary",
    "step_10":  "🖋  Writing bullet points",
    "step_11":  "🏆 Ranking bullets by impact",
    "step_12":  "✂️  Tightening bullets to fit",
    "step_13":  "📐 Tuning bullet widths",
    "step_14":  "🎨 Assembling final HTML",
    "step_15":  "🖨  Rendering PDF",
    "step_16":  "📈 Computing telemetry",
}


def _verb_for(step_name: str) -> str:
    """Return user-friendly verb for a step name (matches step_NN_* prefix)."""
    prefix = "_".join(step_name.split("_")[:2])  # "step_07"
    return _STEP_VERBS.get(prefix, "⚙️  Processing...")


def _emit_progress(step_name: str, phase: str, context: str) -> None:
    """Write a single-line progress message to stderr for live terminal feedback.

    Suppressed when LR_QUIET=1 set (for hypothesis-test subprocesses to keep
    output stream clean for parsers).
    """
    if os.environ.get("LR_QUIET"):
        return
    verb = _verb_for(step_name)
    if phase == "starting":
        sys.stderr.write(f"  → {verb}...\n")
        sys.stderr.flush()
    elif phase in ("eval", "pass"):
        sys.stderr.write(f"    ✓ {verb} — done\n")
        sys.stderr.flush()
    elif phase == "error":
        sys.stderr.write(f"    ✗ {verb} — fallback engaged\n")
        sys.stderr.flush()


def announce_loop(name: str, current: int, total: int, detail: str = "") -> None:
    """Announce entry into a loop iteration (fit_loop, retry, etc.)."""
    if os.environ.get("LR_QUIET"):
        return
    extra = f" — {detail}" if detail else ""
    sys.stderr.write(f"\n🔄 {name} iteration {current}/{total}{extra}\n")
    sys.stderr.flush()


def set_path(path: Path) -> None:
    """Redirect all logbook writes to a different vision.md file."""
    global _VISION_PATH
    _VISION_PATH = Path(path)


def _now_utc() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def append(
    step_name: str,
    phase: str,
    context: str,
    body: Optional[str] = None,
) -> None:
    """Append one entry to vision.md.

    Args:
        step_name: e.g. "step_00_ingest_pdf", "step_03_embed_nuggets".
        phase: one of "starting" | "result" | "eval" | "gap" | "error".
        context: one sentence describing what is happening RIGHT NOW.
        body: optional free-form markdown (LLM output summary, metrics, eval verdict).
    """
    ts = _now_utc()
    header_block = (
        f"\n```text\n"
        f"[{ts}] {step_name} — {phase}\n"
        f"context: {context}\n"
        f"```\n"
    )
    with _VISION_PATH.open("a", encoding="utf-8") as f:
        f.write(header_block)
        if body:
            f.write("\n")
            f.write(body.rstrip())
            f.write("\n")
    # 2026-05-01: emit friendly progress to stderr alongside vision.md write
    _emit_progress(step_name, phase, context)


def append_raw(text: str) -> None:
    """Append raw text (no header). Used for the opening plan transcription."""
    with _VISION_PATH.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
