import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "app.py")


class FakeResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.text = json.dumps(data)

    def json(self):
        return self._data


def fake_post(url, json=None, timeout=None):
    if url.endswith("/ask"):
        if "refunded" in json["question"]:
            return FakeResponse({"answer": "I don't know. The documents I have do not answer this question.",
                                 "known": False, "citations": []})
        return FakeResponse({"answer": "A SIM swap is when fraudsters get a duplicate SIM.", "known": True,
                             "citations": [{"number": 1, "chunk_id": "a", "title": "BE(A)WARE", "page": 12,
                                            "source": "https://example.org/b.pdf"}]})
    return FakeResponse({"detail": "nope"}, 500)


def test_xray_page_shows_red_marks_and_pattern():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="page").set_value("🔍 Scam X-ray").run()
    at.text_area(key="xray_text").set_value("Your SBI KYC will expire today. Update immediately at bit.ly/x").run()
    assert not at.exception
    page = " ".join(m.value for m in at.markdown)
    assert "<mark" in page and "HIGH RISK" in page
    assert any("Phishing links" in s.value for s in at.subheader)
    assert "Call 1930 now" not in page


def test_call_1930_card_appears_when_money_is_lost():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="page").set_value("🔍 Scam X-ray").run()
    at.text_area(key="xray_text").set_value("I entered my PIN and 5000 was debited from my account").run()
    assert "Call 1930 now" in " ".join(m.value for m in at.markdown)


def test_call_1930_card_appears_with_the_checkbox():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="page").set_value("🔍 Scam X-ray").run()
    at.text_area(key="xray_text").set_value("Update your KYC at bit.ly/x").run()
    assert "Call 1930 now" not in " ".join(m.value for m in at.markdown)
    at.checkbox(key="xray_lost").check().run()
    assert "Call 1930 now" in " ".join(m.value for m in at.markdown)


def test_chat_answers_with_citation_and_saves_feedback(monkeypatch):
    monkeypatch.setattr(requests, "post", fake_post)
    feedback = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "feedback.jsonl")
    before = open(feedback).read() if os.path.exists(feedback) else ""
    try:
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.chat_input[0].set_value("What is a SIM swap?").run()
        assert not at.exception
        assert any("duplicate SIM" in m.value for m in at.markdown)
        assert len(at.expander) == 1
        at.button(key="up_2").click().run()
        rows = open(feedback).read().strip().split("\n")
        assert json.loads(rows[-1])["rating"] == "up"
    finally:
        if before:
            open(feedback, "w").write(before)
        elif os.path.exists(feedback):
            os.remove(feedback)


def test_chat_says_i_dont_know_for_the_refund_question(monkeypatch):
    monkeypatch.setattr(requests, "post", fake_post)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.chat_input[0].set_value("Has my bank refunded the money I lost in a UPI fraud?").run()
    assert any("I don't know" in m.value for m in at.markdown)
    assert len(at.expander) == 0


def test_chat_shows_a_friendly_error_when_the_api_is_down(monkeypatch):
    def broken(url, json=None, timeout=None):
        raise requests.exceptions.ConnectionError()
    monkeypatch.setattr(requests, "post", broken)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.chat_input[0].set_value("hello").run()
    assert not at.exception
    assert any("cannot reach the CyberSuraksha API" in m.value for m in at.markdown)