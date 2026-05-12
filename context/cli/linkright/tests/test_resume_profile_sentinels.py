from __future__ import annotations

from pathlib import Path

import yaml

from linkright.resume import orchestrator


def _configure_run(monkeypatch, tmp_path: Path) -> list[tuple[str, str, str, str]]:
    run = tmp_path / "run"
    (run / "inputs").mkdir(parents=True)
    (run / "artifacts").mkdir()
    (run / "logs").mkdir()
    (run / "inputs" / "career_signals.yaml").write_text(
        yaml.safe_dump(
            {
                "metadata": {"user": "Morgan Tester"},
                "signals": [
                    {"company": "Northstar Labs", "role": "Lead"},
                    {"company": "Vector Works", "role": "Analyst"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(orchestrator, "RUN_DIR", run)
    monkeypatch.setattr(orchestrator, "ARTIFACTS", run / "artifacts")
    monkeypatch.setattr(orchestrator, "INPUTS", run / "inputs")
    monkeypatch.setattr(orchestrator, "LOG_PATH", run / "logs" / "pipeline.log")
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "missing-home"))
    captured: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(orchestrator.logbook, "append", lambda *args, **kwargs: captured.append(args))
    monkeypatch.setattr(orchestrator, "log", lambda _msg: None)
    return captured


def test_step_01_flags_missing_profile_derived_company(monkeypatch, tmp_path: Path):
    captured = _configure_run(monkeypatch, tmp_path)
    markdown = """## SKILLS
Python, SQL

## EXPERIENCE
### Northstar Labs | Lead | 2024 | Present
- Built launch analytics
- Improved onboarding
"""
    monkeypatch.setattr(orchestrator.llm, "tier_chat", lambda **_kwargs: (markdown, {"provider": "test"}))

    parsed = orchestrator.step_01_parse_resume("Morgan Tester worked at Northstar Labs and Vector Works.")

    assert [e["company"] for e in parsed["experiences"]] == ["Northstar Labs"]
    assert any("Vector Works" in str(args) for args in captured)


def test_step_02_flags_missing_profile_derived_nugget_company(monkeypatch, tmp_path: Path):
    captured = _configure_run(monkeypatch, tmp_path)
    md_text = """## nugget
type: work_experience
company: Northstar Labs
role: Lead
importance: P0
answer: Built launch analytics that improved activation by 20%.

## nugget
type: work_experience
company: Northstar Labs
role: Lead
importance: P1
answer: Reduced manual reporting by automating executive dashboards.
"""
    monkeypatch.setattr(orchestrator.llm, "tier_chat", lambda **_kwargs: (md_text, {"provider": "test"}))

    nuggets = orchestrator.step_02_extract_nuggets(
        "Morgan Tester worked at Northstar Labs and Vector Works.",
        {"experiences": [{"company": "Northstar Labs"}, {"company": "Vector Works"}]},
    )

    assert len(nuggets) == 2
    assert any("expected companies missing from nugget attribution" in str(args) for args in captured)


def test_step_02_skips_company_sentinel_when_expected_facts_unavailable(monkeypatch, tmp_path: Path):
    run = tmp_path / "run"
    (run / "inputs").mkdir(parents=True)
    (run / "artifacts").mkdir()
    (run / "logs").mkdir()
    monkeypatch.setattr(orchestrator, "RUN_DIR", run)
    monkeypatch.setattr(orchestrator, "ARTIFACTS", run / "artifacts")
    monkeypatch.setattr(orchestrator, "INPUTS", run / "inputs")
    monkeypatch.setattr(orchestrator, "LOG_PATH", run / "logs" / "pipeline.log")
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "missing-home"))
    captured: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(orchestrator.logbook, "append", lambda *args, **kwargs: captured.append(args))
    monkeypatch.setattr(orchestrator, "log", lambda _msg: None)
    md_text = """## nugget
type: work_experience
company: Northstar Labs
role: Lead
importance: P0
answer: Built launch analytics that improved activation by 20%.
"""
    monkeypatch.setattr(orchestrator.llm, "tier_chat", lambda **_kwargs: (md_text, {"provider": "test"}))

    nuggets = orchestrator.step_02_extract_nuggets(
        "Candidate worked at Northstar Labs and Vector Works.",
        {"experiences": [{"company": "Northstar Labs"}, {"company": "Vector Works"}]},
    )

    assert len(nuggets) == 1
    assert not any("expected companies missing from nugget attribution" in str(args) for args in captured)


def test_deep_rca_raw_check_flags_missing_expected_company(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "missing-home"))
    from harness.resume.deep_rca import check_00_raw

    run = tmp_path / "run"
    (run / "inputs").mkdir(parents=True)
    (run / "artifacts").mkdir()
    (run / "inputs" / "career_signals.yaml").write_text(
        yaml.safe_dump({"signals": [{"company": "Northstar Labs"}, {"company": "Vector Works"}]}),
        encoding="utf-8",
    )
    raw_text = "Morgan Tester worked at Northstar Labs. " + ("Delivered measurable impact. " * 90)
    (run / "artifacts" / "00_resume_raw_text.txt").write_text(raw_text, encoding="utf-8")

    verdict, reason, metrics = check_00_raw(run)

    assert verdict == "❌"
    assert "Vector Works" in reason
    assert metrics["missing_companies"] == ["Vector Works"]
