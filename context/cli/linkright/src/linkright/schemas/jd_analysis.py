"""Pydantic models for JD Parser output."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class JDKeyword(BaseModel):
    keyword: str
    category: str = Field(description="skill|tool|action|domain|certification")
    priority: str = Field(default="P1", description="P0 (must-have), P1 (should-have), P2 (nice-to-have)")


class BrandColors(BaseModel):
    primary: Optional[str] = None
    secondary: Optional[str] = None
    tertiary: Optional[str] = None
    quaternary: Optional[str] = None


class JDAnalysis(BaseModel):
    company_name: str
    role_title: str
    career_level: str = Field(description="fresher|entry|mid|senior|executive")
    strategy: str = Field(description="METRIC_BOMBARDMENT|SKILL_MATCHING|LEADERSHIP_NARRATIVE|TRANSFORMATION_STORY|BALANCED")
    keywords: list[JDKeyword]
    brand_colors: Optional[BrandColors] = None
    requirements_p0: list[str] = Field(default_factory=list, description="Must-have requirements")
    requirements_p1: list[str] = Field(default_factory=list, description="Should-have requirements")
    requirements_p2: list[str] = Field(default_factory=list, description="Nice-to-have requirements")
    summary: Optional[str] = Field(default=None, description="Brief role summary for context")
