from linkright.resume.orchestrator import _bucket_from_years


def test_fresher():
    assert _bucket_from_years(0.0) == "fresher"


def test_entry():
    assert _bucket_from_years(2.3) == "entry"


def test_mid_boundary():
    assert _bucket_from_years(5.0) == "mid"


def test_senior():
    assert _bucket_from_years(7.0) == "senior"


def test_executive():
    assert _bucket_from_years(10.5) == "executive"


def test_deterministic_same_input():
    results = {_bucket_from_years(4.2) for _ in range(3)}
    assert len(results) == 1
