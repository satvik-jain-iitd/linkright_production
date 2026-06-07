"""Stable embeddings facade (audit fix W5).

The tiered embedder physically lives in ``resume/lib/embedder.py`` for historical
reasons. Non-resume pillars (content, etc.) should import from HERE rather than
reaching into resume's internal ``lib`` namespace — so the embedder can be moved
or refactored without breaking cross-pillar callers.
"""
from linkright.resume.lib.embedder import embed, embed_batch  # noqa: F401

__all__ = ["embed", "embed_batch"]
