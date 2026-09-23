"""
Inference wrapper for the fine-tuned KISAN-AI intent model.

    clf = IntentClassifier("intent_model", threshold=0.6, log_path="intent_log.jsonl")
    result = clf.classify("நாளைக்கு மழை வருமா?", rules=my_rule_based_classifier)
    # result = {"intent": ..., "source": "bert" | "rules" | "none",
    #           "bert_intent": ..., "confidence": ..., "rule_intent": ...}

- Confident model prediction (>= threshold)  -> intent from the model.
- Low confidence                             -> intent from your rule-based
  function if you pass one, otherwise intent=None (ask the farmer to rephrase).
- Every call is appended to log_path (JSONL) so the week of real Sarvam STT
  transcripts can be labelled later and used as the test set.

Requirements: pip install torch transformers (use the same transformers version
that trained the model). CPU is fine for inference.
"""
import json
import re
import time
import unicodedata

MAX_LEN = 64


def normalize(text: str) -> str:
    """Must stay identical to normalize() in train_intent.py."""
    text = unicodedata.normalize("NFC", str(text)).lower()
    text = text.replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"[^a-z0-9\u0B80-\u0BFF ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class IntentClassifier:
    def __init__(self, model_dir, threshold=0.6, log_path=None, device=None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.id2label = {int(k): v for k, v in self.model.config.id2label.items()}
        self.threshold = threshold
        self.log_path = log_path

    def _probs(self, texts):
        """list[str] -> list of probability lists (one per text)."""
        enc = self.tok([normalize(t) for t in texts], return_tensors="pt", padding=True,
                       truncation=True, max_length=MAX_LEN).to(self.device)
        with self.torch.no_grad():
            return self.torch.softmax(self.model(**enc).logits, dim=-1).cpu().tolist()

    def classify(self, text, rules=None):
        probs = self._probs([text])[0]
        best = max(range(len(probs)), key=probs.__getitem__)
        bert_intent, conf = self.id2label[best], probs[best]
        rule_intent = rules(text) if rules else None

        if conf >= self.threshold:
            intent, source = bert_intent, "bert"
        elif rule_intent is not None:
            intent, source = rule_intent, "rules"
        else:
            intent, source = None, "none"

        result = {"intent": intent, "source": source, "bert_intent": bert_intent,
                  "confidence": round(conf, 4), "rule_intent": rule_intent}
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.time(), "text": text, **result},
                                   ensure_ascii=False) + "\n")
        return result


if __name__ == "__main__":
    import sys
    clf = IntentClassifier(sys.argv[1] if len(sys.argv) > 1 else "intent_model")
    for q in ["நாளைக்கு மழை வருமா?", "இலைலாம் மஞ்சளா இருக்கு என்ன செய்ய", "மேட்டூர்ல தண்ணி எவ்வளவு இருக்கு"]:
        print(q, "->", clf.classify(q))
