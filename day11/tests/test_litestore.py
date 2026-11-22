import json
import sys
import types

from fastapi.testclient import TestClient

from app.litestore import LiteStore

CHUNKS = [
    {"id": "a", "text": "Fraudsters get a duplicate SIM card and use the OTP", "title": "T", "page": 7, "source": "http://x"},
    {"id": "b", "text": "Scanning a QR code can take money out of your account", "title": "T", "page": 9, "source": "http://x"},
    {"id": "c", "text": "Fake websites steal passwords from customers", "title": "T", "page": 6, "source": "http://x"},
]


def test_lite_store_ranks_the_matching_chunk_first():
    hits = LiteStore(CHUNKS).search("duplicate SIM card", n=2)
    assert hits[0]["id"] == "a"
    assert len(hits) == 2
    assert hits[0]["distance"] < hits[1]["distance"]


def test_lite_store_has_the_same_interface_as_the_vector_store():
    store = LiteStore(CHUNKS)
    assert store.count() == 3
    assert set(store.search("QR code")[0]) == {"id", "text", "title", "page", "source", "distance"}


def test_unrelated_query_has_the_largest_distance():
    assert LiteStore(CHUNKS).search("zzzz qqqq")[0]["distance"] == 1.0


def _client(monkeypatch, lite):
    fake_llm = types.ModuleType("app.llm")

    class FakeLLM:
        def ask(self, system_prompt, user_prompt):
            return json.dumps({"answer": "A SIM swap is a duplicate SIM.", "used": [1]})

    fake_llm.LLM = FakeLLM
    monkeypatch.setitem(sys.modules, "app.llm", fake_llm)
    if lite:
        monkeypatch.setenv("LITE_MODE", "1")
    else:
        monkeypatch.delenv("LITE_MODE", raising=False)
        fake_store = types.ModuleType("app.vectorstore")
        fake_store.build_store = lambda *a, **k: LiteStore(CHUNKS)
        monkeypatch.setitem(sys.modules, "app.vectorstore", fake_store)
    monkeypatch.delitem(sys.modules, "app.main", raising=False)
    import app.main as main_module

    return TestClient(main_module.app)


def test_health_reports_lite_mode(monkeypatch):
    body = _client(monkeypatch, lite=True).get("/health").json()
    assert body["mode"] == "lite"
    assert body["chunks"] > 0


def test_health_reports_full_mode_by_default(monkeypatch):
    body = _client(monkeypatch, lite=False).get("/health").json()
    assert body["mode"] == "full"