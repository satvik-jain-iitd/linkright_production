from unittest.mock import MagicMock, patch

from linkright.resume.lib.coherence import enforce_verb_coherence, _leading_verb


def test_leading_verb_extraction():
    assert _leading_verb("Led a team of 5 engineers") == "Led"
    assert _leading_verb("● Managed product roadmap") == "Managed"
    assert _leading_verb("no cap") is None  # lowercase = not a verb start


def test_no_duplicates_unchanged():
    bullets = [
        {"text_html": "Led team of 5", "_weighted_brs": 0.8},
        {"text_html": "Built pipeline", "_weighted_brs": 0.75},
    ]
    result = enforce_verb_coherence(bullets, "Acme", _oracle_ok=True)
    assert result == bullets  # unchanged


def test_duplicate_verb_rephrased():
    # Use realistic bullet lengths (80-120 chars) so the ±50% length heuristic passes.
    orig = "Led migration of 3 legacy services to AWS, reducing infrastructure cost by 30% and cutting deploy time"
    rephrased = "Directed migration of 3 legacy services to AWS, reducing infrastructure cost by 30% and cutting deploy time"
    bullets = [
        {"text_html": "Led team of 5 engineers across two time zones to deliver Q3 roadmap on schedule", "_weighted_brs": 0.8},
        {"text_html": orig, "_weighted_brs": 0.75},
    ]
    mock_resp = MagicMock()
    mock_resp.text = rephrased
    with patch("linkright.resume.lib.coherence.oracle_generate", return_value=mock_resp):
        result = enforce_verb_coherence(bullets, "Acme", _oracle_ok=True)
    assert result[0]["text_html"] == bullets[0]["text_html"]  # first kept
    assert result[1]["text_html"] == rephrased  # second rephrased
    assert result[1].get("_verb_coherence_rephrased") is True


def test_oracle_down_skips_silently():
    bullets = [
        {"text_html": "Led team of 5", "_weighted_brs": 0.8},
        {"text_html": "Led migration", "_weighted_brs": 0.75},
    ]
    result = enforce_verb_coherence(bullets, "Acme", _oracle_ok=False)
    assert result == bullets  # unchanged — silent skip


def test_bad_rephrase_reverts():
    """If Oracle returns garbage, keep original."""
    bullets = [
        {"text_html": "Led team of 5", "_weighted_brs": 0.8},
        {"text_html": "Led migration", "_weighted_brs": 0.75},
    ]
    mock_resp = MagicMock()
    mock_resp.text = "x"  # too short
    with patch("linkright.resume.lib.coherence.oracle_generate", return_value=mock_resp):
        result = enforce_verb_coherence(bullets, "Acme", _oracle_ok=True)
    assert result[1]["text_html"] == "Led migration"  # reverted
