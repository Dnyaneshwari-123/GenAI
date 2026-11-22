import json
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_FILE = BASE_DIR.parent / "day05" / "docs" / "user_questions.json"
RESULTS_FILE = BASE_DIR / "eval" / "results.json"

URL = "http://127.0.0.1:8000/chat"
DELAY = 15        # seconds between calls, keeps you under 8000 tokens/minute
MAX_RETRIES = 4

with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
    questions = json.load(file)


def ask(question, version):
    for attempt in range(1, MAX_RETRIES + 1):
        response = None
        try:
            response = requests.post(
                URL,
                json={"question": question, "prompt_version": version},
                timeout=60,
            )
            reply = response.json()
        except (requests.RequestException, ValueError) as err:
            reply = {"detail": str(err)}

        good = (
            response is not None
            and response.ok
            and isinstance(reply, dict)
            and "detail" not in reply
            and "answer" in reply
        )
        if good:
            return reply

        wait = 20 * attempt
        print(f"  attempt {attempt} failed, waiting {wait}s: {str(reply)[:120]}")
        time.sleep(wait)
    return None


results = []

for version in ["v1", "v2"]:
    for item in questions:
        reply = ask(item["question"], version)
        if reply is None:
            print(f"FAILED: {version} question {item['id']}. results.json was NOT changed.")
            sys.exit(1)

        results.append({"id": item["id"], "version": version, "reply": reply})
        print(version, item["id"], reply.get("confidence"), reply.get("answer"))
        time.sleep(DELAY)

with open(RESULTS_FILE, "w", encoding="utf-8") as file:
    json.dump(results, file, indent=4, ensure_ascii=False)

print("Evaluation completed! 20 real answers saved.")