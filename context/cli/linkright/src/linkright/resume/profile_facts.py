"""Best-effort expected profile facts for resume diagnostics.

The resume pipeline can run from a persistent profile cache, from a one-off
run directory, or from older career_signals YAML inputs. Diagnostics should use
whatever user-provided facts are available without making those files required.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class ExpectedProfileFacts:
    name: str = ""
    companies: tuple[str, ...] = ()


def _default_profile_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    if home:
        return Path(home) / "profile"
    return Path.home() / ".linkright" / "profile"


def _load_yaml(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists() or not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _clean(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _dedupe(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = _clean(value)
        key = normalize_for_match(cleaned)
        if not cleaned or not key or key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return tuple(out)


def _name_from_mapping(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    contact = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    for source in (contact, metadata, data):
        for key in ("name", "full_name", "user"):
            value = _clean(source.get(key))
            if value:
                return value
    return ""


def _companies_from_mapping(data: Any) -> list[str]:
    companies: list[str] = []
    if not isinstance(data, dict):
        return companies

    for key in ("expected_companies", "companies", "employers"):
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    companies.append(item.get("name") or item.get("company") or "")
                else:
                    companies.append(item)
        elif isinstance(value, dict):
            companies.extend(value.keys())

    for key in ("signals", "experiences", "experience", "work_experience", "work_history"):
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    companies.append(item.get("company") or item.get("employer") or item.get("organization") or "")

    return companies


def _yaml_candidates(run_dir: Path | None, profile_dir: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if profile_dir:
        candidates.extend(
            [
                profile_dir / "contact.yaml",
                profile_dir / "metadata.yaml",
                profile_dir / "profile.yaml",
                profile_dir / "career_signals.yaml",
            ]
        )
    if run_dir:
        candidates.extend([run_dir / "contact.yaml", run_dir / "metadata.yaml"])
        inputs = run_dir / "inputs"
        if inputs.exists():
            candidates.extend(sorted(inputs.glob("*.yaml")))
            candidates.extend(sorted(inputs.glob("*.yml")))
    return candidates


def load_expected_profile_facts(
    run_dir: Path | None = None,
    profile_dir: Path | None = None,
) -> ExpectedProfileFacts:
    """Load expected user name and companies from local profile facts.

    Returns empty fields when no profile metadata is available. This function is
    intentionally permissive because diagnostics should never break a resume run.
    """

    profile_dir = profile_dir or _default_profile_dir()
    name = ""
    companies: list[str] = []

    for path in _yaml_candidates(run_dir, profile_dir):
        data = _load_yaml(path)
        if not data:
            continue
        if not name:
            name = _name_from_mapping(data)
        companies.extend(_companies_from_mapping(data))

    nuggets_paths: list[Path] = []
    if profile_dir:
        nuggets_paths.append(profile_dir / "nuggets.jsonl")
    if run_dir:
        nuggets_paths.append(run_dir / "nuggets.jsonl")

    for path in nuggets_paths:
        for row in _load_jsonl(path):
            ntype = (row.get("type") or "work_experience").lower()
            company = _clean(row.get("company"))
            if company and ntype == "work_experience" and company.lower() not in ("none", "null"):
                companies.append(company)

    return ExpectedProfileFacts(name=name, companies=_dedupe(companies))


def normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def value_in_text(text: str, expected: str) -> bool:
    expected_norm = normalize_for_match(expected)
    if len(expected_norm) < 3:
        return False
    return expected_norm in normalize_for_match(text)


def missing_expected_values(expected: Iterable[str], observed: Iterable[str]) -> list[str]:
    observed_norm = [normalize_for_match(v) for v in observed if normalize_for_match(v)]
    missing: list[str] = []
    for value in expected:
        value_norm = normalize_for_match(value)
        if len(value_norm) < 3:
            continue
        if any(value_norm in obs or obs in value_norm for obs in observed_norm if len(obs) >= 3):
            continue
        missing.append(value)
    return missing
