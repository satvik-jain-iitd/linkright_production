import json
import pathlib


def test_log_guard_decision_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    from linkright.resume.orchestrator import _log_guard_decision
    _log_guard_decision("Led 50-person team", "managed 30 people", "accepted", "run_001")
    log_file = tmp_path / ".linkright" / "training-data" / "fabrication-guard" / "run_001.jsonl"
    assert log_file.exists()
    row = json.loads(log_file.read_text().strip())
    assert row["decision"] == "accepted"
    assert "bullet" in row and "source" in row and "ts" in row


def test_log_never_crashes_on_bad_path(monkeypatch):
    """Instrumentation must never crash the pipeline even when mkdir raises."""
    monkeypatch.setattr(pathlib.Path, "mkdir", lambda *a, **kw: (_ for _ in ()).throw(PermissionError("no write")))
    from linkright.resume.orchestrator import _log_guard_decision
    # Should not raise even when the directory cannot be created
    _log_guard_decision("bullet", "source", "accepted", "run_bad")
