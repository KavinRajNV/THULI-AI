"""
services/intent_classifier.py — IndicBERT v2 intent classification with
rule-based fallback.

Replaces the rule-based detect_intents() as the primary classifier while
keeping it as a fallback when model confidence is low.

Env vars
--------
INTENT_BACKEND        : "bert" | "rules"  (default "bert")
INTENT_CONF_THRESHOLD : float             (default 0.6)
INTENT_MODEL_DIR      : str               (default "backend/models/intent_model")
"""

import json
import logging
import os
import time
from pathlib import Path

from services.intent_infer import normalize  # keep identical to training-time

logger = logging.getLogger("kisan.intent")

# ---------------------------------------------------------------------------
# Model label  →  pipeline intent name
# ---------------------------------------------------------------------------
MODEL_TO_PIPELINE = {
    "weather":                   "general",   # weather-only maps to "general"
    "disease_prediction":        "disease",
    "dam_water":                 "dam",
    "fertilizer_recommendation": "fertilizer",
    "crop_recommendation":       "crop_recommend",
    "greeting":                  "greeting",
    "out_of_scope":              "out_of_scope",
}

# Intents that have no dedicated handler in pipeline_service.  They fall
# through to the `else` (general) branch, but we want GPT to give a
# polite "here's what I can help with" reply instead of a weather dump.
_POLITE_INTENTS = {"greeting", "out_of_scope"}

# ---------------------------------------------------------------------------
# Configuration from env
# ---------------------------------------------------------------------------
INTENT_BACKEND = os.getenv("INTENT_BACKEND", "bert").lower()
INTENT_CONF_THRESHOLD = float(os.getenv("INTENT_CONF_THRESHOLD", "0.6"))
# Resolve default model dir relative to backend/ (this file lives in backend/services/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
INTENT_MODEL_DIR = os.getenv(
    "INTENT_MODEL_DIR",
    str(_BACKEND_DIR / "models" / "intent_model"),
)

# ---------------------------------------------------------------------------
# JSONL logger
# ---------------------------------------------------------------------------
_LOG_DIR = _BACKEND_DIR / "logs"
_LOG_PATH = _LOG_DIR / "intent_log.jsonl"


def _log_classification(
    text: str,
    model_intent: str | None,
    confidence: float | None,
    rule_intent: list[str] | None,
    final_intent: list[str],
) -> None:
    """Append one JSONL line.  Never raises."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "text": text,
            "model_intent": model_intent,
            "confidence": confidence,
            "rule_intent": rule_intent,
            "final_intent": final_intent,
        }
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("Intent log write failed: %s", exc)


# ---------------------------------------------------------------------------
# Singleton model holder
# ---------------------------------------------------------------------------
_classifier = None  # set by init_intent_model()


class _BertIntentClassifier:
    """Thin wrapper around intent_infer.IntentClassifier for pipeline use."""

    def __init__(self, model_dir: str, device: str | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = (
            AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
        )
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.id2label = {
            int(k): v for k, v in self.model.config.id2label.items()
        }
        print(
            f"✅ Intent classifier loaded (IndicBERT v2, {self.device.upper()}, "
            f"{len(self.id2label)} labels)"
        )

    # keep MAX_LEN identical to intent_infer.py
    _MAX_LEN = 64

    def predict(self, text: str) -> tuple[str, float]:
        """Return (model_label, confidence)."""
        enc = self.tok(
            [normalize(text)],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._MAX_LEN,
        ).to(self.device)
        with self.torch.no_grad():
            probs = (
                self.torch.softmax(self.model(**enc).logits, dim=-1)
                .cpu()
                .tolist()[0]
            )
        best = max(range(len(probs)), key=probs.__getitem__)
        return self.id2label[best], probs[best]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_intent_model() -> None:
    """Load the BERT model once at startup.  Called from main.py lifespan."""
    global _classifier

    if INTENT_BACKEND == "rules":
        print("ℹ️  INTENT_BACKEND=rules — BERT model will NOT be loaded.")
        return

    model_path = Path(INTENT_MODEL_DIR)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Intent model directory not found: {model_path.resolve()}\n"
            "Download the fine-tuned IndicBERT v2 model and place it at "
            f"'{INTENT_MODEL_DIR}/' (or set INTENT_MODEL_DIR env var)."
        )

    _classifier = _BertIntentClassifier(str(model_path))


def classify_intent(text: str) -> list[str]:
    """Drop-in replacement for ``intent_service.detect_intents()``.

    Returns ``list[str]`` — a list of pipeline intent names, exactly
    matching the contract that ``pipeline_service.build_context()`` expects.
    """
    from services.intent_service import detect_intents  # rule-based fallback

    model_intent: str | None = None
    confidence: float | None = None
    rule_intent: list[str] | None = None
    final: list[str]

    # ------------------------------------------------------------------
    # Path A — instant rollback
    # ------------------------------------------------------------------
    if INTENT_BACKEND == "rules" or _classifier is None:
        rule_intent = detect_intents(text)
        final = rule_intent
        print(f"📜 Intent: {final} (via RULES — backend forced or model missing)")
        _log_classification(text, None, None, rule_intent, final)
        return final

    # ------------------------------------------------------------------
    # Path B — BERT with rule-based fallback
    # ------------------------------------------------------------------
    raw_label, confidence = _classifier.predict(text)
    model_intent = MODEL_TO_PIPELINE.get(raw_label, raw_label)

    if confidence >= INTENT_CONF_THRESHOLD:
        final = [model_intent]
        print(f"🤖 Intent: {final} (via BERT, conf: {confidence:.2f})")
    else:
        # Low confidence → ask the rules
        rule_intent = detect_intents(text)
        if rule_intent != ["general"]:
            final = rule_intent
            print(f"⚠️ Intent: {final} (via RULES fallback, BERT conf too low: {confidence:.2f})")
        else:
            # Both classifiers uncertain → still return general
            final = ["general"]
            print(f"❓ Intent: {final} (Both BERT {confidence:.2f} & RULES found nothing)")

    _log_classification(text, model_intent, round(confidence, 4), rule_intent, final)
    return final
