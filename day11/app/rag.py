import json
import os

BASE = os.path.dirname(os.path.dirname(__file__))
PROMPT_DIR = os.path.join(BASE, "prompts")

UNKNOWN_ANSWER = (
    "I don't know. The documents I have do not answer this question. "
    "Please contact your bank, call 1930 or report at cybercrime.gov.in."
)


def read_prompt(name):
    with open(os.path.join(PROMPT_DIR, name), encoding="utf-8") as f:
        return f.read()


class RAG:

    def __init__(self, store, llm, top_k=3, max_distance=1.0):
        self.store = store
        self.llm = llm
        self.top_k = top_k
        self.max_distance = max_distance
        self.system_prompt = read_prompt("rag_system.txt")
        self.task_prompt = read_prompt("rag_task.txt")

    def unknown(self, question, retrieved, reason):
        return {
            "question": question,
            "answer": UNKNOWN_ANSWER,
            "known": False,
            "reason": reason,
            "citations": [],
            "retrieved": retrieved,
        }

    def parse(self, reply):
        start = reply.find("{")
        end = reply.rfind("}")
        try:
            data = json.loads(reply[start:end + 1])
            answer = str(data["answer"])
            used = [int(n) for n in data.get("used", [])]
            return answer, used
        except (ValueError, KeyError, TypeError):
            return None, []

    def ask(self, question):
        hits = self.store.search(question, self.top_k)

        retrieved = []
        for number, hit in enumerate(hits, start=1):
            retrieved.append({
                "number": number,
                "chunk_id": hit["id"],
                "page": hit["page"],
                "distance": hit["distance"],
                "text": hit["text"],
            })

        if not hits or hits[0]["distance"] > self.max_distance:
            return self.unknown(question, retrieved, "no chunk is close enough")

        context = ""
        for item in retrieved:
            context += "[" + str(item["number"]) + "] (page " + str(item["page"]) + ") " + item["text"] + "\n\n"

        user_prompt = self.task_prompt.replace("{context}", context)
        user_prompt = user_prompt.replace("{question}", question)

        reply = self.llm.ask(self.system_prompt, user_prompt)
        answer, used = self.parse(reply)

        if answer is None:
            return self.unknown(question, retrieved, "reply was not valid JSON")

        said_unknown = answer.lower().replace("’", "'").startswith("i don't know")
        if said_unknown or len(used) == 0:
            return self.unknown(question, retrieved, "the model said the excerpts do not answer it")

        citations = []
        for number in used:
            if 1 <= number <= len(hits):
                hit = hits[number - 1]
                citations.append({
                    "number": number,
                    "chunk_id": hit["id"],
                    "title": hit["title"],
                    "page": hit["page"],
                    "source": hit["source"],
                })

        if len(citations) == 0:
            return self.unknown(question, retrieved, "no valid citation")

        return {
            "question": question,
            "answer": answer,
            "known": True,
            "reason": "answered from the retrieved chunks",
            "citations": citations,
            "retrieved": retrieved,
        }