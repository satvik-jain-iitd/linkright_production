"""S5.2 Phase 0 — input hash instrumentation tests.

Phase 0 is purely passive: compute_input_hash() writes sha256 to
16_telemetry.json. No cache logic yet — that's Phase 1 (gated on measured
hit rate ≥25%).

Coverage:
  - hash is deterministic for identical inputs
  - hash differs when resume bytes change
  - hash differs when jd bytes change
  - hash differs when version changes
  - length-prefix prevents boundary-collision false matches
  - empty resume/JD edge cases handled
"""
from __future__ import annotations

from linkright.resume.orchestrator import compute_input_hash


class TestInputHashDeterminism:
    def test_identical_inputs_same_hash(self):
        h1 = compute_input_hash(b"pdf content", b"We need Python", "0.9.0")
        h2 = compute_input_hash(b"pdf content", b"We need Python", "0.9.0")
        assert h1 == h2

    def test_resume_change_different_hash(self):
        h1 = compute_input_hash(b"resume v1", b"JD text", "0.9.0")
        h2 = compute_input_hash(b"resume v2", b"JD text", "0.9.0")
        assert h1 != h2

    def test_jd_change_different_hash(self):
        h1 = compute_input_hash(b"resume", b"Senior PM required", "0.9.0")
        h2 = compute_input_hash(b"resume", b"Junior PM required", "0.9.0")
        assert h1 != h2

    def test_version_change_different_hash(self):
        h1 = compute_input_hash(b"resume", b"JD text", "0.9.0")
        h2 = compute_input_hash(b"resume", b"JD text", "1.0.0")
        assert h1 != h2

    def test_hash_is_hex_string_64_chars(self):
        h = compute_input_hash(b"resume", b"JD", "0.9.0")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_resume_still_hashes(self):
        h = compute_input_hash(b"", b"JD text", "0.9.0")
        assert len(h) == 64

    def test_empty_jd_still_hashes(self):
        h = compute_input_hash(b"resume bytes", b"", "0.9.0")
        assert len(h) == 64


class TestBoundaryCollisionPrevention:
    """Length prefix on resume_bytes prevents sha256(A+B) == sha256(A'+B')
    false matches where A ends with bytes that match B's prefix."""

    def test_no_false_match_on_byte_boundary_split(self):
        # Without length prefix: sha256(b'ABC' + b'DEF') == sha256(b'AB' + b'CDEF')
        # With length prefix: these must produce different hashes.
        h1 = compute_input_hash(b"ABC", b"DEF", "0.9.0")
        h2 = compute_input_hash(b"AB", b"CDEF", "0.9.0")
        assert h1 != h2, (
            "Boundary collision detected: different (resume, JD) pairs produced the same hash"
        )

    def test_no_false_match_empty_resume_nonempty_jd(self):
        h1 = compute_input_hash(b"", b"hello world", "0.9.0")
        h2 = compute_input_hash(b"hello", b" world", "0.9.0")
        assert h1 != h2

    def test_no_false_match_on_jd_version_boundary_split(self):
        # JD ending in version-prefix bytes must not collide with a different version.
        # e.g. JD="...Python 3.9." + version="0" vs JD="...Python 3.9.0" + version=""
        h1 = compute_input_hash(b"resume", b"text0", "9.0")
        h2 = compute_input_hash(b"resume", b"text", "09.0")
        assert h1 != h2, (
            "JD/version boundary collision: different (jd, version) pairs produced same hash"
        )
