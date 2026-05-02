"""Agent 1: JD Parser — Extracts keywords, strategy, and requirements from job descriptions."""
from __future__ import annotations

import json
import os

from anthropic import Anthropic

from linkright.schemas.jd_analysis import JDAnalysis, JDKeyword, BrandColors


SYSTEM_PROMPT = """You are a job description analyzer for resume optimization.
Given a job description, extract structured information to help tailor a resume.

Return a JSON object with these fields:
{
  "company_name": "string",
  "role_title": "string",
  "career_level": "fresher|entry|mid|senior|executive",
  "strategy": "METRIC_BOMBARDMENT|SKILL_MATCHING|LEADERSHIP_NARRATIVE|TRANSFORMATION_STORY|BALANCED",
  "keywords": [{"keyword": "string", "category": "skill|tool|action|domain|certification", "priority": "P0|P1|P2"}],
  "requirements_p0": ["must-have requirement strings"],
  "requirements_p1": ["should-have requirement strings"],
  "requirements_p2": ["nice-to-have requirement strings"],
  "summary": "one-line role summary"
}

Strategy selection rules:
- METRIC_BOMBARDMENT: JD emphasizes measurable impact, ROI, revenue, percentages. Best for data-heavy roles.
- SKILL_MATCHING: JD lists many specific tools/technologies. Best for technical roles.
- LEADERSHIP_NARRATIVE: JD emphasizes team management, cross-functional leadership, scaling. Best for senior/director roles.
- TRANSFORMATION_STORY: JD is about change management, 0→1 product building, turnaround. Best for startup roles.
- BALANCED: JD is a mix of the above. Default for most PM roles.

Career level rules:
- fresher: 0-1 years, entry-level, associate, intern
- entry: 1-3 years, junior
- mid: 3-5 years, product manager
- senior: 5-8 years, senior PM, lead PM
- executive: 8+ years, director, VP, head of product

Extract ALL relevant keywords — technical skills, soft skills, tools, domains, certifications.
Classify each as P0 (explicitly required/must-have), P1 (preferred/should-have), or P2 (nice-to-have/bonus).

Return ONLY valid JSON, no markdown fences."""


def parse_jd(jd_text: str) -> JDAnalysis:
    """Parse a job description using Claude API.

    Args:
        jd_text: Raw job description text.

    Returns:
        JDAnalysis with extracted keywords, strategy, and requirements.
    """
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Analyze this job description:\n\n{jd_text}"}],
    )

    raw_json = response.content[0].text.strip()
    # Handle potential markdown fences
    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[1].rsplit("```", 1)[0]

    data = json.loads(raw_json)

    # Convert keywords list
    keywords = [JDKeyword(**kw) for kw in data.get("keywords", [])]

    # Build brand colors if present
    brand_colors = None
    if data.get("brand_colors"):
        brand_colors = BrandColors(**data["brand_colors"])

    return JDAnalysis(
        company_name=data["company_name"],
        role_title=data["role_title"],
        career_level=data["career_level"],
        strategy=data["strategy"],
        keywords=keywords,
        brand_colors=brand_colors,
        requirements_p0=data.get("requirements_p0", []),
        requirements_p1=data.get("requirements_p1", []),
        requirements_p2=data.get("requirements_p2", []),
        summary=data.get("summary"),
    )
