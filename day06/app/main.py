import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.llm import LLM
from app.records import load_records
from app.smart_search import SmartSearch


app = FastAPI(title="CyberSuraksha Chat API")

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_DIR = BASE_DIR / "prompts"

records = load_records()
searcher = SmartSearch(records)

try:
    llm = LLM()
except ValueError as error:
    llm = None
    print("LLM not ready:", error)


class ChatRequest(BaseModel):
    question: str
    prompt_version: str = "v2"


class Question(BaseModel):
    question: str


def read_prompt(filename):

    file_path = PROMPT_DIR / filename

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def parse_reply(reply, matched):

    start = reply.find("{")
    end = reply.rfind("}")

    try:
        result = json.loads(reply[start:end + 1])

        return {
            "answer": result["answer"],
            "confidence": result.get("confidence", "low"),
            "follow_up": result.get("follow_up", ""),
            "matched": matched
        }

    except (ValueError, KeyError, TypeError):
        return {
            "answer": reply,
            "confidence": "low",
            "follow_up": "Would you like to ask another question?",
            "matched": matched
        }


@app.get("/")
def home():
    return {"message": "Welcome to CyberSuraksha. Open /docs to try the API."}


@app.get("/health")
def health():
    return {"status": "ok", "records": len(records), "llm_ready": llm is not None}


@app.get("/records")
def get_records(limit: int = 10):
    return records[:limit]


@app.get("/records/{record_id}")
def get_record(record_id: int):
    for record in records:
        if record["id"] == record_id:
            return record
    raise HTTPException(status_code=404, detail="Record not found")


@app.get("/search")
def search(q: str):
    return searcher.search(q)


@app.post("/questions")
def ask(body: Question):
    results = searcher.search(body.question, top_n=1)
    if not results:
        return {
            "question": body.question,
            "answer": "Sorry, I could not find a matching fraud type.",
            "source_url": None
        }
    best = results[0]
    return {
        "question": body.question,
        "matched": best["fraud_name"],
        "answer": best["how_it_works"] + " Precautions: " + best["precautions"],
        "source_url": best["source_url"]
    }


@app.post("/chat")
def chat(data: ChatRequest):

    if llm is None:
        raise HTTPException(
            status_code=503,
            detail="LLM not ready. Check your .env file"
        )

    if data.prompt_version not in ["v1", "v2"]:
        raise HTTPException(
            status_code=400,
            detail="Prompt version must be v1 or v2"
        )

    found = searcher.search(data.question, top_n=3)
    matched = [record["fraud_name"] for record in found]

    context = ""

    for record in found:

        context += (
            "\nFraud Name: " + str(record["fraud_name"])
            + "\nHow it works: " + str(record["how_it_works"])
            + "\nPrecautions: " + str(record["precautions"])
            + "\n"
        )

    if context == "":
        context = "(no matching records)"

    system_prompt = read_prompt("system.txt")

    task_prompt = read_prompt(
        "task_" + data.prompt_version + ".txt"
    )

    user_prompt = task_prompt.replace("{context}", context)
    user_prompt = user_prompt.replace("{question}", data.question)

    try:

        reply = llm.ask(system_prompt, user_prompt)

        return parse_reply(reply, matched)

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail="Chat service error: " + str(error)
        )