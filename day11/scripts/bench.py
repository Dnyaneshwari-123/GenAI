import json
import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
qs = [q["question"] for q in json.load(open("../day05/docs/user_questions.json", encoding="utf-8"))]

def run(label, delay):
    times = []
    for q in qs:
        t = time.perf_counter()
        r = requests.post(f"{BASE}/chat", json={"question": q, "prompt_version": "v2"}, timeout=90)
        times.append((time.perf_counter() - t) * 1000)
        assert r.ok and "detail" not in r.json(), r.text[:200]
        time.sleep(delay)
    print(label, "avg ms:", round(sum(times) / len(times)), "max ms:", round(max(times)))

run("cold", 12)   # 12 s pause keeps you under Groq's 8000 tokens/minute
run("warm", 0)
print(requests.get(f"{BASE}/metrics").json())