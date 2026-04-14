"""Pydantic models for the browser snippet execution framework."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SnippetCookie(BaseModel):
    """A cookie to inject before executing the snippet."""
    name: str
    value: str
    domain: str
    path: str = "/"


class SnippetRequest(BaseModel):
    """Request to execute a JS extraction snippet on a web page."""
    url: str = Field(..., description="Target page URL to navigate to")
    js_code: str = Field(..., description="JS code to execute in page context — must return JSON-serializable array")
    cookies: list[SnippetCookie] = Field(default_factory=list, description="Cookies to inject before navigation (e.g., li_at for LinkedIn)")
    wait_selector: str | None = Field(None, description="CSS selector to wait for before executing JS (ensures page loaded)")
    timeout_ms: int = Field(30_000, description="Max time to wait for page + execution")
    user_agent: str | None = Field(None, description="Override user-agent string")


class ExtractedJob(BaseModel):
    """A single job extracted from a browser snippet."""
    title: str
    company: str = ""
    location: str = ""
    job_url: str = ""
    description_snippet: str = ""


class SnippetResponse(BaseModel):
    """Result of executing a browser snippet."""
    success: bool
    jobs: list[ExtractedJob] = Field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0
    page_title: str = ""
