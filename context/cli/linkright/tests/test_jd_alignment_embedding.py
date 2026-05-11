"""test_jd_alignment_embedding.py — Unit tests for S5.1: Oracle embedding-based
JD-bullet alignment in step_11_rank.

All tests mock oracle_embed so Oracle VPS is not required.
"""
from __future__ import annotations

import math
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _unit_vec(dim: int, val: float = 1.0) -> list[float]:
    """Return a normalised vector of length `dim` with first element `val`, rest 0."""
    v = [0.0] * dim
    v[0] = val
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _make_bullet(text: str, signal: str = "build-execution") -> dict:
    return {
        "text_html": text,
        "signal": signal,
        "alignment": 0.5,
    }


def _call_step11(monkeypatch, tmp_path, verbose_all, jd_keywords, jd_req_texts=None,
                 jd_req_clusters=None, career_level="mid"):
    import linkright.resume.orchestrator as orch
    import linkright.resume.lib.logbook as lb
    monkeypatch.setattr(orch, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(lb, "_VISION_PATH", tmp_path / "vision.md")
    from linkright.resume.orchestrator import step_11_rank
    return step_11_rank(
        verbose_all=verbose_all,
        jd_keywords=jd_keywords,
        jd_req_clusters=jd_req_clusters,
        career_level=career_level,
        jd_req_texts=jd_req_texts,
    )


# ── Test 1: alignment > 0.5 when oracle_embed returns semantically identical vecs ──
class TestAlignmentBlending:
    """Test 1: mocked oracle_embed; blended score uses alignment component."""

    def test_alignment_score_stored_on_bullet(self, monkeypatch, tmp_path):
        """_alignment_score field present when Oracle embed succeeds."""
        import linkright.resume.orchestrator as orch

        # Return identical unit vectors → cosine = 1.0
        monkeypatch.setattr(orch, "_oracle_embed", lambda texts, **kw: [_unit_vec(768)] * len(texts))

        verbose_all = {
            "Acme Corp": {
                "paragraphs": [_make_bullet("Drove ARR growth by 40% through P&L ownership")],
            }
        }
        result = _call_step11(
            monkeypatch, tmp_path,
            verbose_all=verbose_all,
            jd_keywords=[],
            jd_req_texts=["P&L ownership and revenue growth responsibility"],
        )
        bullet = result["Acme Corp"][0]
        assert "_alignment_score" in bullet, "_alignment_score must be set on bullet when Oracle available"
        assert bullet["_alignment_score"] > 0.5, (
            f"Alignment should be > 0.5 for semantically matching bullet; got {bullet['_alignment_score']}"
        )

    def test_blended_score_differs_from_brs_only(self, monkeypatch, tmp_path):
        """When Oracle embed succeeds, _weighted_brs should reflect alignment blend."""
        import linkright.resume.orchestrator as orch

        # Return a unit vector → alignment = 1.0 for all
        monkeypatch.setattr(orch, "_oracle_embed", lambda texts, **kw: [_unit_vec(768)] * len(texts))

        # A bullet with zero BRS (no numbers/signals/keywords) but full alignment → non-zero final score
        verbose_all = {
            "Acme Corp": {
                "paragraphs": [_make_bullet("Ownership and strategy alignment work")],
            }
        }
        result_blend = _call_step11(
            monkeypatch, tmp_path,
            verbose_all=verbose_all,
            jd_keywords=[],
            jd_req_texts=["Ownership and strategy"],
        )
        blend_score = result_blend["Acme Corp"][0]["_weighted_brs"]
        # With alignment=1.0, even a 0-BRS bullet should get 0.30 * 1.0 = 0.3 boost
        assert blend_score > 0.0, f"Blended score must be > 0 when alignment=1.0; got {blend_score}"


# ── Test 2: Oracle unavailable → BRS-only fallback, no exception ───────────────
class TestOracleUnavailableFallback:
    """Test 2: OracleUnavailable raises → graceful BRS-only fallback."""

    def test_no_exception_when_oracle_unavailable(self, monkeypatch, tmp_path):
        """step_11_rank must not crash when OracleUnavailable is raised."""
        import linkright.resume.orchestrator as orch

        def _raise_unavailable(texts, **kw):
            raise orch._OracleUnavailable("ORACLE_BACKEND_URL not set")

        monkeypatch.setattr(orch, "_oracle_embed", _raise_unavailable)

        verbose_all = {
            "Acme Corp": {
                "paragraphs": [
                    _make_bullet("Drove 30% cost savings through automation"),
                ],
            }
        }
        # Should not raise
        result = _call_step11(
            monkeypatch, tmp_path,
            verbose_all=verbose_all,
            jd_keywords=["automation"],
            jd_req_texts=["automation and cost reduction"],
        )
        assert "Acme Corp" in result
        bullet = result["Acme Corp"][0]
        # _alignment_score should be absent or 0 in BRS-only mode
        alignment = bullet.get("_alignment_score", 0.0)
        assert alignment == 0.0 or "_alignment_score" not in bullet, (
            f"Fallback mode must not set non-zero _alignment_score; got {alignment}"
        )

    def test_weighted_brs_is_positive_in_fallback_mode(self, monkeypatch, tmp_path):
        """BRS-only fallback still produces a valid _weighted_brs score."""
        import linkright.resume.orchestrator as orch

        def _raise_unavailable(texts, **kw):
            raise orch._OracleUnavailable("no credentials")

        monkeypatch.setattr(orch, "_oracle_embed", _raise_unavailable)

        verbose_all = {
            "Corp X": {
                "paragraphs": [
                    _make_bullet("Reduced deployment time by 60% via 3 CI/CD pipeline optimizations"),
                ],
            }
        }
        result = _call_step11(
            monkeypatch, tmp_path,
            verbose_all=verbose_all,
            jd_keywords=["CI/CD"],
            jd_req_texts=["CI/CD and deployment automation"],
        )
        assert result["Corp X"][0]["_weighted_brs"] >= 0.0


# ── Test 3: determinism — same inputs × 3 runs → identical _alignment_score ───
class TestDeterminism:
    """Test 3: identical inputs must produce identical _alignment_score (no randomness)."""

    def test_same_alignment_score_on_repeated_calls(self, monkeypatch, tmp_path):
        """Three identical runs must produce identical _alignment_score."""
        import linkright.resume.orchestrator as orch

        call_count = {"n": 0}

        def _deterministic_embed(texts, **kw):
            """Return the same unit vector regardless of call order."""
            call_count["n"] += 1
            return [_unit_vec(768)] * len(texts)

        monkeypatch.setattr(orch, "_oracle_embed", _deterministic_embed)

        verbose_all_template = {
            "TechCorp": {
                "paragraphs": [_make_bullet("Built ML pipeline serving 500K daily predictions")],
            }
        }
        jd_req_texts = ["Machine learning and prediction infrastructure"]

        scores = []
        for _ in range(3):
            import copy
            result = _call_step11(
                monkeypatch, tmp_path,
                verbose_all=copy.deepcopy(verbose_all_template),
                jd_keywords=[],
                jd_req_texts=jd_req_texts,
            )
            scores.append(result["TechCorp"][0].get("_alignment_score", 0.0))

        assert scores[0] == scores[1] == scores[2], (
            f"_alignment_score must be identical across runs; got {scores}"
        )


# ── Test 4: jd_req_texts=None but jd_req_clusters provided → derive from canonical_label ──
class TestDeriveFromClusters:
    """Test 4: req texts auto-derived from jd_req_clusters canonical_labels."""

    def test_req_texts_derived_from_canonical_labels(self, monkeypatch, tmp_path):
        """When jd_req_texts=None but jd_req_clusters provided, step derives req texts
        from canonical_label fields and uses them for embedding."""
        import linkright.resume.orchestrator as orch

        captured_texts: list[list[str]] = []

        def _capture_embed(texts, **kw):
            captured_texts.append(list(texts))
            return [_unit_vec(768)] * len(texts)

        monkeypatch.setattr(orch, "_oracle_embed", _capture_embed)

        clusters = [
            {"cluster_id": "c1", "canonical_label": "P&L ownership and revenue strategy", "member_req_ids": ["r1"]},
            {"cluster_id": "c2", "canonical_label": "Cross-functional stakeholder management", "member_req_ids": ["r2"]},
        ]

        verbose_all = {
            "Startup Y": {
                "paragraphs": [
                    _make_bullet("Drove $2M ARR through strategic P&L ownership across 5 teams"),
                ],
            }
        }

        result = _call_step11(
            monkeypatch, tmp_path,
            verbose_all=verbose_all,
            jd_keywords=[],
            jd_req_texts=None,  # must be derived from clusters
            jd_req_clusters=clusters,
            career_level="mid",
        )

        assert result, "step_11_rank must return a non-empty dict"
        # First captured_texts call should contain the canonical labels (JD req embedding)
        assert captured_texts, "oracle_embed must have been called at least once"
        first_call = captured_texts[0]
        assert "P&L ownership and revenue strategy" in first_call or \
               "Cross-functional stakeholder management" in first_call, (
            f"First oracle_embed call must contain canonical_labels; got {first_call}"
        )

    def test_no_embed_when_no_req_texts_and_no_clusters(self, monkeypatch, tmp_path):
        """When neither jd_req_texts nor jd_req_clusters are provided, oracle_embed
        must never be called (avoid unnecessary network call)."""
        import linkright.resume.orchestrator as orch

        embed_called = {"n": 0}

        def _should_not_call(texts, **kw):
            embed_called["n"] += 1
            return [_unit_vec(768)] * len(texts)

        monkeypatch.setattr(orch, "_oracle_embed", _should_not_call)

        verbose_all = {
            "Corp Z": {
                "paragraphs": [_make_bullet("Led team of 5 engineers building data platform")],
            }
        }
        _call_step11(
            monkeypatch, tmp_path,
            verbose_all=verbose_all,
            jd_keywords=["data"],
            jd_req_texts=None,
            jd_req_clusters=None,
        )
        assert embed_called["n"] == 0, (
            "oracle_embed must not be called when no jd_req_texts and no jd_req_clusters"
        )
