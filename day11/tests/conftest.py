import json
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class FakeStore:
    """Stands in for the Chroma vector store, so the tests need no model and no database."""

    def __init__(self, hits=None):
        self.hits = hits if hits is not None else []

    def count(self):
        return len(self.hits)

    def search(self, query, n=3):
        return self.hits[:n]


class FakeLLM:
    """Returns scripted replies and remembers the prompts it was given."""

    def __init__(self, replies=None):
        self.replies = list(replies or [])
        self.prompts = []

    def ask(self, system_prompt, user_prompt):
        self.prompts.append(user_prompt)
        return self.replies.pop(0)


class FailingLLM:
    """Simulates the real LLM failing, for example a rate limit."""

    def ask(self, system_prompt, user_prompt):
        raise RuntimeError("Groq error 429: rate limit")


def make_hit(chunk_id="beaware-p12-c0", page=12, distance=0.5, text="A SIM swap is when fraudsters get a duplicate SIM."):
    return {
        "id": chunk_id,
        "text": text,
        "title": "BE(A)WARE",
        "page": page,
        "source": "https://example.org/beaware.pdf",
        "distance": distance,
    }


@pytest.fixture
def records():
    with open(ROOT / "data" / "records.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def make_client(monkeypatch):
    """Builds the real FastAPI app with a fake vector store and a fake LLM."""

    def build(store=None, llm=None):
        fake_vectorstore = types.ModuleType("app.vectorstore")
        fake_vectorstore.build_store = lambda *args, **kwargs: store or FakeStore([make_hit()])
        monkeypatch.setitem(sys.modules, "app.vectorstore", fake_vectorstore)

        fake_llm_module = types.ModuleType("app.llm")
        if llm is None:
            def no_llm(*args, **kwargs):
                raise ValueError("API key or model is missing")

            fake_llm_module.LLM = no_llm
        else:
            fake_llm_module.LLM = lambda *args, **kwargs: llm
        monkeypatch.setitem(sys.modules, "app.llm", fake_llm_module)

        monkeypatch.delitem(sys.modules, "app.main", raising=False)
        import app.main as main_module

        return TestClient(main_module.app)

    yield build
    sys.modules.pop("app.main", None)