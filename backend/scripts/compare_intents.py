"""
scripts/compare_intents.py — Compare BERT vs rule-based intent classifiers.

Usage:
    python scripts/compare_intents.py path/to/labelled.json

Input format (JSON array):
    [
        {"text": "நாளைக்கு மழை வருமா?", "intent": "weather"},
        {"text": "இலை மஞ்சளா இருக்கு", "intent": "disease"},
        ...
    ]

Output:
    - BERT accuracy
    - Rule-based accuracy
    - Agreement rate (how often both classifiers agree)
    - Table of disagreements
"""

import json
import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Set default model dir relative to backend/
if "INTENT_MODEL_DIR" not in os.environ:
    os.environ["INTENT_MODEL_DIR"] = str(_BACKEND_DIR / "models" / "intent_model")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/compare_intents.py <labelled.json>")
        print()
        print("JSON format: [{\"text\": \"...\", \"intent\": \"...\"}]")
        sys.exit(1)

    labelled_path = sys.argv[1]
    with open(labelled_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    if not isinstance(samples, list) or not samples:
        print("Error: JSON must be a non-empty array of {text, intent} objects.")
        sys.exit(1)

    # Lazy-import after sys.path is set
    from services.intent_service import detect_intents
    from services.intent_classifier import (
        MODEL_TO_PIPELINE,
        _classifier,
        init_intent_model,
        classify_intent,
        INTENT_BACKEND,
    )

    # Ensure model is loaded (if available)
    try:
        if _classifier is None and INTENT_BACKEND != "rules":
            init_intent_model()
    except FileNotFoundError:
        print("⚠️  Model not found — BERT column will show 'N/A'")
    except Exception as e:
        print(f"⚠️  Model load failed: {e} — BERT column will show 'N/A'")

    # Re-import after init
    import services.intent_classifier as ic

    bert_correct = 0
    rules_correct = 0
    agree = 0
    total = len(samples)
    disagreements = []
    
    y_true = []
    y_bert = []
    y_rules = []

    # Build reverse map: pipeline intent → what the label file might use
    # The labelled file might use either model labels or pipeline labels
    _pipeline_to_model = {v: k for k, v in MODEL_TO_PIPELINE.items()}

    print(f"\n{'='*70}")
    print(f"  Comparing classifiers on {total} samples")
    print(f"{'='*70}\n")

    for i, sample in enumerate(samples):
        text = sample.get("text", "")
        gold = sample.get("intent", "").strip()

        if not text or not gold:
            print(f"  Skipping sample {i}: missing text or intent")
            continue

        # --- Rule-based ---
        rule_result = detect_intents(text)
        rule_primary = rule_result[0] if rule_result else "general"

        # --- BERT ---
        if ic._classifier is not None:
            raw_label, confidence = ic._classifier.predict(text)
            bert_mapped = MODEL_TO_PIPELINE.get(raw_label, raw_label)
        else:
            raw_label, confidence = "N/A", 0.0
            bert_mapped = "N/A"

        # --- Compare against gold ---
        # Normalize gold label: accept both model and pipeline label forms
        gold_normalized = MODEL_TO_PIPELINE.get(gold, gold)

        bert_match = bert_mapped == gold_normalized
        rule_match = rule_primary == gold_normalized
        both_agree = bert_mapped == rule_primary

        if bert_match:
            bert_correct += 1
        if rule_match:
            rules_correct += 1
        if both_agree:
            agree += 1
        else:
            disagreements.append({
                "text": text[:60],
                "gold": gold_normalized,
                "bert": f"{bert_mapped} ({confidence:.2f})" if bert_mapped != "N/A" else "N/A",
                "rules": rule_primary,
            })
            
        y_true.append(gold_normalized)
        y_bert.append(bert_mapped)
        y_rules.append(rule_primary)

    # --- Print results ---
    from sklearn.metrics import classification_report
    
    print(f"  BERT accuracy:       {bert_correct}/{total} = {bert_correct/total*100:.1f}%")
    print(f"  Rule-based accuracy: {rules_correct}/{total} = {rules_correct/total*100:.1f}%")
    print(f"  Agreement rate:      {agree}/{total} = {agree/total*100:.1f}%")
    
    print(f"\n{'='*70}")
    print("  BERT CLASSIFICATION REPORT")
    print(f"{'='*70}")
    print(classification_report(y_true, y_bert, zero_division=0))
    
    print(f"\n{'='*70}")
    print("  RULE-BASED CLASSIFICATION REPORT")
    print(f"{'='*70}")
    print(classification_report(y_true, y_rules, zero_division=0))
    print()

    if disagreements:
        print(f"  Disagreements ({len(disagreements)}):")
        print(f"  {'Text':<62} {'Gold':<18} {'BERT':<22} {'Rules':<15}")
        print(f"  {'-'*62} {'-'*18} {'-'*22} {'-'*15}")
        for d in disagreements:
            print(f"  {d['text']:<62} {d['gold']:<18} {d['bert']:<22} {d['rules']:<15}")
    else:
        print("  ✅ No disagreements — both classifiers agree on every sample!")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
