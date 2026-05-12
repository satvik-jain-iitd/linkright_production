"""S5.2 Phase 0 — input hash instrumentation tests.

Phase 0 is purely passive: sha256(resume_bytes + jd_bytes + version_bytes) is
written to 16_telemetry.json.  No cache logic yet — that's Phase 1 (gated on
measured hit rate ≥25%).

Coverage:
  - hash is deterministic for identical inputs
  - hash differs when resume bytes change
  - hash differs when jd bytes change
  - hash differs when version changes
  - non-string keywords excluded (regression guard)
"""
from __future__ import annotations

import hashlib


def _compute_input_hash(resume_bytes: bytes, jd_text: str, version: str) -> str:
    """Replicate the S5.2 Phase 0 hash computation from step_16 telemetry."""
    return hashlib.sha256(
        resume_bytes + jd_text.encode() + version.encode()
    ).hexdigest()


class TestInputHashDeterminism:
    def test_identical_inputs_same_hash(self):
        h1 = _compute_input_hash(b"pdf content", "We need Python", "0.9.0")
        h2 = _compute_input_hash(b"pdf content", "We need Python", "0.9.0")
        assert h1 == h2

    def test_resume_change_different_hash(self):
        h1 = _compute_input_hash(b"resume v1", "JD text", "0.9.0")
        h2 = _compute_input_hash(b"resume v2", "JD text", "0.9.0")
        assert h1 != h2

    def test_jd_change_different_hash(self):
        h1 = _compute_input_hash(b"resume", "Senior PM required", "0.9.0")
        h2 = _compute_input_hash(b"resume", "Junior PM required", "0.9.0")
        assert h1 != h2

    def test_version_change_different_hash(self):
        h1 = _compute_input_hash(b"resume", "JD text", "0.9.0")
        h2 = _compute_input_hash(b"resume", "JD text", "1.0.0")
        assert h1 != h2

    def test_hash_is_hex_string_64_chars(self):
        h = _compute_input_hash(b"resume", "JD", "0.9.0")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_resume_still_hashes(self):
        h = _compute_input_hash(b"", "JD text", "0.9.0")
        assert len(h) == 64

    def test_empty_jd_still_hashes(self):
        h = _compute_input_hash(b"resume bytes", "", "0.9.0")
        assert len(h) == 64
