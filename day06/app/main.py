
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.llm import LLM
from app.records import load_records


app = FastAPI(title="CyberSuraksha Chat API")

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_DIR = BASE_DIR / "prompts"

records = load_records()
llm = LLM()


class ChatRequest(BaseModel):
    question: str
    prompt_version: str = "v2"


def read_prompt(filename):

    file_path = PROMPT_DIR / filename

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def parse_reply(reply):

    try:
        result = json.loads(reply)

        return {
            "answer": result["answer"],
            "confidence": result["confidence"],
            "follow_up": result["follow_up"]
        }

    except (ValueError, KeyError, TypeError):
        return {
            "answer": reply,
            "confidence": "low",
            "follow_up": "Would you like to ask another question?"
        }


@app.get("/")
def home():
    return {"message": "Welcome to CyberSuraksha"}


@app.post("/chat")
def chat(data: ChatRequest):

    if data.prompt_version not in ["v1", "v2"]:
        raise HTTPException(
            status_code=400,
            detail="Prompt version must be v1 or v2"
        )

    context = ""

    for record in records:

        context += (
            "\nFraud Name: " + str(record["fraud_name"])
            + "\nHow it works: " + str(record["how_it_works"])
            + "\nPrecautions: " + str(record["precautions"])
            + "\n"
        )

    system_prompt = read_prompt("system.txt")

    task_prompt = read_prompt(
        "task_" + data.prompt_version + ".txt"
    )

    user_prompt = task_prompt.replace("{context}", context)
    user_prompt = user_prompt.replace("{question}", data.question)

    try:

        reply = llm.ask(system_prompt, user_prompt)

        return parse_reply(reply)

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail="Chat service error: " + str(error)
        )
