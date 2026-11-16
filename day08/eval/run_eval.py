import json
import time

from app.embed import Embedder
from app.llm import LLM
from app.rag import RAG
from app.vectorstore import build_store

CONFIGS = [
    {"name": "A", "chunk_size": 600, "overlap": 100, "top_k": 3},
    {"name": "B", "chunk_size": 300, "overlap": 50, "top_k": 5},
]

with open("eval/eval_set.json", encoding="utf-8") as f:
    rows = json.load(f)

embedder = Embedder()
llm = LLM()


def ask_with_retry(rag, question):
    for attempt in range(3):
        try:
            return rag.ask(question)
        except RuntimeError as error:
            print("  failed, retrying:", str(error)[:120])
            time.sleep(20)
    return None


def check(row, result):
    if result is None:
        return {"id": row["id"], "answerable": row["answerable"], "error": True,
                "retrieval_hit": False, "decision_ok": False, "cited": False,
                "passed": False, "known": False, "best_distance": None, "reason": "error"}

    text = " ".join(" ".join(c["text"] for c in result["retrieved"]).lower().split())
    known = result["known"]
    answerable = row["answerable"]

    hit = any(k.lower() in text for k in row["keywords"]) if answerable else False
    decision_ok = (known == answerable)
    cited = bool(known and len(result["citations"]) > 0)

    if answerable:
        passed = bool(hit and decision_ok and cited)
    else:
        passed = decision_ok

    best = result["retrieved"][0]["distance"] if result["retrieved"] else None
    return {"id": row["id"], "answerable": answerable, "error": False,
            "retrieval_hit": hit, "decision_ok": decision_ok, "cited": cited,
            "passed": passed, "known": known, "best_distance": best,
            "reason": result["reason"]}


def why_failed(d):
    if d["error"]:
        return "error"
    if d["answerable"]:
        if not d["retrieval_hit"]:
            return "no hit"
        if not d["known"]:
            return "said IDK"
        return "no cite"
    return "answered"


all_details = {}
summary = []

for config in CONFIGS:
    print("\n=== Config", config["name"], config, "===")
    store = build_store(config["chunk_size"], config["overlap"], embedder)
    rag = RAG(store, llm, top_k=config["top_k"])

    details = []
    for row in rows:
        result = ask_with_retry(rag, row["question"])
        d = check(row, result)
        details.append(d)
        print("Q" + str(row["id"]), "answerable" if row["answerable"] else "NOT answerable",
              "| best distance:", d["best_distance"], "| known:", d["known"],
              "|", "PASS" if d["passed"] else "FAIL")
        time.sleep(5)

    all_details[config["name"]] = details

    answerable_rows = [d for d in details if d["answerable"]]
    summary.append({
        "config": config,
        "passed": sum(1 for d in details if d["passed"]),
        "hits": sum(1 for d in answerable_rows if d["retrieval_hit"]),
        "decisions": sum(1 for d in details if d["decision_ok"]),
        "cited": sum(1 for d in answerable_rows if d["cited"]),
        "errors": sum(1 for d in details if d["error"]),
        "answerable_count": len(answerable_rows),
        "total": len(details),
    })

best = max(summary, key=lambda s: (s["passed"], s["hits"], -s["config"]["top_k"]))

lines = ["| Config | Chunk size / overlap | Top-k | Passed | Retrieval hit | Right answer or IDK | Cited | Errors | Winner |",
         "|---|---|---|---|---|---|---|---|---|"]
for s in summary:
    c = s["config"]
    lines.append("| " + c["name"] + " | " + str(c["chunk_size"]) + " / " + str(c["overlap"])
                 + " | " + str(c["top_k"])
                 + " | " + str(s["passed"]) + "/" + str(s["total"])
                 + " | " + str(s["hits"]) + "/" + str(s["answerable_count"])
                 + " | " + str(s["decisions"]) + "/" + str(s["total"])
                 + " | " + str(s["cited"]) + "/" + str(s["answerable_count"])
                 + " | " + str(s["errors"])
                 + " | " + ("**WINNER**" if s is best else "") + " |")

lines += ["", "## Per-question results", "",
          "| Q | Question | Answerable | A | B |", "|---|---|---|---|---|"]
for i, row in enumerate(rows):
    cells = []
    for name in ["A", "B"]:
        d = all_details[name][i]
        cells.append("pass" if d["passed"] else "FAIL (" + why_failed(d) + ")")
    lines.append("| " + str(row["id"]) + " | " + row["question"][:60] + " | "
                 + ("yes" if row["answerable"] else "no") + " | " + cells[0] + " | " + cells[1] + " |")

with open("eval/winner_table.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

with open("eval/eval_results.json", "w", encoding="utf-8") as f:
    json.dump(all_details, f, indent=2)

print("\n" + "\n".join(lines))
print("\nSaved eval/winner_table.md and eval/eval_results.json")