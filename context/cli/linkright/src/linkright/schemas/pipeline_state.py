"""Pydantic models for pipeline intermediate state."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class WrittenBullet(BaseModel):
    signal_id: str = Field(description="Links to career_signals.yaml signal")
    achievement_index: int = Field(default=0, description="Index in signal's achievements list")
    section_type: str = Field(default="experience", description="experience|education|awards|projects")
    group: str = Field(default="", description="Bullet group name for visual clustering within a role")
    html_text: str = Field(description="Final HTML-formatted XYZ bullet, ready for template")
    plain_text: str = Field(description="Plain text version for width measurement")
    width_total: float = Field(description="Weighted width in character-units")
    fill_percentage: float = Field(description="Fill % against budget")
    width_status: str = Field(description="PASS|TOO_SHORT|OVERFLOW")
    action_verb: str = Field(description="Leading action verb, for dedup tracking")


class QualityReport(BaseModel):
    overall_grade: str = Field(description="A|B|C|D|F")
    keyword_coverage: float = Field(description="% of P0/P1 keywords in resume")
    width_fill_avg: float = Field(description="Average fill % across all bullets")
    width_fill_min: float = Field(description="Worst bullet fill %")
    verb_duplicates: list[str] = Field(default_factory=list)
    page_fits: bool = Field(default=True)
    contrast_passes: bool = Field(default=True)
    ats_issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class PipelineState(BaseModel):
    step: str = Field(description="Current pipeline step name")
    career_signals_path: Optional[str] = None
    jd_path: Optional[str] = None
    jd_analysis: Optional[dict] = None
    scored_bullets: Optional[dict] = None
    written_bullets: list[WrittenBullet] = Field(default_factory=list)
    html_output: Optional[str] = None
    quality_report: Optional[dict] = None
