"""Unit tests for Pydantic schema validation."""
import pytest
import yaml
from pathlib import Path

from linkright.schemas.career_signals import CareerSignals, Signal, Achievement, Metadata


class TestCareerSignals:
    def test_sample_file_validates(self, sample_signals_path):
        with open(sample_signals_path) as f:
            data = yaml.safe_load(f)
        signals = CareerSignals(**data)
        assert signals.metadata.user is not None
        assert len(signals.signals) >= 1

    def test_minimum_valid_signals(self):
        data = {
            "metadata": {"user": "Test User"},
            "signals": [{
                "id": "test-1",
                "company": "TestCo",
                "role": "PM",
                "achievements": [{"raw": "Did something great"}],
            }],
        }
        signals = CareerSignals(**data)
        assert signals.metadata.user == "Test User"
        assert len(signals.signals) == 1

    def test_missing_signals_fails(self):
        with pytest.raises(Exception):
            CareerSignals(metadata={"user": "Test"}, signals=[])

    def test_achievement_fields(self):
        ach = Achievement(raw="Drove 40% growth", fit_tags=["growth", "metrics"], signal_strength=8)
        assert ach.raw == "Drove 40% growth"
        assert len(ach.fit_tags) == 2
        assert ach.signal_strength == 8
