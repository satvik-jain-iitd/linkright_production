"""Offline tests for the content harness, gates, grounding, and the loop.

No network and no LLM calls. The loop's draft and revise steps are injected, so
these tests run deterministically in CI.
"""
from __future__ import annotations

from linkright.content import gates
from linkright.content.grounding import retrieve_grounding
from linkright.content import grounding as grounding_mod
from linkright.content.loop import run_content_loop


VOICE = {
    "tone_adjectives": ["direct", "plain"],
    "connectives": ["turns out"],
    "avoid_list": ["champion"],
    "hook_style": "hard fact",
    "sentence_length_mean": 12,
    "exclamation_ratio": 0.0,
    "question_ratio": 0.0,
}

STYLE = {
    "banned_words": ["utilize", "leverage", "ensure", "robust", "spearhead"],
    "allowed_punctuation_only": True,
    "allowed_punctuation": [",", "."],
    "require_signature": True,
    "signature": "‼️",  # red double exclamation
    "max_sentences_per_paragraph": 2,
    "forbidden_openers": ["excited to share"],
}

BAD = (
    "Excited to share how we utilize leverage to ensure robust growth; really.\n\n"
    "We spearhead change! Do you agree?\n\nChampion ideas win."
)
GOOD = (
    "I cut churn 18 percent on a real B2C funnel‼️\n\n"
    "We found the drop sat in onboarding, not pricing.\n\n"
    "I shipped a fix in one sprint, retention moved the next week.\n\n"
    "Build the boring instrument first, then the clever idea has somewhere to land."
)


def _write_style(tmp_path, monkeypatch):
    import json
    cfg = tmp_path / "content_style.json"
    cfg.write_text(json.dumps(STYLE))
    monkeypatch.setattr(gates, "_STYLE_PATH", cfg)
    return cfg


def test_gates_block_bad_draft(tmp_path, monkeypatch):
    _write_style(tmp_path, monkeypatch)
    res = gates.check_draft(BAD, VOICE)
    assert not res.passed
    joined = " ".join(res.violations)
    assert "utilize" in joined
    assert "spearhead" in joined
    assert "forbidden opener" in joined
    assert "forbidden punctuation" in joined
    assert "signature" in joined


def test_gates_pass_clean_draft(tmp_path, monkeypatch):
    _write_style(tmp_path, monkeypatch)
    res = gates.check_draft(GOOD, VOICE)
    assert res.passed, res.violations


def test_voice_avoid_list_always_banned(tmp_path, monkeypatch):
    # No style file at all, but the voice avoid_list must still be enforced.
    monkeypatch.setattr(gates, "_STYLE_PATH", tmp_path / "missing.json")
    res = gates.check_draft("Real leaders champion the work.", VOICE)
    assert not res.passed
    assert any("champion" in v for v in res.violations)


def test_loop_revises_to_gate_clean(tmp_path, monkeypatch):
    _write_style(tmp_path, monkeypatch)

    def draft_fn(topic, kind, voice, length, evidence=None):
        return BAD

    def llm_fn(system, user):
        return GOOD

    res = run_content_loop(
        "churn turnaround", voice=VOICE, ground=False,
        draft_fn=draft_fn, llm_fn=llm_fn, max_iters=3, threshold=60.0,
    )
    assert res.gate_passed
    assert len(res.iterations) >= 2          # it had to revise
    assert res.iterations[0].gate_passed is False
    assert res.draft == GOOD


def test_grounding_drops_stale_and_caveats_thin(monkeypatch):
    class F:
        def __init__(self, i, t, c, stale=False):
            self.id, self.text, self.confidence, self.stale = i, t, c, stale

    class S:
        def __init__(self, i, name):
            self.id, self.canonical_name, self.label = i, name, name.replace("_", " ")

    facts = [
        F("F1", "Cut Walmart Spark Driver churn 18 percent", 0.9),
        F("F2", "Maybe improved Navii retention a lot", 0.3),
        F("F3", "Owned schema design at Sprinklr", 0.8),
        F("F4", "Stale growth claim", 0.9, stale=True),
    ]
    signals = [S("S1", "growth_experimentation"), S("S2", "systems_thinking")]

    monkeypatch.setattr(grounding_mod.v2_store, "load_facts", lambda d=None: facts)
    monkeypatch.setattr(grounding_mod.v2_store, "load_signals", lambda d=None: signals)
    monkeypatch.setattr(grounding_mod, "_embed_query", lambda t: None)  # force keyword

    gr = retrieve_grounding("growth and retention churn", k_facts=5, k_signals=3)
    ids = [h.id for h in gr.facts]
    assert gr.mode == "keyword"
    assert "F4" not in ids                      # stale dropped
    assert any(h.id == "F2" and h.caveat for h in gr.facts)  # thin fact caveated
    assert "S1" in [h.id for h in gr.signals]   # relevant signal surfaced
