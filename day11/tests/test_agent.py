import json

from app.agent_loop import Agent, parse_decision, run_tool
from tests.conftest import FakeLLM, FakeStore, make_hit

KYC_SMS = "Dear customer, your SBI KYC will expire today. Update immediately at bit.ly/sbi-kyc or your account will be blocked."


def decision(action, **fields):
    return json.dumps({"action": action, **fields})


def test_run_tool_scam_check_scores_the_message():
    result = run_tool("scam_check", KYC_SMS, rag=None)
    assert result["score"] == 70


def test_run_tool_rejects_an_unknown_action():
    assert "error" in run_tool("delete_everything", "x", rag=None)


def test_parse_decision_accepts_json_inside_text_and_rejects_junk():
    assert parse_decision('Sure! {"action": "final", "answer": "ok"}')["action"] == "final"
    assert parse_decision("no json here") is None
    assert parse_decision('{"no_action": 1}') is None


def test_agent_loop_uses_the_tool_then_answers():
    llm = FakeLLM([decision("scam_check", input=KYC_SMS), decision("final", answer="This is a scam.")])
    result = Agent(llm, rag=None).run("Is this real? " + KYC_SMS)
    assert result["answer"] == "This is a scam."
    assert [step["action"] for step in result["steps"]] == ["scam_check"]
    assert "Result:" in llm.prompts[1]


def test_agent_loop_recovers_from_an_invalid_reply():
    llm = FakeLLM(["not json", decision("final", answer="Done.")])
    result = Agent(llm, rag=None).run("hello")
    assert result["answer"] == "Done."
    assert result["steps"][0]["action"] == "invalid reply"


def test_agent_loop_stops_after_the_step_limit():
    llm = FakeLLM([decision("scam_check", input="x")] * 6)
    result = Agent(llm, rag=None, max_steps=3).run("hello")
    assert "could not finish" in result["answer"]
    assert len(result["steps"]) == 3


def test_agent_endpoint_pauses_for_approval_on_a_high_risk_message(make_client):
    llm = FakeLLM([decision("scam_check", input=KYC_SMS), decision("final", answer="This is a scam. Do not click.")])
    client = make_client(store=FakeStore([make_hit()]), llm=llm)

    first = client.post("/agent", json={"message": KYC_SMS}).json()
    assert first["status"] == "needs_approval"
    assert first["pending"]["risk_score"] == 70

    done = client.post("/agent", json={"thread_id": first["thread_id"], "approve": True}).json()
    assert done["status"] == "done"
    assert done["approved"] is True
    assert done["answer"] == "This is a scam. Do not click."


def test_agent_endpoint_replaces_a_rejected_answer(make_client):
    llm = FakeLLM([decision("scam_check", input=KYC_SMS), decision("final", answer="Draft answer.")])
    client = make_client(llm=llm)

    first = client.post("/agent", json={"message": KYC_SMS}).json()
    done = client.post("/agent", json={"thread_id": first["thread_id"], "approve": False}).json()

    assert done["approved"] is False
    assert "did not approve" in done["answer"]


def test_agent_endpoint_needs_no_approval_for_a_low_risk_question(make_client):
    client = make_client(llm=FakeLLM([decision("final", answer="A SIM swap is...")]))
    body = client.post("/agent", json={"message": "What is a SIM swap?"}).json()
    assert body["status"] == "done"
    assert body["approved"] is None


def test_agent_endpoint_rejects_an_approval_when_nothing_is_waiting(make_client):
    client = make_client(llm=FakeLLM())
    assert client.post("/agent", json={"thread_id": "nope", "approve": True}).status_code == 400