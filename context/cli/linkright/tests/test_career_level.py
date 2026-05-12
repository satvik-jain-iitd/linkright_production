from linkright.resume.orchestrator import _bucket_from_years


def test_fresher():
    assert _bucket_from_years(0.0) == "fresher"


def test_entry_sub_one_year():
    # 0.5yr is entry (not fresher) — explicit boundary for sub-1yr candidates
    assert _bucket_from_years(0.5) == "entry"


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


def test_bucket_invariant_post_retry():
    # Invariant: re-applying _bucket_from_years(same total_years) always returns
    # the same level regardless of how many times called — used to verify the
    # low-reqs retry path re-enforcement in step_07.
    total_years = 3.5
    first = _bucket_from_years(total_years)
    second = _bucket_from_years(total_years)
    assert first == second == "mid"
