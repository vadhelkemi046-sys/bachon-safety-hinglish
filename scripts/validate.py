import json
import os
import sys
from collections import Counter

TRAIN = os.path.normpath("data/dataset.jsonl")
path = os.path.normpath(sys.argv[1]) if len(sys.argv) > 1 else TRAIN

LABELS = {"scam", "grooming", "bullying", "inappropriate", "safe"}
RISKS = {"low", "medium", "high"}
LANGS = {"hinglish", "hindi", "gujarati", "english"}
REQUIRED = {"id", "text", "language", "label", "risk", "reason", "source"}


def norm(text):
    return text.strip().lower()


train_texts = set()
if path != TRAIN and os.path.exists(TRAIN):
    with open(TRAIN, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                train_texts.add(norm(json.loads(line).get("text", "")))

seen_ids, seen_text = set(), set()
counts, errors = Counter(), 0

with open(path, encoding="utf-8") as f:
    for n, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            print(f"line {n}: invalid JSON")
            errors += 1
            continue
        problems = []
        if REQUIRED - row.keys():
            problems.append("missing fields")
        if row.get("label") not in LABELS:
            problems.append("bad label")
        if row.get("risk") not in RISKS:
            problems.append("bad risk")
        if row.get("language") not in LANGS:
            problems.append("bad language")
        if row.get("id") in seen_ids:
            problems.append("duplicate id")
        text = norm(row.get("text", ""))
        if text in seen_text:
            problems.append("duplicate text")
        if text in train_texts:
            problems.append("LEAK: text also in train")
        seen_ids.add(row.get("id"))
        seen_text.add(text)
        counts[row.get("label")] += 1
        if problems:
            errors += 1
            print(f"line {n}: {', '.join(problems)}")

print(f"file: {path}")
print("label counts:", dict(counts))
print("total:", sum(counts.values()))
print("errors:", errors)
sys.exit(1 if errors else 0)