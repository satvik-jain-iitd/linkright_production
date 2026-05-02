"""Career profile definitions for detecting candidate experience level.

Defines detection criteria, default section ordering, space allocations,
summary line counts, and section title mappings for each career tier.

Extracted from Section 3.6 of SPEC-v2-resume-mcp.
"""

CAREER_PROFILES = {
    "fresher": {
        "years_range": (0, 1),
        "detection_signals": [
            "currently studying",
            "recent graduate",
            "campus hiring",
            "no prior work"
        ],
        "default_section_order": [
            "Education & Academics",
            "Scholastic Achievements",
            "Internship Experience",
            "Academic & Personal Projects",
            "Extracurriculars & Positions of Responsibility",
            "Skills",
            "Interests"
        ],
        "space_allocation": {
            "Education & Academics": 25,
            "Scholastic Achievements": 10,
            "Internship Experience": 35,
            "Academic & Personal Projects": 15,
            "Extracurriculars & Positions of Responsibility": 8,
            "Skills": 5,
            "Interests": 2
        },
        "summary_lines": 2,
        "section_titles": {
            "professional_summary": "Professional Summary",
            "experience": "Internship Experience",
            "education": "Education & Academics",
            "skills": "Skills",
            "projects": "Academic & Personal Projects",
            "awards": "Scholastic Achievements",
            "certifications": "Certifications"
        }
    },
    "entry": {
        "years_range": (1, 3),
        "detection_signals": [
            "first professional role",
            "entry-level position",
            "early career"
        ],
        "default_section_order": [
            "Professional Summary",
            "Professional Experience",
            "Internship Experience",
            "Education",
            "Projects",
            "Skills",
            "Certifications",
            "Interests"
        ],
        "space_allocation": {
            "Professional Summary": 8,
            "Professional Experience": 50,
            "Internship Experience": 10,
            "Education": 12,
            "Projects": 8,
            "Skills": 7,
            "Certifications": 3,
            "Interests": 2
        },
        "summary_lines": 2,
        "section_titles": {
            "professional_summary": "Professional Summary",
            "experience": "Professional Experience",
            "education": "Education",
            "skills": "Skills",
            "projects": "Projects",
            "internships": "Internship Experience",
            "awards": "Awards & Recognition",
            "certifications": "Certifications"
        }
    },
    "mid": {
        "years_range": (3, 8),
        "detection_signals": [
            "team leadership experience",
            "cross-functional ownership",
            "technical depth"
        ],
        "default_section_order": [
            "Professional Summary",
            "Professional Experience",
            "Key Initiatives",
            "Skills & Competencies",
            "Education",
            "Certifications & Training",
            "Interests"
        ],
        "space_allocation": {
            "Professional Summary": 8,
            "Professional Experience": 55,
            "Key Initiatives": 12,
            "Skills & Competencies": 12,
            "Education": 8,
            "Certifications & Training": 3,
            "Interests": 2
        },
        "summary_lines": 3,
        "section_titles": {
            "professional_summary": "Professional Summary",
            "experience": "Professional Experience",
            "education": "Education",
            "skills": "Skills & Competencies",
            "projects": "Key Initiatives",
            "awards": "Awards & Recognition",
            "certifications": "Certifications & Training"
        }
    },
    "senior": {
        "years_range": (8, 15),
        "detection_signals": [
            "organizational leadership",
            "strategic decision-making",
            "multi-team management"
        ],
        "default_section_order": [
            "Professional Summary",
            "Professional Experience",
            "Skills & Expertise",
            "Board & Advisory Roles",
            "Education",
            "Publications & Speaking"
        ],
        "space_allocation": {
            "Professional Summary": 10,
            "Professional Experience": 60,
            "Skills & Expertise": 10,
            "Board & Advisory Roles": 5,
            "Education": 10,
            "Publications & Speaking": 5
        },
        "summary_lines": 3,
        "section_titles": {
            "professional_summary": "Professional Summary",
            "experience": "Professional Experience",
            "education": "Education",
            "skills": "Skills & Expertise",
            "projects": "Key Initiatives",
            "awards": "Awards & Recognition",
            "board": "Board & Advisory Roles",
            "speaking": "Publications & Speaking"
        }
    },
    "executive": {
        "years_range": (15, 100),
        "detection_signals": [
            "founded or scaled company",
            "executive leadership",
            "industry recognition"
        ],
        "default_section_order": [
            "Executive Summary",
            "Professional Experience",
            "Board & Advisory Positions",
            "Education",
            "Industry Recognition & Awards"
        ],
        "space_allocation": {
            "Executive Summary": 12,
            "Professional Experience": 65,
            "Board & Advisory Positions": 8,
            "Education": 10,
            "Industry Recognition & Awards": 5
        },
        "summary_lines": 4,
        "section_titles": {
            "professional_summary": "Executive Summary",
            "experience": "Professional Experience",
            "education": "Education",
            "skills": "Core Competencies",
            "projects": "Key Ventures",
            "awards": "Industry Recognition & Awards",
            "board": "Board & Advisory Positions"
        }
    }
}
