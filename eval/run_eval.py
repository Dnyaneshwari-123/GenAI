
import json
import requests
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_FILE = BASE_DIR.parent / "day05" / "docs" / "user_questions.json"
RESULTS_FILE = BASE_DIR / "eval" / "results.json"

URL = "http://127.0.0.1:8000/chat"

with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
    questions = json.load(file)

results = []

for version in ["v1", "v2"]:

    for item in questions:

        response = requests.post(
            URL,
            json={
                "question": item["question"],
                "prompt_version": version
            },
            timeout=60
        )

        reply = response.json()

        results.append({
            "id": item["id"],
            "version": version,
            "reply": reply
        })

        print(
            version,
            item["id"],
            reply.get("confidence"),
            reply.get("answer")
        )

        time.sleep(2)

with open(RESULTS_FILE, "w", encoding="utf-8") as file:
    json.dump(results, file, indent=4, ensure_ascii=False)

print("Evaluation completed!")
