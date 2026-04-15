"""Tests for BambooHR, Workday, and iCIMS ATS adapters + keyword filter + registry.

Covers:
1. Happy path — valid JSON response returns filtered JobResults
2. Empty results — no jobs in response
3. Keyword filtering — positive match, negative reject
4. HTTP error handling — 404, 500 responses
5. Malformed JSON response
6. _ATS_SCANNERS dict size (9 entries)
7. INDIA_STARTER_COMPANIES size (12 entries)
"""

from __future__ import annotations

import json
import os
import re
import sys

import httpx
import pytest
import pytest_asyncio

# Ensure worker root is importable
_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from app.pipeline.scanner import (
    INDIA_STARTER_COMPANIES,
    JobResult,
    _ATS_SCANNERS,
    _scan_bamboohr,
    _scan_icims,
    _scan_workday,
    filter_by_keywords,
)


# ---------------------------------------------------------------------------
# filter_by_keywords tests
# ---------------------------------------------------------------------------


class TestFilterByKeywords:
    """Unit tests for the keyword filter function."""

    def test_positive_match(self):
        assert filter_by_keywords("Senior Product Manager", ["product"], []) is True

    def test_positive_no_match(self):
        assert filter_by_keywords("Data Scientist", ["product"], []) is False

    def test_negative_reject(self):
        assert filter_by_keywords("Senior Intern PM", ["pm"], ["intern"]) is False

    def test_negative_without_positive(self):
        """Negative keyword rejects even with no positive keywords."""
        assert filter_by_keywords("Intern Position", [], ["intern"]) is False

    def test_empty_keywords_pass_all(self):
        assert filter_by_keywords("Anything at all", [], []) is True

    def test_case_insensitive(self):
        assert filter_by_keywords("PRODUCT MANAGER", ["product"], []) is True
        assert filter_by_keywords("Product Manager", [], ["PRODUCT"]) is False

    def test_positive_and_negative_both_match(self):
        """Negative takes priority over positive."""
        assert filter_by_keywords("Product Intern", ["product"], ["intern"]) is False

    def test_multiple_positive_one_matches(self):
        assert filter_by_keywords("Data Engineer", ["product", "engineer"], []) is True


# ---------------------------------------------------------------------------
# Registry / constants tests
# ---------------------------------------------------------------------------


class TestRegistry:
    """Verify scanner registry and starter company lists."""

    def test_ats_scanners_has_9_entries(self):
        assert len(_ATS_SCANNERS) == 9
        expected = {
            "greenhouse", "lever", "ashby", "smartrecruiters",
            "workable", "recruitee", "bamboohr", "workday", "icims",
        }
        assert set(_ATS_SCANNERS.keys()) == expected

    def test_new_adapters_in_registry(self):
        assert "bamboohr" in _ATS_SCANNERS
        assert "workday" in _ATS_SCANNERS
        assert "icims" in _ATS_SCANNERS

    def test_india_starter_companies_has_12(self):
        assert len(INDIA_STARTER_COMPANIES) == 12

    def test_india_starter_companies_have_required_keys(self):
        for entry in INDIA_STARTER_COMPANIES:
            assert "name" in entry
            assert "slug" in entry
            assert "ats" in entry


