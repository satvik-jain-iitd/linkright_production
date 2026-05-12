"""Tests for jd_cluster.cluster_requirements (S3.2).

Mock embeddings use 4-D unit vectors to guarantee deterministic cosine values.
Clusters are formed when cosine(a, b) >= threshold (default 0.75).

Vector design:
  "communicate" / "collaborate" / "stakeholder" → near [1,0,0,0]
    cosine between any two ≈ 0.9999 → merges at threshold=0.75
  "Python" / "AWS" → near [0,1,0,0]
    cosine to each other ≈ 0.9999 → merges at threshold=0.75
    cosine to communicate cluster ≈ 0.0 → no merge
  "Spanish" → [0,0,1,0]
    cosine to all others ≈ 0.0 → no merge
"""

from __future__ import annotations

import math
import os

import pytest

from linkright.resume.lib.jd_cluster import cluster_requirements


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unit(v: list[float]) -> list[float]:
    """Return L2-normalised vector (so cosines are exact)."""
    mag = math.sqrt(sum(x * x for x in v))
    return [x / mag for x in v]


# Base vectors (orthogonal)
_COMM  = _unit([0.98, 0.02, 0.00, 0.00])   # "communicate" / "collaborate" / "stakeholder"
_TECH  = _unit([0.02, 0.98, 0.00, 0.00])   # "Python" / "AWS"
_LANG  = _unit([0.00, 0.00, 1.00, 0.00])   # "Spanish fluency"

# Slightly perturbed copies of _COMM to simulate real near-duplicate embeddings
_COLLAB = _unit([0.97, 0.03, 0.00, 0.00])
_STKH   = _unit([0.96, 0.04, 0.00, 0.00])
_AWS    = _unit([0.03, 0.97, 0.00, 0.00])


# ---------------------------------------------------------------------------
# Test (a) — similar embeddings → 1 cluster
# ---------------------------------------------------------------------------

class TestSimilarRequirementsMerge:
    """communicate + collaborate + stakeholder alignment → 1 cluster."""

    def _reqs(self) -> list[dict]:
        return [
            {"id": "r1", "text": "communicate effectively with stakeholders", "emb": _COMM},
            {"id": "r2", "text": "collaborate across teams",                  "emb": _COLLAB},
            {"id": "r3", "text": "stakeholder alignment",                     "emb": _STKH},
        ]

    def test_produces_one_cluster(self):
        clusters = cluster_requirements(self._reqs(), threshold=0.75)
        assert len(clusters) == 1

    def test_cluster_contains_all_members(self):
        clusters = cluster_requirements(self._reqs(), threshold=0.75)
        member_ids = set(clusters[0]["member_req_ids"])
        assert member_ids == {"r1", "r2", "r3"}

    def test_cluster_has_required_keys(self):
        clusters = cluster_requirements(self._reqs(), threshold=0.75)
        cl = clusters[0]
        assert "cluster_id" in cl
        assert "member_req_ids" in cl
        assert "canonical_label" in cl
        assert "centroid_embedding" in cl

    def test_canonical_label_is_one_of_member_texts(self):
        reqs = self._reqs()
        member_texts = {r["text"] for r in reqs}
        clusters = cluster_requirements(reqs, threshold=0.75)
        assert clusters[0]["canonical_label"] in member_texts

    def test_centroid_embedding_has_correct_dim(self):
        clusters = cluster_requirements(self._reqs(), threshold=0.75)
        assert len(clusters[0]["centroid_embedding"]) == 4


# ---------------------------------------------------------------------------
# Test (b) — dissimilar embeddings → 3 clusters
# ---------------------------------------------------------------------------

class TestDissimilarRequirementsStaySeparate:
    """Python + Spanish fluency + AWS → 3 clusters (Python+AWS merge → 2, actually
    we separate all 3 by design: Python cluster, AWS cluster (merged with Python
    since cos≈0.9), Spanish cluster stays alone).

    Wait — Python and AWS are both near [0,1,0,0] so they DO merge.
    Let us test with truly orthogonal vectors for all three.
    """

    def _reqs(self) -> list[dict]:
        # Use fully orthogonal vectors so nothing merges
        return [
            {"id": "r1", "text": "Python programming",      "emb": _unit([1,0,0,0])},
            {"id": "r2", "text": "Spanish fluency",         "emb": _unit([0,1,0,0])},
            {"id": "r3", "text": "AWS infrastructure",      "emb": _unit([0,0,1,0])},
        ]

    def test_produces_three_clusters(self):
        clusters = cluster_requirements(self._reqs(), threshold=0.75)
        assert len(clusters) == 3

    def test_each_cluster_is_singleton(self):
        clusters = cluster_requirements(self._reqs(), threshold=0.75)
        for cl in clusters:
            assert len(cl["member_req_ids"]) == 1

    def test_all_req_ids_present(self):
        clusters = cluster_requirements(self._reqs(), threshold=0.75)
        all_ids = {rid for cl in clusters for rid in cl["member_req_ids"]}
        assert all_ids == {"r1", "r2", "r3"}


