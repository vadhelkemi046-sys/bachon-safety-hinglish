"""Make noisy variants of an existing test file to check robustness.

Usage (from the project root):
    python scripts/perturb.py data/test_hard.jsonl data/test_perturbed.jsonl
    python scripts/perturb.py data/test_hard.jsonl data/test_perturbed.jsonl --per-row 2 --seed 7

Label, risk and reason are copied unchanged. The changes are only in how the
message is typed (SMS-style spelling, dropped vowels, stretched letters,
casing, typos, punctuation). Emojis and meaning are left alone.
"""
import argparse
import json
import random
import re
import unicodedata

# Common Hinglish SMS-style spellings: word -> alternatives
SHORT = {
    "nahi": ["nhi", "nahin", "nai"],
    "nahin": ["nhi", "nai"],
    "hai": ["h", "hai"],
    "hain": ["hn", "h"],
    "kya": ["kya", "kyaa", "kia"],
    "kyu": ["kyun", "kyo", "q"],
    "kyun": ["kyu", "q"],
    "mat": ["mt"],
    "bata": ["bta", "batao"],
    "batana": ["btana", "btaana"],
    "bhai": ["bhaii", "bhaiya", "bro"],
    "aaj": ["aj", "aaj"],
    "kal": ["kl"],
    "tum": ["tm", "tu"],
    "tumhara": ["tmhara", "tera"],
    "tera": ["tr", "tera"],
    "mujhe": ["mjhe", "mje"],
    "mera": ["mra", "mera"],
    "abhi": ["abhi", "abi"],
    "bhej": ["bhj", "bhejo"],
    "bhejo": ["bhjo", "bhej"],
    "karo": ["kro", "kar"],
    "kar": ["kr"],
    "bahut": ["bhot", "bohot", "bht"],
    "accha": ["acha", "achha", "acchaa"],
    "acha": ["accha", "achha"],
    "yaar": ["yar", "yaar", "yaaar"],
    "sab": ["sb"],
    "sabko": ["sbko"],
    "kisi": ["ksi"],
    "kisi ko": ["ksi ko"],
    "please": ["plz", "pls"],
    "link": ["lnk", "link"],
    "ghar": ["ghr"],
    "paisa": ["paisa", "paise"],
    "mummy": ["mom", "mumma"],
    "papa": ["pappa", "pa"],
    "dekh": ["dekhh", "dkh"],
    "ho": ["ho", "hoo"],
}


def is_latin(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin = sum(1 for c in letters if unicodedata.name(c, "").startswith("LATIN"))
    return latin / len(letters) >= 0.8


def tokens_of(text):
    return re.findall(r"\w+|\W+", text)


def is_word(tok):
    return tok.isalpha() and tok.isascii()


def sms_short(toks, rng):
    out = []
    for t in toks:
        key = t.lower()
        if is_word(t) and key in SHORT and rng.random() < 0.7:
            out.append(rng.choice(SHORT[key]))
        else:
            out.append(t)
    return out


def drop_vowels(toks, rng):
    out = []
    for t in toks:
        if is_word(t) and len(t) >= 5 and rng.random() < 0.3:
            out.append(t[0] + re.sub(r"[aeiouAEIOU]", "", t[1:]))
        else:
            out.append(t)
    return out


def stretch(toks, rng):
    idx = [i for i, t in enumerate(toks) if is_word(t) and len(t) >= 3 and re.search(r"[aeiou]", t)]
    if not idx:
        return toks
    i = rng.choice(idx)
    t = toks[i]
    vowels = [j for j, c in enumerate(t) if c in "aeiou"]
    j = rng.choice(vowels)
    toks = list(toks)
    toks[i] = t[:j] + t[j] * rng.randint(2, 3) + t[j + 1:]
    return toks


def casing(toks, rng):
    mode = rng.choice(["lower", "upper_word", "random"])
    out = []
    for t in toks:
        if not is_word(t):
            out.append(t)
        elif mode == "lower":
            out.append(t.lower())
        elif mode == "upper_word":
            out.append(t.upper() if rng.random() < 0.2 else t)
        else:
            out.append("".join(c.upper() if rng.random() < 0.3 else c.lower() for c in t))
    return out


def swap_typo(toks, rng):
    idx = [i for i, t in enumerate(toks) if is_word(t) and len(t) >= 4]
    if not idx:
        return toks
    i = rng.choice(idx)
    t = toks[i]
    j = rng.randint(1, len(t) - 3)
    toks = list(toks)
    toks[i] = t[:j] + t[j + 1] + t[j] + t[j + 2:]
    return toks


def punct(toks, rng):
    mode = rng.choice(["strip", "spaces"])
    out = []
    for t in toks:
        if mode == "strip":
            out.append(re.sub(r"[.,!?;:।]", "", t) if not is_word(t) else t)
        else:
            out.append(t + " " if t.isspace() else t)
    return out


LATIN_OPS = [sms_short, drop_vowels, stretch, casing, swap_typo, punct]
OTHER_OPS = [punct]  # Hindi / Gujarati script: only punctuation and spacing


def make_variant(text, rng):
    ops = LATIN_OPS if is_latin(text) else OTHER_OPS
    k = min(len(ops), rng.randint(2, 3)) if len(ops) > 1 else 1
    chosen = rng.sample(ops, k)
    toks = tokens_of(text)
    for op in chosen:
        toks = op(toks, rng)
    return " ".join("".join(toks).split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--per-row", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = []
    with open(args.src, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    seen = {" ".join(r["text"].split()).lower() for r in rows}
    out, skipped = [], 0
    for row in rows:
        made = 0
        for _ in range(20):
            if made >= args.per_row:
                break
            new = make_variant(row["text"], rng)
            key = new.lower()
            if not new or key in seen:
                continue
            seen.add(key)
            made += 1
            out.append({**row, "id": f"{row['id']}_p{made}", "text": new,
                        "source": "test_perturbed", "parent_id": row["id"]})
        if made == 0:
            skipped += 1

    with open(args.dst, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"read {len(rows)} rows from {args.src}")
    print(f"wrote {len(out)} variants to {args.dst}")
    print(f"rows with no variant possible: {skipped}")
    for r in out[:6]:
        print(f"  {r['id']}: {r['text'][:80]}")


if __name__ == "__main__":
    main()