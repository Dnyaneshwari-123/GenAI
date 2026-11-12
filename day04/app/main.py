from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.records import load_records
from app.smart_search import SmartSearch

app = FastAPI(title="CyberSuraksha")

records = load_records()
searcher = SmartSearch(records)


class Question(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", "records": len(records)}


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
        return {"question": body.question,
                "answer": "Sorry, I could not find a matching fraud type.",
                "source_url": None}
    best = results[0]
    return {"question": body.question,
            "matched": best["fraud_name"],
            "answer": best["how_it_works"] + " Precautions: " + best["precautions"],
            "source_url": best["source_url"]}