# ---------------------------------------------------------------------------
# Test (c) — threshold=1.0 → every req is its own cluster
# ---------------------------------------------------------------------------

class TestThresholdOnePointZero:
    """At threshold=1.0 no two reqs ever merge, even identical-looking embeddings."""

    def _reqs(self) -> list[dict]:
        return [
            {"id": "r1", "text": "communicate", "emb": _COMM},
            {"id": "r2", "text": "collaborate",  "emb": _COLLAB},
            {"id": "r3", "text": "stakeholder",  "emb": _STKH},
        ]

    def test_every_req_own_cluster_via_arg(self):
        clusters = cluster_requirements(self._reqs(), threshold=1.0)
        assert len(clusters) == 3

    def test_every_req_own_cluster_via_env_var(self, monkeypatch):
        monkeypatch.setenv("LR_CLUSTER_THRESHOLD", "1.0")
        # Pass threshold=None so it reads the env var
        clusters = cluster_requirements(self._reqs(), threshold=None)
        assert len(clusters) == 3

    def test_default_env_var_is_0_75(self, monkeypatch):
        """Default (no env var) → similar embeddings merge."""
        monkeypatch.delenv("LR_CLUSTER_THRESHOLD", raising=False)
        # communicate / collaborate / stakeholder all near [1,0,0,0] → should merge
        clusters = cluster_requirements(self._reqs(), threshold=None)
        assert len(clusters) == 1


# ---------------------------------------------------------------------------
# Test (d) — integration: parsed_p12 gets jd_requirement_clusters
# ---------------------------------------------------------------------------

class TestParsedP12Integration:
    """Simulates the orchestrator's clustering pass writing to parsed_p12."""

    def test_parsed_p12_field_set(self):
        """After cluster_requirements runs, parsed_p12['jd_requirement_clusters']
        should contain the cluster list."""
        reqs = [
            {"id": "r1", "text": "communicate effectively", "emb": _COMM},
            {"id": "r2", "text": "collaborate across teams", "emb": _COLLAB},
            {"id": "r3", "text": "Python programming",      "emb": _unit([0,1,0,0])},
        ]
        parsed_p12: dict = {}

        # Replicate the orchestrator's 2-line pass:
        _req_clusters = cluster_requirements(reqs)
        parsed_p12["jd_requirement_clusters"] = _req_clusters

        assert "jd_requirement_clusters" in parsed_p12
        clusters = parsed_p12["jd_requirement_clusters"]
        # communicate + collaborate should merge → 2 clusters total
        assert len(clusters) == 2

    def test_field_is_list_of_dicts(self):
        reqs = [
            {"id": "r1", "text": "stakeholder management", "emb": _STKH},
        ]
        parsed_p12: dict = {}
        parsed_p12["jd_requirement_clusters"] = cluster_requirements(reqs)
        assert isinstance(parsed_p12["jd_requirement_clusters"], list)
        assert isinstance(parsed_p12["jd_requirement_clusters"][0], dict)

    def test_empty_reqs_gives_empty_clusters(self):
        parsed_p12: dict = {}
        parsed_p12["jd_requirement_clusters"] = cluster_requirements([])
        assert parsed_p12["jd_requirement_clusters"] == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_single_req(self):
        reqs = [{"id": "r1", "text": "leadership", "emb": _unit([1,0,0,0])}]
        clusters = cluster_requirements(reqs)
        assert len(clusters) == 1
        assert clusters[0]["member_req_ids"] == ["r1"]

    def test_req_without_embedding_becomes_singleton(self):
        """Reqs with no emb field must not crash and must appear in output."""
        reqs = [
            {"id": "r1", "text": "Python",    "emb": _unit([1,0,0,0])},
            {"id": "r2", "text": "no embed"},  # no emb key
        ]
        clusters = cluster_requirements(reqs, threshold=0.75)
        all_ids = {rid for cl in clusters for rid in cl["member_req_ids"]}
        assert "r2" in all_ids

    def test_cluster_id_format(self):
        reqs = [
            {"id": "r1", "text": "a", "emb": _unit([1,0,0,0])},
            {"id": "r2", "text": "b", "emb": _unit([0,1,0,0])},
        ]
        clusters = cluster_requirements(reqs)
        ids = [cl["cluster_id"] for cl in clusters]
        assert all(cid.startswith("c") for cid in ids)


