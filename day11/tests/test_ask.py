import json

from tests.conftest import FailingLLM, FakeLLM, FakeStore, make_hit

SIM_ANSWER = json.dumps({"answer": "A SIM swap is when fraudsters get a duplicate SIM.", "used": [1]})


def test_ask_answers_from_the_chunks_with_a_citation(make_client):
    llm = FakeLLM([SIM_ANSWER])
    client = make_client(store=FakeStore([make_hit(distance=0.4)]), llm=llm)

    body = client.post("/ask", json={"question": "What is a SIM swap scam?"}).json()

    assert body["known"] is True
    assert "duplicate SIM" in body["answer"]
    assert body["citations"][0]["page"] == 12
    assert "What is a SIM swap scam?" in llm.prompts[0]
    assert "A SIM swap is when fraudsters" in llm.prompts[0]


def test_ask_says_i_dont_know_when_no_chunk_is_close_enough(make_client):
    llm = FakeLLM([SIM_ANSWER])
    client = make_client(store=FakeStore([make_hit(distance=1.8)]), llm=llm)

    body = client.post("/ask", json={"question": "Has my bank refunded my money?"}).json()

    assert body["known"] is False
    assert body["answer"].startswith("I don't know")
    assert body["citations"] == []
    assert llm.prompts == []


def test_ask_says_i_dont_know_when_the_model_does(make_client):
    llm = FakeLLM([json.dumps({"answer": "I don't know.", "used": []})])
    client = make_client(store=FakeStore([make_hit(distance=0.4)]), llm=llm)

    body = client.post("/ask", json={"question": "Which section of the IT Act applies?"}).json()

    assert body["known"] is False
    assert body["citations"] == []


def test_ask_handles_a_reply_that_is_not_json(make_client):
    client = make_client(store=FakeStore([make_hit(distance=0.4)]), llm=FakeLLM(["sorry, no json here"]))
    body = client.post("/ask", json={"question": "What is a SIM swap scam?"}).json()
    assert body["known"] is False


def test_ask_returns_503_without_an_llm(make_client):
    assert make_client(llm=None).post("/ask", json={"question": "hello"}).status_code == 503


def test_ask_returns_502_when_the_llm_fails(make_client):
    client = make_client(store=FakeStore([make_hit(distance=0.4)]), llm=FailingLLM())
    response = client.post("/ask", json={"question": "What is a SIM swap scam?"})
    assert response.status_code == 502
    assert "rate limit" in response.json()["detail"]