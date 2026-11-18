import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from app.graph import build_graph
from app.llm import LLM
from app.rag import RAG
from app.records import load_records
from app.smart_search import SmartSearch
from app.vectorstore import build_store


app = FastAPI(title="CyberSuraksha API")

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_DIR = BASE_DIR / "prompts"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
TOP_K = 3

records = load_records()
searcher = SmartSearch(records)
store = build_store(CHUNK_SIZE, CHUNK_OVERLAP)

try:
    llm = LLM()
except ValueError as error:
    llm = None
    print("LLM not ready:", error)

rag = RAG(store, llm, top_k=TOP_K) if llm is not None else None
agent_graph = build_graph(llm, rag) if llm is not None else None


class ChatRequest(BaseModel):
    question: str
    prompt_version: str = "v2"


class Question(BaseModel):
    question: str


class AgentRequest(BaseModel):
    message: str | None = None
    thread_id: str | None = None
    approve: bool | None = None


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


def this_turn(messages):
    start = 0
    for i, line in enumerate(messages):
        if line.startswith("User: "):
            start = i
    return [line[:300] for line in messages[start:]]


def agent_response(result, thread_id):
    if "__interrupt__" in result:
        pending = result["__interrupt__"][0].value
        return {
            "status": "needs_approval",
            "thread_id": thread_id,
            "pending": pending,
            "how_to_continue": "Call POST /agent again with this thread_id and approve true or false"
        }

    risk = result.get("risk")
    return {
        "status": "done",
        "thread_id": thread_id,
        "answer": result["answer"],
        "risk_score": risk["score"] if risk else None,
        "approved": result.get("approved"),
        "citations": result.get("citations", []),      # EDIT 2: citations for the UI
        "trace": this_turn(result["messages"])
    }


@app.get("/")
def home():
    return {"message": "Welcome to CyberSuraksha. Open /docs to try the API."}


@app.get("/health")
def health():
    return {"status": "ok", "records": len(records), "chunks": store.count(), "llm_ready": llm is not None}


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


@app.get("/search/semantic")
def semantic_search(q: str, n: int = 3):
    return store.search(q, n)


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


@app.post("/ask")
def ask_rag(body: Question):

    if rag is None:
        raise HTTPException(status_code=503, detail="LLM not ready. Check your .env file")

    try:
        return rag.ask(body.question)

    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Chat service error: " + str(error))


@app.post("/agent")
def agent(body: AgentRequest):

    if agent_graph is None:
        raise HTTPException(status_code=503, detail="LLM not ready. Check your .env file")

    thread_id = body.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    waiting = bool(agent_graph.get_state(config).next)

    try:
        if body.approve is not None:
            if not waiting:
                raise HTTPException(status_code=400, detail="Nothing is waiting for approval on this thread")
            result = agent_graph.invoke(Command(resume=body.approve), config)
        else:
            if not body.message:
                raise HTTPException(status_code=400, detail="message is required")
            if waiting:
                raise HTTPException(status_code=409, detail="This thread is waiting for approval")
            result = agent_graph.invoke({
                "messages": ["User: " + body.message],
                "decision": {},
                "steps": 0,
                "answer": "",
                "risk": None,
                "approved": None,
                "citations": []                        # EDIT 1: reset citations each turn
            }, config)

    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Agent error: " + str(error))

    return agent_response(result, thread_id)


@app.post("/chat")
def chat(data: ChatRequest):

    if llm is None:
        raise HTTPException(status_code=503, detail="LLM not ready. Check your .env file")

    if data.prompt_version not in ["v1", "v2"]:
        raise HTTPException(status_code=400, detail="Prompt version must be v1 or v2")

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
    task_prompt = read_prompt("task_" + data.prompt_version + ".txt")

    user_prompt = task_prompt.replace("{context}", context)
    user_prompt = user_prompt.replace("{question}", data.question)

    try:
        reply = llm.ask(system_prompt, user_prompt)
        return parse_reply(reply, matched)

    except Exception as error:
        raise HTTPException(status_code=502, detail="Chat service error: " + str(error))