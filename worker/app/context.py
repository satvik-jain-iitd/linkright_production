"""PipelineContext — per-request scoped state.

Replaces the module-level SERVER_STATE from the MCP server.
Each resume job gets its own context, so concurrent jobs don't collide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """All mutable state for a single resume generation run."""

    job_id: str
    user_id: str
    jd_text: str
    career_text: str
    model_provider: str
    model_id: str
    api_key: str
    template_id: str = "cv-a4-standard"
    qa_answers: list[dict] = field(default_factory=list)  # [{question, answer}]
    override_theme_colors: dict | None = None  # pre-confirmed brand colors from wizard step

    # Populated by tools during the pipeline
    template_config: dict | None = None
    used_verbs: set = field(default_factory=set)
    sections: list[str] = field(default_factory=list)
    line_log: list[dict] = field(default_factory=list)
    career_level: str | None = None
    strategy: str | None = None
    bullet_scores: list[dict] = field(default_factory=list)
    jd_keywords: list[str] = field(default_factory=list)
    theme_colors: dict | None = None

    # Inter-phase scratch data (set by orchestrator, consumed across phases)
    _parsed: dict = field(default_factory=dict)          # Phase 1 LLM output
    _section_order: list[str] = field(default_factory=list)
    _bullet_budget: dict = field(default_factory=dict)
    _page_fit: dict = field(default_factory=dict)
    _section_specs: list = field(default_factory=list)    # list[SectionSpec]
    _raw_bullets: list[dict] = field(default_factory=list)
    _optimized_bullets: list[dict] = field(default_factory=list)
    _relevant_chunks: list[str] = field(default_factory=list)  # from pgvector/FTS
    _company_chunks: dict[int, list[str]] = field(default_factory=dict)  # per-company QMD results
    _professional_summary: str | None = None                      # Phase 3.5A professional summary text
    _verbose_bullets: list[dict] = field(default_factory=list)  # Phase 4a output (200-400 char paragraphs)
    _ranked_verbose_bullets: list[dict] = field(default_factory=list)  # Phase 4b ranked by BRS
    _nuggets: list = field(default_factory=list)              # Phase 0 extracted Nugget objects
    _nugget_results: list = field(default_factory=list)      # Phase 2.5 NuggetResult objects from hybrid_retrieve
    _llm_log: list[dict] = field(default_factory=list)       # per-call token/timing log
    _phase_timings: dict[str, int] = field(default_factory=dict)  # phase_N → ms

    # Progressive rendering
    draft_html: str | None = None  # intermediate HTML, updated at each visual phase

    # Pipeline progress
    current_phase: int = 0
    phase_message: str = ""

    # Multi-key management
    key_manager: Any | None = None  # Optional KeyManager instance

    # Output
    output_html: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
