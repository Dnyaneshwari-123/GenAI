import json
from app.vectorstore import VectorStore

with open("../day05/docs/user_questions.json", encoding="utf-8") as f:
    questions = json.load(f)

store = VectorStore()

lines = ["# Semantic search results", "",
         "Top 3 chunks for each question. Distance: lower means closer in meaning.", ""]

for item in questions:
    lines.append("## Q" + str(item["id"]) + ": " + item["question"])
    lines.append("")
    lines.append("| Rank | Page | Distance | Start of chunk | Relevant? |")
    lines.append("|---|---|---|---|---|")
    for rank, hit in enumerate(store.search(item["question"], 3), start=1):
        text = hit["text"][:110].replace("|", " ")
        lines.append("| " + str(rank) + " | " + str(hit["page"]) + " | "
                     + str(hit["distance"]) + " | " + text + "... | |")
    lines.append("")

with open("eval/search_results.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Saved eval/search_results.md")