import json, re
from pathlib import Path

BASE = Path(__file__).resolve().parent
results = json.load(open(BASE / "results.json", encoding="utf-8"))
questions = json.load(open(BASE.parent.parent / "day05" / "docs" / "user_questions.json", encoding="utf-8"))

by = {"v1": {}, "v2": {}}
for x in results:
    by[x["version"]][x["id"]] = x["reply"]

MISSING = re.compile(r"records (do|does) not (have|contain|provide)|don'?t have (this |any )?information|no (further |additional )?information", re.I)
KEYS = {"answer", "confidence", "follow_up"}
CRITERIA = ["valid", "conf_fmt", "simple", "records", "missing", "followup"]

def is_low(c):
    return c == "low" or (isinstance(c, (int, float)) and c <= 0.4)

def check(r):
    if not isinstance(r, dict) or "detail" in r:
        return None  # API error, not an answer
    valid = KEYS <= r.keys() and isinstance(r["answer"], str)
    if not valid:
        return {k: False for k in CRITERIA}
    admits = bool(MISSING.search(r["answer"]))
    return {
        "valid": True,
        "conf_fmt": r["confidence"] in ("high", "medium", "low"),
        "simple": len(r["answer"].split()) <= 60,
        "records": bool(r.get("matched")) and not admits,
        "missing": is_low(r["confidence"]) if admits else not is_low(r["confidence"]),
        "followup": isinstance(r["follow_up"], str) and r["follow_up"].strip().endswith("?"),
    }

n = len(questions)
tot = {v: {k: 0 for k in CRITERIA} for v in by}
errors = {"v1": 0, "v2": 0}
rows = []
for i in range(1, n + 1):
    cells = []
    for v in ("v1", "v2"):
        r = by[v].get(i)
        c = check(r)
        if c is None:
            errors[v] += 1
            cells.append("ERROR")
            continue
        for k in CRITERIA:
            tot[v][k] += c[k]
        cells.append(f"conf={r['confidence']}")
    rows.append(f"| {i} | {questions[i-1]['question'][:70]} | {cells[0]} | {cells[1]} |")

names = {"valid": "Valid JSON (answer, confidence, follow_up)",
         "conf_fmt": "Confidence is high/medium/low",
         "simple": "Simple answers (≤60 words)",
         "records": "Gives a record-based answer",
         "missing": "Confidence matches missing info",
         "followup": "Has a follow-up question"}
out = ["| Criteria | Version 1 | Version 2 |", "|---|---|---|"]
for k in CRITERIA:
    out.append(f"| {names[k]} | {tot['v1'][k]}/{n} | {tot['v2'][k]}/{n} |")
out += ["", f"API errors: v1 = {errors['v1']}, v2 = {errors['v2']}", ""]
out += ["| # | Question | v1 | v2 |", "|---|---|---|---|"] + rows
if errors["v1"] or errors["v2"]:
    out.insert(0, "**WARNING: error entries present. Re-run before using these numbers.**\n")
Path(BASE / "table_out.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))