# ---------------------------------------------------------------------------
# BambooHR adapter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScanBambooHR:
    """Tests for _scan_bamboohr."""

    async def test_happy_path_with_result_key(self, httpx_mock):
        """Valid JSON with 'result' key returns filtered jobs."""
        payload = {
            "result": [
                {"id": 101, "jobOpeningName": "Product Manager", "location": {"city": "Bengaluru"}},
                {"id": 102, "jobOpeningName": "Software Engineer", "location": {"city": "Mumbai"}},
            ]
        }
        httpx_mock.add_response(
            url="https://acme.bamboohr.com/careers/list",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_bamboohr(client, "acme", "Acme Corp", ["product"], [])

        assert len(jobs) == 1
        assert jobs[0].title == "Product Manager"
        assert jobs[0].company == "Acme Corp"
        assert jobs[0].job_url == "https://acme.bamboohr.com/careers/101"
        assert jobs[0].location == "Bengaluru"
        assert jobs[0].external_id == "101"

    async def test_happy_path_flat_list(self, httpx_mock):
        """BambooHR sometimes returns a flat list instead of {result: [...]}."""
        payload = [
            {"id": 201, "jobOpeningName": "Designer", "location": "Remote"},
        ]
        httpx_mock.add_response(
            url="https://acme.bamboohr.com/careers/list",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_bamboohr(client, "acme", "Acme Corp", [], [])

        assert len(jobs) == 1
        assert jobs[0].title == "Designer"
        assert jobs[0].location == "Remote"

    async def test_empty_results(self, httpx_mock):
        """Empty result list returns no jobs."""
        httpx_mock.add_response(
            url="https://acme.bamboohr.com/careers/list",
            json={"result": []},
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_bamboohr(client, "acme", "Acme Corp", [], [])

        assert jobs == []

    async def test_keyword_filtering(self, httpx_mock):
        """Negative keywords filter out matching titles."""
        payload = {
            "result": [
                {"id": 1, "jobOpeningName": "Senior PM"},
                {"id": 2, "jobOpeningName": "PM Intern"},
            ]
        }
        httpx_mock.add_response(
            url="https://acme.bamboohr.com/careers/list",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_bamboohr(client, "acme", "Acme Corp", ["pm"], ["intern"])

        assert len(jobs) == 1
        assert jobs[0].title == "Senior PM"

    async def test_http_500_raises(self, httpx_mock):
        """Server error raises HTTPStatusError."""
        httpx_mock.add_response(
            url="https://acme.bamboohr.com/careers/list",
            status_code=500,
        )
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await _scan_bamboohr(client, "acme", "Acme Corp", [], [])

    async def test_http_404_raises(self, httpx_mock):
        """404 raises HTTPStatusError."""
        httpx_mock.add_response(
            url="https://acme.bamboohr.com/careers/list",
            status_code=404,
        )
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await _scan_bamboohr(client, "acme", "Acme Corp", [], [])

    async def test_malformed_json_returns_empty(self, httpx_mock):
        """Non-JSON response falls back to empty list."""
        httpx_mock.add_response(
            url="https://acme.bamboohr.com/careers/list",
            text="<html>Not JSON</html>",
            headers={"Content-Type": "text/html"},
        )
        async with httpx.AsyncClient() as client:
            # BambooHR adapter calls resp.json() in a try/except
            # but first calls raise_for_status — which passes for 200
            # then .json() fails and returns []
            jobs = await _scan_bamboohr(client, "acme", "Acme Corp", [], [])

        assert jobs == []


# ---------------------------------------------------------------------------
# Workday adapter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScanWorkday:
    """Tests for _scan_workday."""

    async def test_happy_path_wd5(self, httpx_mock):
        """Valid response from wd5 endpoint returns filtered jobs."""
        payload = {
            "jobPostings": [
                {
                    "title": "Product Manager",
                    "externalPath": "/job/PM-Role/12345",
                    "bulletFields": ["Bengaluru, India"],
                },
                {
                    "title": "Intern",
                    "externalPath": "/job/Intern/99999",
                    "bulletFields": [],
                },
            ]
        }
        httpx_mock.add_response(
            url="https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", ["product"], [])

        assert len(jobs) == 1
        assert jobs[0].title == "Product Manager"
        assert "wd5" in jobs[0].job_url
        assert "/job/PM-Role/12345" in jobs[0].job_url
        assert jobs[0].location == "Bengaluru, India"

    async def test_fallback_to_wd1(self, httpx_mock):
        """If wd5 returns 404, falls back to wd1."""
        # wd5 fails
        httpx_mock.add_response(
            url="https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            status_code=404,
        )
        # wd1 succeeds
        payload = {
            "jobPostings": [
                {"title": "Engineer", "externalPath": "/job/Eng/111", "locationsText": "Remote"},
            ]
        }
        httpx_mock.add_response(
            url="https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", [], [])

        assert len(jobs) == 1
        assert jobs[0].title == "Engineer"
        assert "wd1" in jobs[0].job_url
        assert jobs[0].location == "Remote"

    async def test_fallback_to_wd3(self, httpx_mock):
        """If wd5 and wd1 both fail, falls back to wd3."""
        httpx_mock.add_response(
            url="https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            status_code=404,
        )
        httpx_mock.add_response(
            url="https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            status_code=404,
        )
        payload = {
            "jobPostings": [
                {"title": "PM", "externalPath": "/job/PM/222", "bulletFields": []},
            ]
        }
        httpx_mock.add_response(
            url="https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", [], [])

        assert len(jobs) == 1
        assert jobs[0].title == "PM"
        assert "wd3" in jobs[0].job_url

    async def test_all_instances_fail_returns_empty(self, httpx_mock):
        """All wd5/wd1/wd3 fail -> empty list."""
        for num in [5, 1, 3]:
            httpx_mock.add_response(
                url=f"https://acme.wd{num}.myworkdayjobs.com/wday/cxs/acme/External/jobs",
                method="POST",
                status_code=404,
            )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", [], [])

        assert jobs == []

    async def test_empty_job_postings(self, httpx_mock):
        """Response with empty jobPostings list returns nothing."""
        httpx_mock.add_response(
            url="https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            json={"jobPostings": []},
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", [], [])

        assert jobs == []

    async def test_keyword_filtering(self, httpx_mock):
        """Positive + negative keywords filter correctly."""
        payload = {
            "jobPostings": [
                {"title": "Senior Product Manager", "externalPath": "/job/SPM/1"},
                {"title": "Product Manager Intern", "externalPath": "/job/PMI/2"},
                {"title": "Data Analyst", "externalPath": "/job/DA/3"},
            ]
        }
        httpx_mock.add_response(
            url="https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", ["product"], ["intern"])

        assert len(jobs) == 1
        assert jobs[0].title == "Senior Product Manager"

    async def test_http_500_all_instances(self, httpx_mock):
        """500 on all instances returns empty (caught by except clause)."""
        for num in [5, 1, 3]:
            httpx_mock.add_response(
                url=f"https://acme.wd{num}.myworkdayjobs.com/wday/cxs/acme/External/jobs",
                method="POST",
                status_code=500,
            )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", [], [])

        assert jobs == []

    async def test_location_from_locationsText(self, httpx_mock):
        """Falls back to locationsText when no bulletField matches geo keywords."""
        payload = {
            "jobPostings": [
                {
                    "title": "PM",
                    "externalPath": "/job/PM/1",
                    "bulletFields": ["Full-time", "Mid-level"],
                    "locationsText": "London, UK",
                },
            ]
        }
        httpx_mock.add_response(
            url="https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/jobs",
            method="POST",
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_workday(client, "acme", "Acme Corp", [], [])

        assert jobs[0].location == "London, UK"


# ---------------------------------------------------------------------------
# iCIMS adapter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScanICIMS:
    """Tests for _scan_icims."""

    async def test_happy_path(self, httpx_mock):
        """Valid JSON response with jobs key returns filtered jobs."""
        payload = {
            "jobs": [
                {"id": 1001, "title": "Product Manager", "location": "Bengaluru"},
                {"id": 1002, "title": "Data Scientist", "location": "Mumbai"},
            ]
        }
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_icims(client, "acme", "Acme Corp", ["product"], [])

        assert len(jobs) == 1
        assert jobs[0].title == "Product Manager"
        assert jobs[0].company == "Acme Corp"
        assert "1001" in jobs[0].job_url
        assert jobs[0].external_id == "1001"

    async def test_empty_jobs(self, httpx_mock):
        """Empty jobs list returns nothing."""
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            json={"jobs": []},
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_icims(client, "acme", "Acme Corp", [], [])

        assert jobs == []

    async def test_keyword_filtering(self, httpx_mock):
        """Keywords filter correctly on iCIMS titles."""
        payload = {
            "jobs": [
                {"id": 1, "title": "Senior PM"},
                {"id": 2, "title": "PM Intern"},
                {"id": 3, "title": "Engineer"},
            ]
        }
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_icims(client, "acme", "Acme Corp", ["pm"], ["intern"])

        assert len(jobs) == 1
        assert jobs[0].title == "Senior PM"

    async def test_http_404_raises(self, httpx_mock):
        """404 raises HTTPStatusError."""
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            status_code=404,
        )
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await _scan_icims(client, "acme", "Acme Corp", [], [])

    async def test_http_500_raises(self, httpx_mock):
        """500 raises HTTPStatusError."""
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            status_code=500,
        )
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await _scan_icims(client, "acme", "Acme Corp", [], [])

    async def test_malformed_json_returns_empty(self, httpx_mock):
        """Non-JSON response falls back to empty list."""
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            text="<html>Error</html>",
            headers={"Content-Type": "text/html"},
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_icims(client, "acme", "Acme Corp", [], [])

        assert jobs == []

    async def test_flat_list_response(self, httpx_mock):
        """iCIMS sometimes returns a flat list instead of {jobs: [...]}."""
        payload = [
            {"id": 501, "title": "Designer", "location": "Remote"},
        ]
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_icims(client, "acme", "Acme Corp", [], [])

        assert len(jobs) == 1
        assert jobs[0].title == "Designer"

    async def test_location_as_dict(self, httpx_mock):
        """Location field as dict is handled gracefully."""
        payload = {
            "jobs": [
                {"id": 1, "title": "PM", "location": {"name": "Delhi", "city": "New Delhi"}},
            ]
        }
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_icims(client, "acme", "Acme Corp", [], [])

        assert len(jobs) == 1
        assert jobs[0].location == "Delhi"

    async def test_uses_name_field_fallback(self, httpx_mock):
        """Falls back to 'name' field when 'title' is missing."""
        payload = {
            "jobs": [
                {"id": 1, "name": "Product Lead"},
            ]
        }
        httpx_mock.add_response(
            url=re.compile(r"https://careers-acme\.icims\.com/jobs/search.*"),
            json=payload,
        )
        async with httpx.AsyncClient() as client:
            jobs = await _scan_icims(client, "acme", "Acme Corp", [], [])

        assert len(jobs) == 1
        assert jobs[0].title == "Product Lead"
