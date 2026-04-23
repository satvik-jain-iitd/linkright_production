"""Fixture JDs and expected annotation values for deterministic E2E testing.

6 fixture JDs covering all enrichment edge cases. Each comes with ground-truth
expected annotation values used by Layer 1 unit tests and baseline scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FixtureJD:
    name: str
    jd_text: str
    expected_remote_ok: bool | None        # True/False/None=unknown
    expected_experience_level: str         # early/mid/senior/executive/cxo
    expected_employment_type: str          # full_time/contract/part_time
    expected_action_min: str              # minimum acceptable recommended_action
    notes: str = ""


FIXTURE_JDS: list[FixtureJD] = [
    FixtureJD(
        name="pm_remote_yes",
        jd_text="""Product Manager — Platform AI
        We are hiring a Product Manager to lead our AI platform product.
        This is a fully remote position. Salary: $130,000 – $160,000 annually.
        Requirements: 5+ years of product management experience.
        We value autonomy, transparency, and fast iteration. Series B startup.
        Strong preference for candidates with LLM/ML product experience.
        Remote OK. Flexible hours. Equity included.""",
        expected_remote_ok=True,
        expected_experience_level="senior",
        expected_employment_type="full_time",
        expected_action_min="maybe",
        notes="Strong JD, remote=yes, clear comp range",
    ),
    FixtureJD(
        name="pm_onsite_no_remote",
        jd_text="""Senior Product Manager — FinTech
        We are looking for a Senior PM to join our NYC office.
        This is an onsite-only role. No remote work available.
        3–5 years of PM experience required.
        You will work closely with engineering and design in our Manhattan office.
        Compensation: $110,000 – $130,000. We do not sponsor visas.""",
        expected_remote_ok=False,
        expected_experience_level="senior",
        expected_employment_type="full_time",
        expected_action_min="maybe",
        notes="Onsite only, no remote, no visa",
    ),
    FixtureJD(
        name="pm_visa_sponsor",
        jd_text="""Product Manager — Consumer Apps
        We are hiring a Product Manager for our consumer mobile team.
        We actively sponsor H1B visas and welcome international candidates.
        Series A startup in healthcare tech. 4–6 years experience.
        Hybrid role, 3 days onsite in San Francisco.
        Salary range: $120,000 – $145,000 plus equity.""",
        expected_remote_ok=None,
        expected_experience_level="senior",
        expected_employment_type="full_time",
        expected_action_min="maybe",
        notes="Visa sponsor explicit, hybrid",
    ),
    FixtureJD(
        name="associate_pm_early",
        jd_text="""Associate Product Manager — Rotational Program
        Join our APM rotational program for early-career product thinkers.
        0–2 years of experience required. Recent graduates welcome.
        You will work as an individual contributor across 3 product teams.
        No people management responsibilities.
        Stipend: $70,000 – $85,000. Remote-friendly.""",
        expected_remote_ok=True,
        expected_experience_level="early",
        expected_employment_type="full_time",
        expected_action_min="skip",
        notes="Entry level APM, low comp, IC only",
    ),
    FixtureJD(
        name="red_flag_jd",
        jd_text="""Product Manager Needed URGENTLY
        We need a product manager who can do EVERYTHING.
        Salary: competitive (we don't disclose). Must wear many hats.
        10+ years REQUIRED for this role. Immediate start.
        You will manage product, design, marketing AND engineering.
        Fast-paced startup environment. Long hours expected.
        No benefits discussed. Apply immediately.""",
        expected_remote_ok=None,
        expected_experience_level="executive",
        expected_employment_type="full_time",
        expected_action_min="skip",
        notes="Multiple red flags: no comp, unrealistic, urgency",
    ),
    FixtureJD(
        name="strong_faang_jd",
        jd_text="""Lead Product Manager — AI/ML Platform (FAANG)
        We are looking for a Lead PM to own our AI inference infrastructure product.
        Hybrid NYC office, 2 days onsite per week. Salary: $200,000 – $240,000 + equity.
        7+ years of product management experience required, 3+ years in ML/LLM products.
        You will drive roadmap for serving infrastructure used by 500M users.
        Comprehensive benefits, 401k, health. We sponsor visas.
        Strong culture of ownership and psychological safety.""",
        expected_remote_ok=None,
        expected_experience_level="senior",
        expected_employment_type="full_time",
        expected_action_min="worth_it",
        notes="FAANG, high comp, strong JD, LLM focus",
    ),
]

FIXTURE_MAP: dict[str, FixtureJD] = {f.name: f for f in FIXTURE_JDS}


# PM user profile used across all tests
PM_USER_TAGS = [
    "product management", "roadmap", "stakeholder management",
    "agile", "sql", "data analysis", "user research",
    "product strategy", "go-to-market", "jira",
]

PM_USER_PREFS = {
    "target_roles": ["Product Manager", "Senior PM", "Lead PM"],
    "min_comp_usd": 120000,
    "location_preference": "hybrid_ok",
    "visa_status": "no_sponsorship_needed",
}

# Mock Greenhouse JSON response (Notion jobs endpoint)
MOCK_GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 12345,
            "title": "Senior Product Manager",
            "absolute_url": "https://boards.greenhouse.io/notion/jobs/12345",
            "location": {"name": "Remote"},
            "metadata": [],
        },
        {
            "id": 12346,
            "title": "Associate Product Manager",
            "absolute_url": "https://boards.greenhouse.io/notion/jobs/12346",
            "location": {"name": "New York, NY"},
            "metadata": [],
        },
    ]
}

MOCK_ADZUNA_RESPONSE = {
    "results": [
        {
            "id": "adzuna-001",
            "title": "Product Manager",
            "company": {"display_name": "TechCorp India"},
            "redirect_url": "https://www.adzuna.in/jobs/details/adzuna-001",
            "location": {"display_name": "Bengaluru, Karnataka"},
            "salary_min": 2000000,
            "salary_max": 3000000,
            "description": "We need a product manager with 5+ years experience.",
        }
    ],
    "__CLASS__": "Job",
    "count": 1,
}

MOCK_THEMUSE_RESPONSE = {
    "results": [
        {
            "id": 12345,
            "name": "Senior Product Manager",
            "company": {"name": "Stripe"},
            "refs": {"landing_page": "https://www.themuse.com/jobs/stripe/spm"},
            "locations": [{"name": "Remote"}],
            "levels": [{"name": "Senior Level"}],
            "publication_date": "2026-04-22T00:00:00Z",
        }
    ],
    "page": 0,
    "page_count": 1,
    "items_per_page": 20,
    "total": 1,
}

MOCK_REMOTIVE_RESPONSE = {
    "jobs": [
        {
            "id": 1001,
            "url": "https://remotive.com/remote-jobs/product/pm-1001",
            "title": "Product Manager",
            "company_name": "RemoteFirst Co",
            "category": "Product",
            "candidate_required_location": "Worldwide",
            "salary": "$100,000 - $130,000",
            "description": "We are hiring a remote product manager.",
            "publication_date": "2026-04-22",
        }
    ]
}

MOCK_IIMJOBS_RESPONSE = {
    "data": {
        "jobs": [
            {
                "jobId": "iim-001",
                "jobTitle": "Senior Product Manager",
                "companyName": "Flipkart",
                "jobUrl": "https://www.iimjobs.com/j/senior-pm-iim-001",
                "location": "Bangalore",
                "experience": "5-9 Years",
                "salary": "25-35 LPA",
            }
        ]
    }
}

MOCK_WELLFOUND_RESPONSE = {
    "data": {
        "talent__job_search_v1": {
            "jobs": [
                {
                    "jobListingId": "wf-001",
                    "jobListingTitle": "Product Manager",
                    "companyName": "Y Combinator Startup",
                    "jobListingSlug": "pm-wf-001",
                    "remote": True,
                    "locationNames": ["Remote"],
                    "compensation": "$120k – $160k",
                }
            ],
            "totalJobListings": 1,
        }
    }
}

MOCK_JSEARCH_RESPONSE = {
    "data": [
        {
            "job_id": "js-001",
            "job_title": "Senior Product Manager",
            "employer_name": "Google",
            "job_apply_link": "https://careers.google.com/jobs/js-001",
            "job_city": "Mountain View",
            "job_country": "US",
            "job_is_remote": False,
            "job_min_salary": 180000,
            "job_max_salary": 220000,
            "job_description": "Lead product strategy for Google's AI products.",
        }
    ],
    "status": "OK",
}
