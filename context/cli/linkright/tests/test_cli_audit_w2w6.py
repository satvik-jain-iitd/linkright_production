"""Audit follow-ups — W2 (Oracle retry), W5 (embeddings facade), W6 (batch)."""
import httpx
import pytest

from linkright.llm import oracle
from linkright.resume.lib import embedder


# ── W2: Oracle calls retry transient network errors ──
def test_w2_post_retry_raises_after_network_failures(monkeypatch):
    calls = {"n": 0}

    class _Boom:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k):
            calls["n"] += 1
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(oracle.httpx, "Client", _Boom)
    monkeypatch.setattr(oracle.time, "sleep", lambda s: None)
    with pytest.raises(oracle.OracleUnavailable, match="network error"):
        oracle._post_retry("http://x/y", {}, {}, 1.0, attempts=2)
    assert calls["n"] == 2  # retried, not single-shot


def test_w2_post_retry_succeeds_on_second_attempt(monkeypatch):
    calls = {"n": 0}

    class _Resp:
        status_code = 200

    class _Flaky:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ConnectError("blip")
            return _Resp()

    monkeypatch.setattr(oracle.httpx, "Client", _Flaky)
    monkeypatch.setattr(oracle.time, "sleep", lambda s: None)
    resp = oracle._post_retry("http://x/y", {}, {}, 1.0, attempts=2)
    assert resp.status_code == 200 and calls["n"] == 2


def test_w2_no_retry_on_http_status(monkeypatch):
    """A non-200 status is deterministic — returned as-is, NOT retried."""
    calls = {"n": 0}

    class _Resp:
        status_code = 503

    class _C:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k):
            calls["n"] += 1
            return _Resp()

    monkeypatch.setattr(oracle.httpx, "Client", _C)
    resp = oracle._post_retry("http://x/y", {}, {}, 1.0, attempts=2)
    assert resp.status_code == 503 and calls["n"] == 1


# ── W5: stable embeddings facade ──
def test_w5_embeddings_facade_importable():
    from linkright.embeddings import embed, embed_batch
    assert callable(embed) and callable(embed_batch)


# ── W6: embed_batch preserves count + order, handles empty ──
def test_w6_embed_batch_matches_count():
    res = embedder.embed_batch(["alpha", "beta", "gamma"])
    assert len(res) == 3
    vec, meta = res[0]
    assert vec and isinstance(vec, list)


def test_w6_embed_batch_empty():
    assert embedder.embed_batch([]) == []
