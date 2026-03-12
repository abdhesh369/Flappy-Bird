"""
Tests for high-score persistence (load/save round-trip, error resilience).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

# Redirect the score file into a temp directory for every test.
import src.score as score_module


@pytest.fixture(autouse=True)
def isolated_score_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        score_module, "HIGH_SCORE_FILE", str(tmp_path / "high_score.json")
    )
    yield


class TestLoadHighScore:
    def test_returns_zero_when_file_missing(self):
        assert score_module.load_high_score() == 0

    def test_returns_stored_value(self):
        score_module.save_high_score(42)
        assert score_module.load_high_score() == 42

    def test_returns_zero_on_corrupt_json(self, tmp_path, monkeypatch):
        path = tmp_path / "bad.json"
        path.write_text("not valid json{{{")
        monkeypatch.setattr(score_module, "HIGH_SCORE_FILE", str(path))
        assert score_module.load_high_score() == 0

    def test_returns_zero_on_missing_key(self, tmp_path, monkeypatch):
        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"other_key": 99}))
        monkeypatch.setattr(score_module, "HIGH_SCORE_FILE", str(path))
        assert score_module.load_high_score() == 0

    def test_returns_zero_for_negative_stored_value(self, tmp_path, monkeypatch):
        path = tmp_path / "neg.json"
        path.write_text(json.dumps({"high_score": -10}))
        monkeypatch.setattr(score_module, "HIGH_SCORE_FILE", str(path))
        assert score_module.load_high_score() == 0


class TestSaveHighScore:
    def test_save_persists_value(self):
        score_module.save_high_score(100)
        assert score_module.load_high_score() == 100

    def test_save_overwrites_previous_value(self):
        score_module.save_high_score(50)
        score_module.save_high_score(200)
        assert score_module.load_high_score() == 200

    def test_save_to_unwritable_path_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(score_module, "HIGH_SCORE_FILE", "/no/such/dir/score.json")
        score_module.save_high_score(99)  # Must not raise
