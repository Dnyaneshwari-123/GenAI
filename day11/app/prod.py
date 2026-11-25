"""Production helpers: input guard, TTL cache, request metrics."""
import hashlib
import json
import logging
import re
import time
from collections import OrderedDict, deque

logger = logging.getLogger("cybersuraksha")
MAX_QUESTION_CHARS = 500

INJECTION = re.compile(
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|rules)"
    r"|reveal .*(system prompt|api key|secret)"
    r"|(show|print|repeat) .*(system prompt|your instructions)"
    r"|developer mode|you are now",
    re.I,
)

SAFE_REFUSAL = {
    "answer": "I can only help with online fraud and cyber-safety questions based on our records.",
    "confidence": "low",
    "follow_up": "Would you like to ask about a fraud type such as UPI, phishing or QR code scams?",
    "matched": [],
}


def check_input(question: str):
    """Return (ok, reason). Never calls the LLM."""
    q = (question or "").strip()
    if len(q) < 3:
        return False, "too_short"
    if len(q) > MAX_QUESTION_CHARS:
        return False, "too_long"
    if INJECTION.search(q):
        return False, "injection"
    return True, ""


class TTLCache:
    def __init__(self, max_size=100, ttl=3600):
        self.max_size, self.ttl = max_size, ttl
        self._data = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(question: str, version: str) -> str:
        norm = " ".join(question.lower().split())
        return hashlib.sha256(f"{version}|{norm}".encode()).hexdigest()

    def get(self, key):
        item = self._data.get(key)
        if item and time.time() - item[0] < self.ttl:
            self._data.move_to_end(key)
            self.hits += 1
            return item[1]
        self._data.pop(key, None)
        self.misses += 1
        return None

    def set(self, key, value):
        self._data[key] = (time.time(), value)
        self._data.move_to_end(key)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)


RECENT = deque(maxlen=500)


def log_request(path, question, latency_ms, usage, cached, status):
    """One JSON line per request. Logs the length, not the text, for privacy."""
    usage = usage or {}
    row = {
        "path": path,
        "q_chars": len(question),
        "latency_ms": round(latency_ms),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cached": cached,
        "status": status,
    }
    RECENT.append(row)
    logger.info(json.dumps(row))


def summary():
    rows = list(RECENT)
    live = sorted(r["latency_ms"] for r in rows if r["status"] == "ok" and not r["cached"])
    hits = [r["latency_ms"] for r in rows if r["cached"]]
    if not rows:
        return {"requests": 0}
    def pick(p):
        return live[min(len(live) - 1, int(len(live) * p))] if live else None
    return {
        "requests": len(rows),
        "llm_calls": len(live),
        "p50_ms": pick(0.5),
        "p95_ms": pick(0.95),
        "cached_avg_ms": round(sum(hits) / len(hits)) if hits else None,
        "cache_hit_rate": round(len(hits) / len(rows), 2),
        "avg_prompt_tokens": round(sum(r["prompt_tokens"] for r in rows if not r["cached"]) / max(1, len(live))),
        "avg_completion_tokens": round(sum(r["completion_tokens"] for r in rows if not r["cached"]) / max(1, len(live))),
        "rejected": sum(1 for r in rows if r["status"] in ("too_short", "too_long", "injection")),
    }