import json

with open("eval/eval_results.json", encoding="utf-8") as f:
    data = json.load(f)

for name, rows in data.items():
    ok = [r["best_distance"] for r in rows if r["answerable"] and r["best_distance"] is not None]
    no = [r["best_distance"] for r in rows if not r["answerable"] and r["best_distance"] is not None]
    print("Config", name, "| answerable max:", max(ok), "| unanswerable min:", min(no))
    if max(ok) < min(no):
        print("  threshold between the two:", round((max(ok) + min(no)) / 2, 2))
    else:
        print("  the ranges overlap, so distance alone cannot separate them; keep the LLM check")