"""Validate a JSONL file for the bachon-safety-hinglish dataset.

Usage (from the project root):
    python scripts/validate.py                      # checks data/dataset.jsonl
    python scripts/validate.py data/test_hard.jsonl # also checks leakage against train
    python scripts/validate.py data/test.jsonl

Errors make the script exit with code 1. Warnings do not.
"""
import json
import os
import sys
import unicodedata
from collections import Counter, defaultdict

TRAIN = os.path.normpath("data/dataset.jsonl")
path = os.path.normpath(sys.argv[1]) if len(sys.argv) > 1 else TRAIN

LABELS = {"scam", "grooming", "bullying", "inappropriate", "safe"}
RISKS = {"low", "medium", "high"}
LANGS = {"hinglish", "hindi", "gujarati", "english"}
REQUIRED = {"id", "text", "language", "label", "risk", "reason", "source"}
NEAR_DUP_THRESHOLD = 0.8  # word-set Jaccard similarity
MIN_PER_LABEL = 20  # warn if a label has fewer examples than this


def norm(text):
    """Lowercase, NFC-normalise, drop punctuation/symbols, collapse spaces.

    Combining marks (Hindi/Gujarati matras) are kept on purpose.
    """
    text = unicodedata.normalize("NFC", str(text)).lower()
    text = "".join(c for c in text if not unicodedata.category(c).startswith(("P", "S")))
    return " ".join(text.split())


def words(text):
    return frozenset(text.split())


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_rows(p):
    with open(p, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                yield n, line


# ---- load train for leakage checks (only when checking another file) ----
train_exact, train_words = set(), []
if path != TRAIN and os.path.exists(TRAIN):
    for _, line in load_rows(TRAIN):
        try:
            t = norm(json.loads(line).get("text", ""))
        except (json.JSONDecodeError, AttributeError):
            continue
        train_exact.add(t)
        train_words.append((t, words(t)))

seen_ids, seen_text = set(), {}
labels_for_text = defaultdict(set)
counts, by_lang = Counter(), Counter()
errors = warnings = 0

for n, line in load_rows(path):
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        print(f"line {n}: ERROR invalid JSON")
        errors += 1
        continue
    if not isinstance(row, dict):
        print(f"line {n}: ERROR row is not a JSON object")
        errors += 1
        continue

    problems, warns = [], []
    if REQUIRED - row.keys():
        problems.append("missing fields: " + ", ".join(sorted(REQUIRED - row.keys())))
    if row.get("label") not in LABELS:
        problems.append("bad label")
    if row.get("risk") not in RISKS:
        problems.append("bad risk")
    if row.get("language") not in LANGS:
        problems.append("bad language")
    if row.get("id") in seen_ids:
        problems.append("duplicate id")

    raw_text = row.get("text", "")
    text = norm(raw_text)
    if not text:
        problems.append("empty text")
    if not str(row.get("reason", "")).strip():
        problems.append("empty reason")

    if text in seen_text:
        problems.append(f"duplicate text (first on line {seen_text[text]})")
    else:
        seen_text[text] = n
    labels_for_text[text].add(row.get("label"))

    if text in train_exact:
        problems.append("LEAK: text also in train")
    elif train_words:
        w = words(text)
        best = max((jaccard(w, tw) for _, tw in train_words), default=0.0)
        if best >= NEAR_DUP_THRESHOLD:
            warns.append(f"near-duplicate of a train row (similarity {best:.2f})")

    if row.get("label") == "safe" and row.get("risk") not in (None, "low"):
        warns.append("label is safe but risk is not low")
    if row.get("label") in LABELS - {"safe"} and row.get("risk") == "low":
        warns.append("unsafe label with low risk (check this)")

    seen_ids.add(row.get("id"))
    counts[row.get("label")] += 1
    by_lang[(row.get("label"), row.get("language"))] += 1

    if problems:
        errors += 1
        print(f"line {n}: ERROR {', '.join(problems)}")
    if warns:
        warnings += 1
        print(f"line {n}: warning {', '.join(warns)}")

for t, ls in labels_for_text.items():
    if len(ls) > 1:
        errors += 1
        print(f"conflicting labels {sorted(map(str, ls))} for the same text: {t[:60]!r}")

print()
print(f"file: {path}")
print("label counts:", dict(counts))
print("total:", sum(counts.values()))
print("label x language:")
for label in sorted(LABELS):
    row_counts = {lg: by_lang[(label, lg)] for lg in sorted(LANGS) if by_lang[(label, lg)]}
    print(f"  {label:14s} {row_counts}")
for label in sorted(LABELS):
    if counts[label] < MIN_PER_LABEL:
        print(f"warning: only {counts[label]} examples for '{label}' (aim for {MIN_PER_LABEL}+)")
        warnings += 1
print(f"errors: {errors}   warnings: {warnings}")
sys.exit(1 if errors else 0)