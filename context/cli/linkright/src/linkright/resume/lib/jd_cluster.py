"""JD requirement clustering via cosine similarity.

Groups semantically-related JD requirements so that step_11 can score bullets
against clusters instead of individual requirements — eliminating keyword-stuffing
and reducing redundant LLM penalty for semantically-equivalent reqs.

Public API
----------
cluster_requirements(reqs, threshold=0.75) -> list[dict]

Each returned cluster dict::

    {
        "cluster_id": "c0",
        "member_req_ids": ["r1", "r3", "r4"],
        "canonical_label": "communicate effectively",   # most-central member text
        "centroid_embedding": [0.1, 0.2, ...]           # mean of member embeddings
    }

At threshold=1.0 every requirement becomes its own singleton cluster
(backward-compatible mode).
"""

from __future__ import annotations

import math
import os
from typing import Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cosine(a: list[float], b: list[float]) -> float:
    """Pure cosine similarity (no external dependency)."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na * nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _mean_vector(vecs: list[list[float]]) -> list[float]:
    """Element-wise mean of a list of equal-length vectors."""
    if not vecs:
        return []
    dim = len(vecs[0])
    result = [0.0] * dim
    for v in vecs:
        for i, x in enumerate(v):
            result[i] += x
    n = len(vecs)
    return [x / n for x in result]


def _most_central(embs: list[Optional[list[float]]], texts: list[str]) -> str:
    """Return the text of the member with highest average cosine to all others.

    Falls back to texts[0] if embeddings are unavailable or there is only one
    member.
    """
    valid: list[tuple[int, list[float]]] = [
        (i, e) for i, e in enumerate(embs) if e
    ]
    if len(valid) <= 1:
        return texts[0] if texts else ""

    best_idx = 0
    best_avg = -1.0
    for i, (idx_i, emb_i) in enumerate(valid):
        sims = [
            _cosine(emb_i, emb_j)
            for j, (idx_j, emb_j) in enumerate(valid)
            if j != i
        ]
        avg = sum(sims) / len(sims) if sims else 0.0
        if avg > best_avg:
            best_avg = avg
            best_idx = idx_i

    return texts[best_idx] if best_idx < len(texts) else texts[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cluster_requirements(
    reqs: list[dict],
    threshold: float | None = None,
) -> list[dict]:
    """Group JD requirements by cosine similarity into clusters.

    Parameters
    ----------
    reqs:
        List of requirement dicts. Each must have ``id``, ``text``, and
        optionally ``emb`` (list[float]).  Requirements without embeddings
        are placed in their own singleton cluster.
    threshold:
        Cosine similarity threshold above which two requirements are
        considered semantically equivalent and merged into the same cluster.
        Defaults to ``LR_CLUSTER_THRESHOLD`` env var, then 0.75.
        At 1.0 every req becomes its own cluster (backward-compatible).

    Returns
    -------
    list[dict]
        Cluster list ordered by first-encountered member.  Each cluster::

            {
                "cluster_id": "c0",
                "member_req_ids": ["r1", "r3"],
                "canonical_label": "<most-central member text>",
                "centroid_embedding": [...]   # None if no embeddings
            }
    """
    if threshold is None:
        threshold = float(os.environ.get("LR_CLUSTER_THRESHOLD", "0.75"))

    if not reqs:
        return []

    # Each req starts in its own cluster, represented as an index into `reqs`.
    # We use a Union-Find (disjoint-set) approach for O(N²) pairwise merge.
    n = len(reqs)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    # Pairwise similarity — skip if threshold == 1.0 (all singletons)
    if threshold < 1.0:
        for i in range(n):
            emb_i = reqs[i].get("emb")
            if not emb_i:
                continue
            for j in range(i + 1, n):
                emb_j = reqs[j].get("emb")
                if not emb_j:
                    continue
                if _cosine(emb_i, emb_j) >= threshold:
                    union(i, j)

    # Build clusters from union-find groups
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    # Build output in root-index order (deterministic)
    clusters: list[dict] = []
    for cid, (root, members) in enumerate(sorted(groups.items())):
        member_ids = [reqs[m]["id"] for m in members]
        member_texts = [reqs[m].get("text", "") for m in members]
        member_embs = [reqs[m].get("emb") for m in members]

        label = _most_central(member_embs, member_texts)

        valid_embs = [e for e in member_embs if e]
        centroid = _mean_vector(valid_embs) if valid_embs else None

        clusters.append(
            {
                "cluster_id": f"c{cid}",
                "member_req_ids": member_ids,
                "canonical_label": label,
                "centroid_embedding": centroid,
            }
        )

    return clusters
