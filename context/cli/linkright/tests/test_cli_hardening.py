"""Audit hardening fixes — B1 (key leak), B3 (thundering-herd), W1 ($0 guard)."""
import time

import pytest

from linkright.llm import direct as d
from linkright.llm import budget as b


# ── B1: Gemini API key must never appear in the request URL ──
def test_b1_gemini_key_not_in_url():
    url = d.GEMINI_URL_TMPL.format(model="gemini-2.0-flash")
    assert "key=" not in url
    assert "?key" not in url
    # template no longer takes a key kwarg — formatting with only model must work
    assert url.endswith(":generateContent")


# ── B3: cooldown must be jittered + honor Retry-After ──
def test_b3_cooldown_jitter_decorrelates():
    d._PROVIDER_COOLDOWNS.clear()
    d._mark_cooling("p")
    t1 = d._PROVIDER_COOLDOWNS["p"]
    d._mark_cooling("p")
    t2 = d._PROVIDER_COOLDOWNS["p"]
    assert t1 != t2  # jittered → effectively never identical


def test_b3_retry_after_never_shorter_than_server():
    d._PROVIDER_COOLDOWNS.clear()
    d._mark_cooling("p", retry_after=10)
    delay = d._PROVIDER_COOLDOWNS["p"] - time.time()
    assert 9.9 <= delay <= 15.1  # jitter UP only: [base, base*1.5] = [10,15]


def test_b3_retry_after_capped_against_hostile_value():
    d._PROVIDER_COOLDOWNS.clear()
    d._mark_cooling("p", retry_after=10_000_000)
    delay = d._PROVIDER_COOLDOWNS["p"] - time.time()
    assert delay <= d._COOLDOWN_SECS * 5 * 1.5 + 1  # capped at 5×cooldown then jittered


def test_b3_retry_after_parser():
    class _R:
        headers = {"Retry-After": "30"}
    assert d._retry_after_secs(_R()) == 30.0

    class _RBad:
        headers = {"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"}
    assert d._retry_after_secs(_RBad()) is None  # HTTP-date form → None


# ── W1: paid provider off by default, budget-capped when on ──
def test_w1_paid_off_by_default(monkeypatch):
    monkeypatch.delenv("LR_ALLOW_PAID", raising=False)
    assert b.paid_allowed() is False
    with pytest.raises(b.BudgetError, match="PAID"):
        b.ensure_paid_allowed("openrouter")


def test_w1_paid_opt_in_under_budget(monkeypatch, tmp_path):
    monkeypatch.setenv("LR_ALLOW_PAID", "1")
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path))
    b.ensure_paid_allowed("openrouter")  # fresh month, zero spent → no raise


def test_w1_over_budget_blocks(monkeypatch, tmp_path):
    monkeypatch.setenv("LR_ALLOW_PAID", "1")
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path))
    monkeypatch.setenv("LR_MONTHLY_BUDGET_CENTS", "10")
    b.record_spend("openrouter", None, 2_000_000, 0)  # default llama rate → 14c > 10c cap
    with pytest.raises(b.BudgetError, match="budget"):
        b.ensure_paid_allowed("openrouter")


def test_w1_estimate_cents_default_model():
    # 1M prompt + 1M completion at llama rate = 7 + 25 = 32 cents
    assert b.estimate_cents("openrouter", None, 1_000_000, 1_000_000) == pytest.approx(32.0)


def test_w1_unknown_model_fails_safe_high():
    # An unknown/overridden model must be priced HIGH so the cap trips early.
    cheap = b.estimate_cents("openrouter", "meta-llama/llama-3.3-70b-instruct", 1_000_000, 0)
    pricey = b.estimate_cents("openrouter", "anthropic/claude-3-opus", 1_000_000, 0)
    assert pricey > cheap * 10  # unknown model over-counted on purpose


# ── B2: session JWT stored in OS keychain, file fallback when none ──
from linkright import auth  # noqa: E402


class _FakeKR:
    def __init__(self):
        self.store = {}
    def set_password(self, s, u, v):
        self.store[(s, u)] = v
    def get_password(self, s, u):
        return self.store.get((s, u))
    def delete_password(self, s, u):
        self.store.pop((s, u), None)


_FUTURE = "2099-01-01T00:00:00Z"


def test_b2_keychain_roundtrip_no_file(monkeypatch, tmp_path):
    fake = _FakeKR()
    monkeypatch.setattr(auth, "_keyring", lambda: fake)
    monkeypatch.setattr(auth, "SESSION_PATH", tmp_path / "session.json")
    auth.save_session({"access_token": "secret123", "expires_at": _FUTURE})
    assert fake.store                                   # stored in keychain
    assert not (tmp_path / "session.json").exists()     # NOT on disk
    assert auth.load_session()["access_token"] == "secret123"
    auth.clear_session()
    assert auth.load_session() is None


def test_b2_file_fallback_when_no_keyring(monkeypatch, tmp_path):
    import stat
    monkeypatch.setattr(auth, "_keyring", lambda: None)
    monkeypatch.setattr(auth, "SESSION_PATH", tmp_path / "session.json")
    auth.save_session({"access_token": "f", "expires_at": _FUTURE})
    sp = tmp_path / "session.json"
    assert sp.exists()
    assert stat.S_IMODE(sp.stat().st_mode) == 0o600    # owner-only
    assert auth.load_session()["access_token"] == "f"


def test_b2_migrates_plaintext_to_keychain(monkeypatch, tmp_path):
    sp = tmp_path / "session.json"
    monkeypatch.setattr(auth, "SESSION_PATH", sp)
    sp.write_text('{"access_token": "old", "expires_at": "%s"}' % _FUTURE)
    fake = _FakeKR()
    monkeypatch.setattr(auth, "_keyring", lambda: fake)
    assert auth.load_session()["access_token"] == "old"   # reads legacy file
    auth.save_session({"access_token": "new", "expires_at": _FUTURE})
    assert not sp.exists()                                 # plaintext removed
    assert fake.get_password("linkright", "session")       # now in keychain


def test_b2_opt_out_uses_file(monkeypatch, tmp_path):
    monkeypatch.setenv("LR_NO_KEYRING", "1")
    monkeypatch.setattr(auth, "SESSION_PATH", tmp_path / "session.json")
    assert auth._keyring() is None
    auth.save_session({"access_token": "x", "expires_at": _FUTURE})
    assert (tmp_path / "session.json").exists()
