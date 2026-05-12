from __future__ import annotations

import json
from pathlib import Path

import yaml

from linkright.resume.profile_facts import (
    load_expected_profile_facts,
    missing_expected_values,
    value_in_text,
)


def test_loads_expected_name_and_companies_from_profile(monkeypatch, tmp_path: Path):
    home = tmp_path / "home"
    profile = home / "profile"
    profile.mkdir(parents=True)
    monkeypatch.setenv("LINKRIGHT_HOME", str(home))

    (profile / "contact.yaml").write_text(
        yaml.safe_dump({"name": "Avery Example"}),
        encoding="utf-8",
    )
    rows = [
        {"type": "work_experience", "company": "Northstar Labs", "answer": "Shipped pricing"},
        {"type": "work_experience", "company": "Vector Works", "answer": "Led rollout"},
        {"type": "skill", "company": "", "answer": "Python"},
    ]
    (profile / "nuggets.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows),
        encoding="utf-8",
    )

    facts = load_expected_profile_facts()

    assert facts.name == "Avery Example"
    assert facts.companies == ("Northstar Labs", "Vector Works")


def test_loads_expected_facts_from_run_career_signals(tmp_path: Path):
    run = tmp_path / "run"
    inputs = run / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "career_signals.yaml").write_text(
        yaml.safe_dump(
            {
                "metadata": {"user": "Riley Candidate"},
                "signals": [
                    {"company": "Orbit Analytics", "role": "PM"},
                    {"company": "Harbor Tools", "role": "Analyst"},
                ],
            }
        ),
        encoding="utf-8",
    )

    facts = load_expected_profile_facts(run_dir=run, profile_dir=tmp_path / "missing-profile")

    assert facts.name == "Riley Candidate"
    assert facts.companies == ("Orbit Analytics", "Harbor Tools")


def test_absent_profile_returns_empty_facts(tmp_path: Path):
    facts = load_expected_profile_facts(run_dir=tmp_path / "missing-run", profile_dir=tmp_path / "missing-profile")

    assert facts.name == ""
    assert facts.companies == ()


def test_malformed_yaml_degrades_to_empty_facts(tmp_path: Path):
    run = tmp_path / "run"
    inputs = run / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "career_signals.yaml").write_text("metadata: [unterminated", encoding="utf-8")

    facts = load_expected_profile_facts(run_dir=run, profile_dir=tmp_path / "missing-profile")

    assert facts.name == ""
    assert facts.companies == ()


def test_jsonl_loader_skips_bad_rows(monkeypatch, tmp_path: Path):
    home = tmp_path / "home"
    profile = home / "profile"
    profile.mkdir(parents=True)
    monkeypatch.setenv("LINKRIGHT_HOME", str(home))
    (profile / "nuggets.jsonl").write_text(
        "\n".join(
            [
                "{bad json",
                json.dumps(["not", "a", "mapping"]),
                json.dumps({"type": "work_experience", "company": "Northstar Labs"}),
            ]
        ),
        encoding="utf-8",
    )

    facts = load_expected_profile_facts()

    assert facts.companies == ("Northstar Labs",)


def test_matching_helpers_ignore_spacing_and_case():
    assert value_in_text("Worked at Northstar Labs on growth", "northstar labs")
    assert missing_expected_values(["Northstar Labs", "Vector Works"], ["northstar labs"]) == ["Vector Works"]
