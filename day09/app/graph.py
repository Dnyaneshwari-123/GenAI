import json
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agent_loop import FALLBACK_ANSWER, MAX_STEPS, load_agent_prompt, parse_decision, run_tool

HIGH_RISK = 60

REJECTED_ANSWER = (
    "The reviewer did not approve the draft answer. To be safe, do not click links, "
    "reply or share any code. Call 1930 or report at cybercrime.gov.in."
)


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    decision: dict
    steps: int
    answer: str
    risk: dict
    approved: bool


def build_graph(llm, rag):
    system_prompt = load_agent_prompt()

    def agent_node(state):
        reply = llm.ask(system_prompt, "\n".join(state["messages"]))
        decision = parse_decision(reply)

        if decision is None:
            return {
                "decision": {"action": "retry"},
                "steps": state["steps"] + 1,
                "messages": ["System: reply with one JSON object only."],
            }

        update = {
            "decision": decision,
            "steps": state["steps"] + 1,
            "messages": ["Assistant: " + json.dumps(decision)],
        }
        if decision["action"] == "final":
            update["answer"] = str(decision.get("answer", ""))
        return update

    def tool_node(state):
        decision = state["decision"]
        observation = run_tool(decision["action"], decision.get("input", ""), rag)
        update = {"messages": ["Tool result: " + json.dumps(observation)]}
        if decision["action"] == "scam_check" and "score" in observation:
            update["risk"] = observation
        return update

    def approval_node(state):
        answer = state.get("answer") or FALLBACK_ANSWER
        risk = state.get("risk")
        high_risk = bool(risk) and risk["score"] >= HIGH_RISK

        if not high_risk:
            return {"answer": answer, "approved": None}

        human_says = interrupt({
            "message": "This message looks high risk. Approve this answer before it is shown?",
            "risk_score": risk["score"],
            "fired_rules": [item["rule"] for item in risk["fired"]],
            "draft_answer": answer,
        })

        if human_says is True:
            return {"answer": answer, "approved": True,
                    "messages": ["System: the reviewer approved the answer."]}
        return {"answer": REJECTED_ANSWER, "approved": False,
                "messages": ["System: the reviewer rejected the draft answer."]}

    def route_after_agent(state):
        action = state["decision"].get("action")
        if action == "final":
            return "approval"
        if state["steps"] >= MAX_STEPS:
            return "approval"
        if action == "retry":
            return "agent"
        return "tools"

    def route_after_tools(state):
        if state["steps"] >= MAX_STEPS:
            return "approval"
        return "agent"

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_node("approval", approval_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_agent,
                                  {"tools": "tools", "agent": "agent", "approval": "approval"})
    builder.add_conditional_edges("tools", route_after_tools,
                                  {"agent": "agent", "approval": "approval"})
    builder.add_edge("approval", END)

    return builder.compile(checkpointer=InMemorySaver())