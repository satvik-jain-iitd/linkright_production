"""Shared fixtures for LinkRight tests."""
from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from linkright.schemas.career_signals import CareerSignals
from linkright.schemas.jd_analysis import JDAnalysis, JDKeyword
from linkright.schemas.pipeline_state import WrittenBullet
from linkright.data.default_template import DEFAULT_TEMPLATE_CONFIG


@pytest.fixture
def template_config():
    return DEFAULT_TEMPLATE_CONFIG


@pytest.fixture
def sample_signals_path():
    return str(Path(__file__).parent.parent / "examples" / "sample_career_signals.yaml")


@pytest.fixture
def sample_jd_path():
    return str(Path(__file__).parent.parent / "examples" / "sample_jd.txt")


@pytest.fixture
def career_signals(sample_signals_path):
    with open(sample_signals_path) as f:
        data = yaml.safe_load(f)
    return CareerSignals(**data)


@pytest.fixture
def jd_text(sample_jd_path):
    with open(sample_jd_path) as f:
        return f.read()


@pytest.fixture
def sample_jd_analysis():
    return JDAnalysis(
        company_name="Attentive",
        role_title="Senior Product Manager",
        career_level="senior",
        strategy="BALANCED",
        keywords=[
            JDKeyword(keyword="AI/ML", category="skill", priority="P0"),
            JDKeyword(keyword="product strategy", category="skill", priority="P0"),
            JDKeyword(keyword="cross-functional", category="action", priority="P1"),
            JDKeyword(keyword="A/B testing", category="tool", priority="P1"),
            JDKeyword(keyword="SMS marketing", category="domain", priority="P0"),
        ],
        requirements_p0=["5+ years PM experience", "AI/ML product experience"],
        requirements_p1=["Mobile marketing experience"],
        requirements_p2=["Startup experience"],
        summary="Senior PM for AI-powered SMS marketing platform",
    )


@pytest.fixture
def sample_written_bullets():
    return [
        WrittenBullet(
            signal_id="cdl-amex",
            achievement_index=0,
            section_type="experience",
            html_text='Reduced bid turnaround by <b>40%</b> by building AI-powered measurement tool processing <b>1000+ properties/month</b>',
            plain_text="Reduced bid turnaround by 40% by building AI-powered measurement tool processing 1000+ properties/month",
            width_total=480.0,
            fill_percentage=95.0,
            width_status="PASS",
            action_verb="reduced",
        ),
        WrittenBullet(
            signal_id="cdl-amex",
            achievement_index=1,
            section_type="experience",
            html_text='Drove <b>$2.3M annual savings</b> by optimizing data acquisition strategy across <b>4 vendor contracts</b>',
            plain_text="Drove $2.3M annual savings by optimizing data acquisition strategy across 4 vendor contracts",
            width_total=470.0,
            fill_percentage=93.0,
            width_status="PASS",
            action_verb="drove",
        ),
        WrittenBullet(
            signal_id="crr-amex",
            achievement_index=0,
            section_type="experience",
            html_text='Increased bid volume by <b>2x</b> by shipping automated valuation model serving <b>50K+ monthly users</b>',
            plain_text="Increased bid volume by 2x by shipping automated valuation model serving 50K+ monthly users",
            width_total=465.0,
            fill_percentage=92.0,
            width_status="PASS",
            action_verb="increased",
        ),
    ]
