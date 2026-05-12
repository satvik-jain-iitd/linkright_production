"""LinkRight MCP server — exposes resume pipeline tools to agent clients.

Ported from context/cli/sync/server.py (v2.0.0). Run as:

    linkright mcp serve

Spawned fresh per agent session (Claude Code / Cursor). No daemon, no cross-
session state. Module-level SERVER_STATE persists for the lifetime of this
subprocess only. When the agent session ends, the process exits.

Pillar 1 (Resume) tools are wired today. Pillars 2/3/4 register additional
tools on the same FastMCP instance in their respective `register_mcp()` hooks
(to be added in Phase 4B/C/D).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from ..mcp_sync.tools.parse_template import (
    resume_parse_template,
    ParseTemplateInput,
)
from ..mcp_sync.tools.measure_width import (
    resume_measure_width,
    MeasureWidthInput,
)
from ..mcp_sync.tools.validate_contrast import (
    resume_validate_contrast,
    ContrastInput,
)
from ..mcp_sync.tools.validate_page_fit import (
    resume_validate_page_fit,
    PageFitInput,
)
from ..mcp_sync.tools.suggest_synonyms import (
    resume_suggest_synonyms,
    SynonymInput,
)
from ..mcp_sync.tools.track_verbs import (
    resume_track_verbs,
    TrackVerbsInput,
    TrackVerbsState,
)
from ..mcp_sync.tools.assemble_html import (
    resume_assemble_html,
    AssembleInput,
)
from ..mcp_sync.tools.score_bullets import (
    resume_score_bullets,
    ScoreBulletsInput,
)


SERVER_STATE: dict = {
    "template_config": None,
    "used_verbs": set(),
    "sections": [],
    "line_log": [],
    "career_level": None,
    "strategy": None,
    "bullet_scores": [],
    "jd_keywords": [],
    "theme_colors": None,
}

_verb_state = TrackVerbsState(used_verbs=set())

mcp = FastMCP("linkright")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False))
async def resume_parse_template_tool(params: ParseTemplateInput) -> str:
    """Parse HTML template + compute line budgets. MUST be called first."""
    return await resume_parse_template(params, server_state=SERVER_STATE)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
async def resume_measure_width_tool(params: MeasureWidthInput) -> str:
    """Weighted CU width of text vs line budget. Returns PASS/TOO_SHORT/OVERFLOW."""
    template_config = SERVER_STATE.get("template_config")
    result = await resume_measure_width(params, template_config=template_config)
    try:
        output = json.loads(result)
        SERVER_STATE["line_log"].append({
            "text": output.get("rendered_text", ""),
            "line_type": params.line_type,
            "status": output.get("status", ""),
            "fill_percentage": output.get("fill_percentage", 0),
        })
    except (json.JSONDecodeError, KeyError):
        pass
    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
async def resume_validate_contrast_tool(params: ContrastInput) -> str:
    """WCAG 2.0 AA contrast check between two hex colors."""
    return await resume_validate_contrast(params)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
async def resume_validate_page_fit_tool(params: PageFitInput) -> str:
    """Vertical page-fit check + recommended section allocations."""
    template_config = SERVER_STATE.get("template_config")
    return await resume_validate_page_fit(params, template_config=template_config)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
async def resume_suggest_synonyms_tool(params: SynonymInput) -> str:
    """Synonym substitutions ranked by proximity to target width."""
    return await resume_suggest_synonyms(params)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
async def resume_track_verbs_tool(params: TrackVerbsInput) -> str:
    """Session-scoped action verb registry (check/register/list/reset)."""
    global _verb_state
    _verb_state.used_verbs = SERVER_STATE["used_verbs"]
    result = await resume_track_verbs(params, state=_verb_state)
    SERVER_STATE["used_verbs"] = _verb_state.used_verbs
    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
async def resume_assemble_html_tool(params: AssembleInput) -> str:
    """Final HTML assembly — inject colors, header, sections into template."""
    result = await resume_assemble_html(params)
    if hasattr(params, "theme_colors"):
        SERVER_STATE["theme_colors"] = params.theme_colors
    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
async def resume_score_bullets_tool(params: ScoreBulletsInput) -> str:
    """BRS scoring: keyword overlap, metric magnitude, recency, leadership, uniqueness."""
    result = await resume_score_bullets(params)
    try:
        output = json.loads(result)
        SERVER_STATE["bullet_scores"] = output.get("scored_bullets", [])
    except (json.JSONDecodeError, KeyError):
        pass
    return result


# ── High-level MCP tools (2026-05-01 — Route 2 / BMAD pattern) ─────────────
#
# Below tools wrap the full LinkRight CLI commands as single-call MCP tools.
# This lets MCP clients (Claude Code, Cursor, Gemini CLI, ChatGPT desktop, etc.)
# drive end-to-end resume tailoring without orchestrating 8 low-level tools
# manually. Each user's IDE provides the LLM under their existing subscription
# quota — LinkRight consumes $0 incremental.
#
# Pattern: subprocess invoke `linkright resume <command>` (already-installed
# CLI), parse output, return structured JSON to the MCP client.


class TailorResumeInput(BaseModel):
    """Tailor an existing resume to fit a target job description."""
    resume_path: str = Field(..., description="Absolute path to resume PDF")
    jd_path: str = Field(..., description="Absolute path to JD markdown file")
    deterministic: bool = Field(
        default=True,
        description="If True, pin temperature=0 across all LLM calls for reproducibility.",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Custom run identifier. Defaults to timestamp.",
    )


class ImproveResumeInput(BaseModel):
    """Refine an existing tailored resume to lift specific quality dimensions."""
    run_id: str = Field(..., description="Run ID from a previous tailor_resume call")
    target_dim: Optional[str] = Field(
        default=None,
        description="Scorecard dim to improve. Defaults to weakest. "
                    "Currently supports: width_hit_rate, keyword_coverage.",
    )


class ScoreResumeInput(BaseModel):
    """Score an existing tailored resume against the 16 scorecard dimensions."""
    run_id: str = Field(..., description="Run ID from a previous tailor_resume call")


def _latest_run_dir() -> Path:
    runs = Path.home() / ".linkright" / "runs"
    return max(
        (d for d in runs.iterdir() if d.is_dir() and not d.name.startswith("hyp_")),
        key=lambda p: p.stat().st_mtime,
    )


def _score_run_dir(run_dir: Path) -> dict:
    """Compute scorecard for a run dir. Returns flat dict for MCP response."""
    import sys as _sys
    harness_parent = Path(__file__).resolve().parents[3]
    if str(harness_parent) not in _sys.path:
        _sys.path.insert(0, str(harness_parent))
    from harness.resume.scorecard_context import build_context
    from linkright.resume.scorecard import ResumeScorecard
    ctx = build_context(run_dir)
    sc = ResumeScorecard(run_id=run_dir.name)
    sc.score(ctx)
    weakest = min(sc.results, key=lambda r: r.score)
    return {
        "overall_score": round(sc.overall_score, 1),
        "overall_grade": sc.overall_grade,
        "weakest_dim": weakest.name,
        "weakest_dim_score": round(weakest.score, 1),
        "per_dim": {r.name: round(r.score, 1) for r in sc.results},
    }


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True,
))
async def linkright_tailor_resume(params: TailorResumeInput) -> str:
    """Tailor a resume to a job description — full LinkRight pipeline.

    Runs 16-step pipeline: parse resume → extract nuggets → embed → analyze JD
    → match → write bullets → condense → tune width → render HTML+PDF.
    Wall time ~2-3 min. Cost ~$0 with free API keys configured.

    Returns JSON with run_id, paths to HTML+PDF outputs, and scorecard summary.
    """
    cmd = ["linkright", "resume", "tailor",
           "-r", params.resume_path, "-j", params.jd_path]
    if params.deterministic:
        cmd.append("--deterministic")
    if params.run_id:
        cmd.extend(["--run-id", params.run_id])

    _env = {**os.environ, "LR_NO_PAUSE": "1"}
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=_env)
    if proc.returncode != 0:
        return json.dumps({"error": "tailor failed",
                           "stderr": proc.stderr[-1500:],
                           "stdout_tail": proc.stdout[-500:]})

    run_dir = (Path.home() / ".linkright" / "runs" / params.run_id) if params.run_id else _latest_run_dir()
    if not run_dir.exists():
        return json.dumps({"error": f"run dir not created: {run_dir}"})

    score_data = _score_run_dir(run_dir)
    return json.dumps({
        "run_id": run_dir.name,
        "html_path": str(run_dir / "artifacts" / "14_final_resume.html"),
        "pdf_path": str(run_dir / "artifacts" / "15_final_resume.pdf"),
        "scorecard": score_data,
    })


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True,
))
async def linkright_improve_resume(params: ImproveResumeInput) -> str:
    """Refine an existing tailored resume — does NOT regenerate from scratch.

    Identifies the weakest scorecard dim (or specified target_dim), runs targeted
    LLM refinement to fix that deficiency, re-renders HTML+PDF, returns delta.
    """
    cmd = ["linkright", "resume", "improve", "--run-id", params.run_id]
    if params.target_dim:
        cmd.extend(["--target-dim", params.target_dim])

    _env = {**os.environ, "LR_NO_PAUSE": "1"}
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=_env)
    if proc.returncode != 0:
        return json.dumps({"error": "improve failed",
                           "stderr": proc.stderr[-1500:]})

    run_dir = Path.home() / ".linkright" / "runs" / params.run_id
    return json.dumps({
        "run_id": params.run_id,
        "scorecard": _score_run_dir(run_dir),
        "stderr_tail": proc.stderr[-500:],
    })


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
))
async def linkright_score_resume(params: ScoreResumeInput) -> str:
    """Score an existing tailored resume against the 16 scorecard dimensions.

    Reads run dir artifacts, computes per-dim scores + overall grade.
    Read-only — no LLM calls, no file mutations.
    """
    run_dir = Path.home() / ".linkright" / "runs" / params.run_id
    if not run_dir.exists():
        return json.dumps({"error": f"run not found: {params.run_id}"})
    return json.dumps(_score_run_dir(run_dir))


def serve() -> None:
    """Entry point for `linkright mcp serve`."""
    mcp.run()


if __name__ == "__main__":
    serve()
