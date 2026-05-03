"""Pydantic models for the /api/captures endpoint.

Hard length caps prevent DB bloat AND limit the privacy blast radius if a
malicious or buggy userscript ever sends a giant payload.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ── Hard caps (defense in depth: the userscript SHOULD trim, but we re-cap here) ──
MAX_TITLE_LEN        = 500
MAX_COMPANY_NAME_LEN = 250
MAX_LOCATION_LEN     = 250
MAX_SALARY_TEXT_LEN  = 200
MAX_JD_TEXT_LEN      = 50_000     # 50 KB — covers very long JDs without bloating Oracle PG
MAX_RAW_PAYLOAD_LEN  = 100_000    # 100 KB — debug payload; truncated above this

CaptureSource  = Literal["naukri", "linkedin", "indeed", "wellfound"]
DedupStatus    = Literal["new", "updated", "skipped"]
CompanyStatus  = Literal["matched_existing", "created_new"]


class CaptureIn(BaseModel):
    """Request body for `POST /api/captures`."""

    source:          CaptureSource
    job_url:         str = Field(..., min_length=1, max_length=2048)
    external_id:     Optional[str] = Field(default=None, max_length=200)
    title:           str
    company_name:    str
    company_website: Optional[str] = Field(default=None, max_length=500)
    location:        Optional[str] = None
    salary_text:     Optional[str] = None
    jd_text:         Optional[str] = None
    posted_at:       Optional[datetime] = None
    captured_at:     datetime
    raw_payload:     Optional[dict[str, Any]] = None

    @field_validator("title")
    @classmethod
    def _title_required_capped(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        return v[:MAX_TITLE_LEN]

    @field_validator("company_name")
    @classmethod
    def _company_required_capped(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("company_name cannot be empty")
        return v[:MAX_COMPANY_NAME_LEN]

    @field_validator("location")
    @classmethod
    def _location_capped(cls, v: Optional[str]) -> Optional[str]:
        return v[:MAX_LOCATION_LEN] if v else v

    @field_validator("salary_text")
    @classmethod
    def _salary_capped(cls, v: Optional[str]) -> Optional[str]:
        return v[:MAX_SALARY_TEXT_LEN] if v else v

    @field_validator("jd_text")
    @classmethod
    def _jd_text_capped(cls, v: Optional[str]) -> Optional[str]:
        return v[:MAX_JD_TEXT_LEN] if v else v

    @field_validator("raw_payload")
    @classmethod
    def _raw_payload_size_check(cls, v: Optional[dict]) -> Optional[dict]:
        # Replace oversized payloads with a marker — keeps the response useful
        # for debugging without flooding Oracle PG with multi-MB JSON blobs.
        if v is None:
            return v
        try:
            serialized = json.dumps(v, default=str)
            if len(serialized) > MAX_RAW_PAYLOAD_LEN:
                return {"_truncated": True, "_original_size_bytes": len(serialized)}
        except (TypeError, ValueError):
            return None
        return v


class CaptureOut(BaseModel):
    """Response body for `POST /api/captures`."""

    ok:             bool
    job_id:         Optional[str]          = None
    canonical_id:   Optional[str]          = None
    dedup_status:   Optional[DedupStatus]  = None
    company_status: Optional[CompanyStatus] = None
    notes:          Optional[str]          = None
