"""
tests/test_intent_classifier.py — Unit tests for the IndicBERT v2 intent
classifier with a stubbed model (no real model files required).
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure backend/ is on sys.path so ``services.*`` imports work.
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


# ---------------------------------------------------------------------------
# Helpers: build a fake classifier that returns controlled outputs.
# ---------------------------------------------------------------------------

def _make_fake_classifier(label: str, confidence: float):
    """Return a mock _BertIntentClassifier whose .predict() is fixed."""
    clf = MagicMock()
    clf.predict.return_value = (label, confidence)
    return clf


# ---------------------------------------------------------------------------
# Tests for normalize() — imported from intent_infer.py
# ---------------------------------------------------------------------------

class TestNormalize:
    """Verify the normalize() function used for preprocessing."""

    def test_basic_lowercase(self):
        from services.intent_infer import normalize
        assert normalize("HELLO WORLD") == "hello world"

    def test_tamil_preserved(self):
        from services.intent_infer import normalize
        result = normalize("நாளைக்கு மழை வருமா?")
        assert "நாளைக்கு" in result
        assert "மழை" in result
        assert "?" not in result  # punctuation removed

    def test_zwnj_zwj_removed(self):
        from services.intent_infer import normalize
        text = "hello\u200cworld\u200dtest"
        result = normalize(text)
        assert "\u200c" not in result
        assert "\u200d" not in result
        assert "helloworldtest" in result

    def test_whitespace_collapsed(self):
        from services.intent_infer import normalize
        assert normalize("  hello   world  ") == "hello world"

    def test_special_chars_to_space(self):
        from services.intent_infer import normalize
        result = normalize("நோய் — disease! (leaf)")
        # special chars become spaces, then collapsed
        assert "--" not in result
        assert "!" not in result
        assert "(" not in result

    def test_mixed_script(self):
        from services.intent_infer import normalize
        result = normalize("மேட்டூர் dam water level?")
        assert "மேட்டூர்" in result
        assert "dam" in result
        assert "?" not in result


# ---------------------------------------------------------------------------
# Tests for classify_intent() — the main public API
# ---------------------------------------------------------------------------

class TestClassifyIntent:
    """Test the classify_intent() function with a stubbed BERT model."""

    def _patch_and_classify(
        self,
        text: str,
        model_label: str,
        confidence: float,
        backend: str = "bert",
        threshold: float = 0.6,
    ) -> list[str]:
        """Helper: patch globals inside intent_classifier and run classify."""
        import services.intent_classifier as ic

        fake_clf = _make_fake_classifier(model_label, confidence)

        original_backend = ic.INTENT_BACKEND
        original_threshold = ic.INTENT_CONF_THRESHOLD
        original_clf = ic._classifier
        original_log_path = ic._LOG_PATH

        try:
            ic.INTENT_BACKEND = backend
            ic.INTENT_CONF_THRESHOLD = threshold
            ic._classifier = fake_clf

            # Redirect log to a temp file to avoid polluting real logs
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False
            ) as tmp:
                ic._LOG_PATH = Path(tmp.name)

            result = ic.classify_intent(text)
            return result
        finally:
            ic.INTENT_BACKEND = original_backend
            ic.INTENT_CONF_THRESHOLD = original_threshold
            ic._classifier = original_clf
            ic._LOG_PATH = original_log_path

    # --- Test: confident BERT prediction ---
    def test_confident_weather(self):
        """High-confidence 'weather' → ['general'] (via MODEL_TO_PIPELINE)."""
        result = self._patch_and_classify(
            "நாளைக்கு மழை வருமா?", "weather", 0.92
        )
        assert result == ["general"]

    def test_confident_disease(self):
        """High-confidence 'disease_prediction' → ['disease']."""
        result = self._patch_and_classify(
            "இலை மஞ்சளா இருக்கு", "disease_prediction", 0.85
        )
        assert result == ["disease"]

    def test_confident_dam(self):
        """High-confidence 'dam_water' → ['dam']."""
        result = self._patch_and_classify(
            "மேட்டூர் அணை நீர் நிலை", "dam_water", 0.78
        )
        assert result == ["dam"]

    def test_confident_fertilizer(self):
        """High-confidence 'fertilizer_recommendation' → ['fertilizer']."""
        result = self._patch_and_classify(
            "உரம் எவ்வளவு போடணும்", "fertilizer_recommendation", 0.88
        )
        assert result == ["fertilizer"]

    def test_confident_crop_recommend(self):
        """High-confidence 'crop_recommendation' → ['crop_recommend']."""
        result = self._patch_and_classify(
            "என்ன பயிர் போடலாம்", "crop_recommendation", 0.75
        )
        assert result == ["crop_recommend"]

    def test_confident_greeting(self):
        """High-confidence 'greeting' → ['greeting']."""
        result = self._patch_and_classify(
            "வணக்கம்", "greeting", 0.95
        )
        assert result == ["greeting"]

    def test_confident_out_of_scope(self):
        """High-confidence 'out_of_scope' → ['out_of_scope']."""
        result = self._patch_and_classify(
            "cricket score என்ன", "out_of_scope", 0.80
        )
        assert result == ["out_of_scope"]

    # --- Test: low confidence → rule-based fallback ---
    def test_low_confidence_falls_back_to_rules(self):
        """Low BERT confidence + rules detect 'disease' → ['disease']."""
        # The text contains disease keywords so rules will detect it
        result = self._patch_and_classify(
            "leaf yellow spot disease", "weather", 0.35, threshold=0.6
        )
        assert "disease" in result

    def test_low_confidence_rules_general(self):
        """Low BERT confidence + rules find nothing → ['general']."""
        # Text with no keywords for any intent
        result = self._patch_and_classify(
            "random gibberish xyz abc", "out_of_scope", 0.30, threshold=0.6
        )
        assert result == ["general"]

    # --- Test: INTENT_BACKEND=rules bypasses model ---
    def test_rules_backend_flag(self):
        """INTENT_BACKEND=rules → model never called, rules used."""
        import services.intent_classifier as ic

        fake_clf = _make_fake_classifier("weather", 0.99)

        original_backend = ic.INTENT_BACKEND
        original_clf = ic._classifier
        original_log_path = ic._LOG_PATH

        try:
            ic.INTENT_BACKEND = "rules"
            ic._classifier = fake_clf

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False
            ) as tmp:
                ic._LOG_PATH = Path(tmp.name)

            # Use text with dam keywords to verify rules are running
            result = ic.classify_intent("mettur dam water level")
            assert "dam" in result
            # Model should NOT have been called
            fake_clf.predict.assert_not_called()
        finally:
            ic.INTENT_BACKEND = original_backend
            ic._classifier = original_clf
            ic._LOG_PATH = original_log_path

    # --- Test: JSONL logging ---
    def test_logging_writes_jsonl(self):
        """Every classification writes a JSONL entry."""
        import services.intent_classifier as ic

        fake_clf = _make_fake_classifier("weather", 0.92)

        original_backend = ic.INTENT_BACKEND
        original_clf = ic._classifier
        original_log_path = ic._LOG_PATH

        try:
            ic.INTENT_BACKEND = "bert"
            ic._classifier = fake_clf

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False
            ) as tmp:
                log_file = Path(tmp.name)
                ic._LOG_PATH = log_file

            ic.classify_intent("நாளைக்கு மழை")

            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) >= 1

            entry = json.loads(lines[-1])
            assert "ts" in entry
            assert "text" in entry
            assert entry["text"] == "நாளைக்கு மழை"
            assert "model_intent" in entry
            assert "confidence" in entry
            assert "final_intent" in entry
        finally:
            ic.INTENT_BACKEND = original_backend
            ic._classifier = original_clf
            ic._LOG_PATH = original_log_path


# ---------------------------------------------------------------------------
# Tests for MODEL_TO_PIPELINE mapping completeness
# ---------------------------------------------------------------------------

class TestLabelMapping:
    """Ensure all model labels are mapped."""

    def test_all_model_labels_mapped(self):
        from services.intent_classifier import MODEL_TO_PIPELINE

        expected_model_labels = {
            "weather", "disease_prediction", "dam_water",
            "fertilizer_recommendation", "crop_recommendation",
            "greeting", "out_of_scope",
        }
        assert set(MODEL_TO_PIPELINE.keys()) == expected_model_labels

    def test_pipeline_values_are_strings(self):
        from services.intent_classifier import MODEL_TO_PIPELINE

        for k, v in MODEL_TO_PIPELINE.items():
            assert isinstance(v, str), f"{k} maps to {type(v)}, expected str"
