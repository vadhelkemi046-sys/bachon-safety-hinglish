import json
import os
import sys
import re
import time

# prompt.py project ke root mein hai, isliye root ko path mein jodte hain
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompt import LABELS, build_system

load_dotenv()
client = genai.Client()  # GEMINI_API_KEY .env se padhta hai

MODEL = os.getenv("MODEL", "gemini-3.1-flash-lite")


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


train = load("data/dataset.jsonl")
TEST_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/test.jsonl"
test = load(TEST_PATH)
OUT_NAME = os.path.splitext(os.path.basename(TEST_PATH))[0]

SYSTEM = build_system(train)

CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM,
    temperature=0,
    max_output_tokens=300,
    response_mime_type="application/json",
)


def predict(text):
    raw = ""
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=f"<message>{text}</message>",
                config=CONFIG,
            )
            raw = resp.text or ""
            break
        except Exception as e:
            print(f"  retry {attempt + 1}: {str(e)[:80]}")
            time.sleep(10 * (attempt + 1))
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        out = json.loads(match.group(0))
        if out.get("label") not in LABELS:
            out["label"] = "invalid"
        return out
    except Exception:
        return {"label": "invalid", "risk": "", "reason": raw[:100]}


preds = []
for i, row in enumerate(test, 1):
    out = predict(row["text"])
    preds.append({**row, "pred_label": out["label"],
                  "pred_risk": out.get("risk", ""),
                  "pred_reason": out.get("reason", "")})
    print(f"{i}/{len(test)} {row['id']}: true={row['label']} pred={out['label']}")
    time.sleep(4)  # free tier ke rate limit se bachne ke liye

os.makedirs("results", exist_ok=True)
with open(f"results/{OUT_NAME}_predictions.jsonl", "w", encoding="utf-8") as f:
    for p in preds:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

# ---- Metrics ----
correct = sum(p["label"] == p["pred_label"] for p in preds)
print(f"\nModel: {MODEL}")
invalid = sum(p["pred_label"] == "invalid" for p in preds)
print(f"Invalid/failed predictions: {invalid}")
print(f"Accuracy: {correct}/{len(preds)} = {correct / len(preds):.2%}")

print("\nPer-label:")
print(f"{'label':<14}{'precision':>10}{'recall':>8}{'f1':>6}")
for lab in LABELS:
    tp = sum(p["label"] == lab and p["pred_label"] == lab for p in preds)
    fp = sum(p["label"] != lab and p["pred_label"] == lab for p in preds)
    fn = sum(p["label"] == lab and p["pred_label"] != lab for p in preds)
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    print(f"{lab:<14}{prec:>10.2f}{rec:>8.2f}{f1:>6.2f}")

safe = [p for p in preds if p["label"] == "safe"]
danger = [p for p in preds if p["label"] != "safe"]
fpr = sum(p["pred_label"] != "safe" for p in safe) / len(safe)
drec = sum(p["pred_label"] != "safe" for p in danger) / len(danger)
print(f"\nFalse-positive rate (safe ko khatra bola): {fpr:.2%}")
print(f"Danger recall (khatre ko pakda): {drec:.2%}")

print("\nGalat predictions:")
for p in preds:
    if p["label"] != p["pred_label"]:
        print(f"{p['id']}: true={p['label']} pred={p['pred_label']} | {p['text'][:70]}")