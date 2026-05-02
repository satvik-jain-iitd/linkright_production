"""Pydantic models for career_signals.yaml input."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Achievement(BaseModel):
    raw: str = Field(..., min_length=1, description="Raw bullet text")
    fit_tags: list[str] = Field(default_factory=list, description="Skill/domain tags")
    signal_strength: Optional[float] = Field(default=None, ge=0, le=10)


class SignalContext(BaseModel):
    team_size: Optional[int] = None
    scope: Optional[str] = None  # global|national|regional|local
    budget: Optional[float] = None
    tech_stack: list[str] = Field(default_factory=list)


class Signal(BaseModel):
    id: str = Field(..., description="Signal ID, e.g. sig-001")
    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    tenure: Optional[str] = None
    signal_type: str = Field(default="job", description="job|internship|freelance|project|venture|research|open-source")
    narrative: Optional[str] = None
    achievements: list[Achievement] = Field(default_factory=list)
    context: Optional[SignalContext] = None


class Education(BaseModel):
    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None


class VoluntaryWork(BaseModel):
    org: str
    role: Optional[str] = None
    tenure: Optional[str] = None
    description: str


class Project(BaseModel):
    """v0.1.1: optional user-side project entry for Pillar 1 Projects section."""
    name: str
    description: Optional[str] = None
    year: Optional[str] = None
    url: Optional[str] = None


class Certification(BaseModel):
    """v0.1.1: optional user-side certification entry for Pillar 1 Certifications section."""
    name: str
    issuer: Optional[str] = None
    year: Optional[str] = None
    url: Optional[str] = None


class StaticSection(BaseModel):
    role_title: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    education: Optional[Education] = None
    achievements: list[str] = Field(default_factory=list)
    voluntary_work: list[VoluntaryWork] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)


class Metadata(BaseModel):
    user: str = Field(..., min_length=1, description="Full name")
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    tagline: Optional[str] = None
    summary: Optional[str] = None
    profession: str = Field(default="product-manager")
    region: Optional[str] = None
    yoe_override: Optional[int] = None
    anchor_signals: list[str] = Field(default_factory=list)


class CareerSignals(BaseModel):
    metadata: Metadata
    static: Optional[StaticSection] = None
    signals: list[Signal] = Field(..., min_length=1)
