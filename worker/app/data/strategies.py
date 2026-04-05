"""Optimization strategy definitions for resume customization.

Defines 5 strategies for optimizing resume emphasis and content placement
based on job description analysis.

Extracted from Section 3.7 of SPEC-v2-resume-mcp.
"""

STRATEGIES = {
    "METRIC_BOMBARDMENT": {
        "name": "METRIC_BOMBARDMENT",
        "description": "Maximize quantified metrics. Every bullet leads with or contains a number. Bold and color every metric.",
        "trigger": "When JD emphasizes outcomes, revenue growth, measurable impact, or business metrics.",
        "bullet_emphasis": "metrics",
        "verb_style": "action-driven",
        "summary_focus": "quantifiable impact",
        "emphasis_rules": {
            "metric_display": "bold + color",
            "arrow_use": "\u2191 (green) for increases, \u2193 (red) for decreases",
            "bullet_lead": "Every bullet should start with or quickly introduce a number",
            "keywords": [
                "percentage",
                "revenue",
                "growth",
                "cost",
                "reduction",
                "improvement",
                "increase",
                "ROI",
                "impact"
            ]
        }
    },
    "SKILL_MATCHING": {
        "name": "SKILL_MATCHING",
        "description": "Every required/desired skill appears in context within experience bullets or project titles.",
        "trigger": "When JD reads like a tech/tool laundry list ('Must know: Python, AWS, Kubernetes, Tableau, etc.').",
        "bullet_emphasis": "skills",
        "verb_style": "technical",
        "summary_focus": "technical expertise",
        "emphasis_rules": {
            "skill_embedding": "Each JD-required skill appears in at least one bullet's context",
            "title_emphasis": "Project titles reference specific tools/skills",
            "section_allocation": "Skills section gets +5% space (at the expense of less-relevant content)",
            "keywords": [
                "Python",
                "AWS",
                "SQL",
                "Kubernetes",
                "Docker",
                "Terraform",
                "Java",
                "Go",
                "React",
                "Angular"
            ]
        }
    },
    "LEADERSHIP_NARRATIVE": {
        "name": "LEADERSHIP_NARRATIVE",
        "description": "Emphasize team sizes, stakeholder levels, organizational scope, leadership verbs.",
        "trigger": "When JD is for a people-management, leadership, or organizational role.",
        "bullet_emphasis": "leadership",
        "verb_style": "people-centric",
        "summary_focus": "organizational impact",
        "emphasis_rules": {
            "team_size": "Always mention number of direct reports, team members, or cross-functional collaborators",
            "stakeholder_level": "Specify level of stakeholder engagement (e.g., 'reported to VP', 'partnered with C-suite')",
            "leadership_verbs": [
                "led",
                "directed",
                "mentored",
                "coached",
                "cultivated",
                "orchestrated",
                "championed"
            ],
            "metrics": "Emphasize org-level impact (team velocity, retention, culture metrics) not just technical output"
        }
    },
    "TRANSFORMATION_STORY": {
        "name": "TRANSFORMATION_STORY",
        "description": "Frame bullets as before/after narratives. Emphasize magnitude of change and significance.",
        "trigger": "When JD emphasizes innovation, disruption, 0-to-1 building, turnarounds, or industry shifts.",
        "bullet_emphasis": "transformation",
        "verb_style": "narrative-driven",
        "summary_focus": "disruptive change",
        "emphasis_rules": {
            "before_after": "Every major bullet includes implicit or explicit before/after state",
            "magnitude": "Quantify the span of change (time saved, scale increase, scope expansion)",
            "narrative_arc": "Bullets tell a story: problem identified \u2192 solution designed \u2192 outcome delivered",
            "keywords": [
                "transformed",
                "rebuilt",
                "pioneered",
                "scaled from X to Y",
                "shifted",
                "evolved",
                "modernized"
            ]
        }
    },
    "BALANCED": {
        "name": "BALANCED",
        "description": "Blend metrics + skills + context in natural proportions.",
        "trigger": "Default strategy when JD is mixed or when confidence in other strategies is low.",
        "bullet_emphasis": "mixed",
        "verb_style": "professional",
        "summary_focus": "comprehensive expertise",
        "emphasis_rules": {
            "metric_frequency": "~50% of bullets include quantified metrics",
            "skill_embedding": "Key JD skills appear in context, but not forced into every bullet",
            "emphasis_balance": "Metrics colored, some skills bolded, but not overwhelming",
            "keywords": [
                "mixed",
                "balanced",
                "contextual",
                "professional"
            ]
        }
    }
}
