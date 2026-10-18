import sys, json
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

path = sys.argv[1] if len(sys.argv) > 1 else "results/test_perturbed_predictions.jsonl"
rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
if not rows:
    sys.exit("File khaali hai: " + path)

print("File:", path)
print("Rows:", len(rows))
print("Keys:", list(rows[0].keys()))

TRUE_KEYS = ["true", "true_label", "gold", "expected", "label"]
PRED_KEYS = ["pred", "pred_label", "prediction", "predicted", "predicted_label"]
TEXT_KEYS = ["text", "message", "msg", "input"]


def pick(r, names):
    for n in names:
        if n in r:
            v = r[n]
            if isinstance(v, dict):
                v = v.get("label")
            return v
    return None


valid_labels = ["scam", "grooming", "bullying", "inappropriate", "safe"]
data = []
for r in rows:
    t = pick(r, TRUE_KEYS)
    p = pick(r, PRED_KEYS)
    if p not in valid_labels:
        p = "INVALID"
    data.append((r.get("id", "?"), t, p, pick(r, TEXT_KEYS) or ""))

if all(t is None for _, t, _, _ in data):
    sys.exit("True label ka key nahi mila. Upar 'Keys:' wali line bhej do.")

correct = sum(1 for _, t, p, _ in data if t == p)
invalid = sum(1 for _, _, p, _ in data if p == "INVALID")
print()
print("Invalid/failed predictions:", invalid)
print(f"Accuracy: {correct}/{len(data)} = {100 * correct / len(data):.2f}%")

print()
print("Per-label:")
print(f"{'label':<14}{'support':>8}{'precision':>11}{'recall':>8}{'f1':>7}")
for lab in valid_labels:
    tp = sum(1 for _, t, p, _ in data if t == lab and p == lab)
    fp = sum(1 for _, t, p, _ in data if t != lab and p == lab)
    fn = sum(1 for _, t, p, _ in data if t == lab and p != lab)
    sup = tp + fn
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    print(f"{lab:<14}{sup:>8}{pr:>11.2f}{rc:>8.2f}{f1:>7.2f}")

safe_rows = [(t, p) for _, t, p, _ in data if t == "safe"]
danger_rows = [(t, p) for _, t, p, _ in data if t != "safe"]
fp_rate = sum(1 for _, p in safe_rows if p != "safe") / len(safe_rows) if safe_rows else 0
d_recall = sum(1 for _, p in danger_rows if p not in ("safe", "INVALID")) / len(danger_rows) if danger_rows else 0
print()
print(f"False-positive rate (safe ko khatra bola): {100 * fp_rate:.2f}%")
print(f"Danger recall (khatre ko pakda): {100 * d_recall:.2f}%")

wrong = [d for d in data if d[1] != d[2]]
print()
print("Confusion (true -> pred):", dict(Counter((t, p) for _, t, p, _ in wrong)))
print()
print(f"Galat predictions ({len(wrong)}):")
for i, t, p, text in wrong:
    print(f"- {i}: true={t} pred={p}")
    print(f"    {text}")