# ---------------------------------------------------------------------------
# Test (e) — step_11_rank: same-cluster dedup + cross-company independence
# ---------------------------------------------------------------------------

class TestStep11RankClusterDedup:
    """Integration tests for the cluster-aware BRS in step_11_rank.

    Uses minimal verbose_all dicts with 2 companies / 2 bullets each.
    Mock embeddings are not needed here — we test BRS logic only.
    Logbook and ARTIFACTS are monkeypatched so the test has no I/O side effects.
    """

    @staticmethod
    def _setup(monkeypatch, tmp_path):
        """Wire up orchestrator paths + silence logbook writes."""
        from linkright.resume import orchestrator
        arts = tmp_path / "artifacts"
        arts.mkdir()
        monkeypatch.setattr(orchestrator, "ARTIFACTS", arts)
        monkeypatch.setattr(orchestrator.logbook, "append", lambda *a, **kw: None)
        monkeypatch.setattr(orchestrator.logbook, "set_path", lambda *a, **kw: None)
        return orchestrator

    @staticmethod
    def _bullet(text: str) -> dict:
        return {"text_html": text, "nugget_ids": []}

    def test_same_cluster_counted_once(self, monkeypatch, tmp_path):
        """Two bullets both mentioning 'communication' (same cluster) should
        yield a score gap: the first bullet gets the cluster BRS credit,
        the second does NOT (covered_clusters anti-stuffing)."""
        orch = self._setup(monkeypatch, tmp_path)

        clusters = [
            {
                "cluster_id": "c1",
                "canonical_label": "communication skills",
                "member_req_ids": [],
                "centroid_embedding": [1.0, 0.0, 0.0, 0.0],
            }
        ]
        # Both bullets reference 'communication' (>=4 chars → matches cluster c1)
        verbose_all = {
            "AcmeCorp": {
                "paragraphs": [
                    self._bullet("Led communication across 12 stakeholders"),
                    self._bullet("Improved communication for 3 teams"),
                ]
            }
        }

        ranked = orch.step_11_rank(
            verbose_all, jd_keywords=[], jd_req_clusters=clusters
        )

        paras = ranked["AcmeCorp"]
        # First bullet (higher score) should have scored the cluster
        # Second bullet cannot claim c1 again — its cluster contribution is 0
        scores = [p["_brs"] for p in paras]
        # gap = one cluster kw_hit credit not awarded to second bullet (dedup).
        # Formula: kw_hits * 0.05 * len_bonus. Both bullets <150 chars → len_bonus=0.5.
        # Bullet 1: (nums=1)*0.15 + (kw_hits=1)*0.05 all ×0.5 = 0.100
        # Bullet 2: (nums=1)*0.15 + (kw_hits=0)*0.05 all ×0.5 = 0.075  (c1 deduped)
        # Expected gap = 0.025 = 1 cluster hit × 0.05 × len_bonus 0.5
        assert scores[0] - scores[1] == pytest.approx(0.025, abs=1e-6), (
            f"Score gap {scores[0] - scores[1]:.6f} != 0.025 — dedup or scoring broken"
        )

    def test_cross_company_cluster_resets(self, monkeypatch, tmp_path):
        """covered_clusters must reset between companies so Company B's bullet
        can still score cluster c1 even if Company A already covered it."""
        orch = self._setup(monkeypatch, tmp_path)

        clusters = [
            {
                "cluster_id": "c1",
                "canonical_label": "stakeholder alignment skills",
                "member_req_ids": [],
                "centroid_embedding": [1.0, 0.0, 0.0, 0.0],
            }
        ]
        verbose_all = {
            "CompanyA": {
                "paragraphs": [
                    self._bullet("Led stakeholder alignment across 5 regions"),
                ]
            },
            "CompanyB": {
                "paragraphs": [
                    self._bullet("Drove stakeholder alignment for product roadmap"),
                ]
            },
        }

        ranked = orch.step_11_rank(
            verbose_all, jd_keywords=[], jd_req_clusters=clusters
        )

        score_a = ranked["CompanyA"][0]["_brs"]
        score_b = ranked["CompanyB"][0]["_brs"]
        # Both bullets reference 'stakeholder' + 'alignment' (both >=4 chars → c1)
        # covered_clusters resets per company, so both must receive cluster credit
        assert score_a > 0, "CompanyA bullet did not score cluster c1"
        assert score_b > 0, "CompanyB bullet did not score cluster c1 — cross-company reset broken"
