import json
import os

from app.tools import scam_red_flag_score

BASE = os.path.dirname(os.path.dirname(__file__))
MAX_STEPS = 4

FALLBACK_ANSWER = (
    "I could not finish this check. If you think the message is a scam, do not click links "
    "or share any code, and call 1930 or report at cybercrime.gov.in."
)


def load_agent_prompt():
    path = os.path.join(BASE, "prompts", "agent_system.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_decision(reply):
    start = reply.find("{")
    end = reply.rfind("}")
    try:
        decision = json.loads(reply[start:end + 1])
    except ValueError:
        return None
    if not isinstance(decision, dict) or "action" not in decision:
        return None
    return decision


def ask_model(llm, system_prompt, transcript):
    try:
        return llm.ask(system_prompt, transcript)
    except RuntimeError as error:
        if "tool_use_failed" in str(error):
            return None
        raise


def run_tool(action, tool_input, rag):
    text = str(tool_input)

    if action == "scam_check":
        return scam_red_flag_score(text)

    if action == "search_documents":
        try:
            result = rag.ask(text)
        except RuntimeError as error:
            return {"error": str(error)}
        citations = []
        for c in result["citations"]:
            citations.append({"page": c["page"], "title": c["title"], "source": c["source"]})
        return {"answer": result["answer"], "known": result["known"], "citations": citations}

    return {"error": "unknown tool: " + str(action)}


class Agent:

    def __init__(self, llm, rag, max_steps=MAX_STEPS):
        self.llm = llm
        self.rag = rag
        self.max_steps = max_steps
        self.system_prompt = load_agent_prompt()

    def run(self, user_message):
        transcript = "User: " + user_message + "\n"
        steps = []

        for number in range(1, self.max_steps + 1):
            reply = ask_model(self.llm, self.system_prompt, transcript)
            decision = parse_decision(reply) if reply else None

            if decision is None:
                steps.append({"step": number, "action": "invalid reply"})
                transcript += "System: reply with plain text containing one JSON object only. Do not use function calling.\n"
                continue

            if decision["action"] == "final":
                return {"answer": str(decision.get("answer", "")), "steps": steps}

            observation = run_tool(decision["action"], decision.get("input", ""), self.rag)
            steps.append({
                "step": number,
                "action": decision["action"],
                "input": str(decision.get("input", ""))[:80],
                "result": observation,
            })
            transcript += "Assistant: " + json.dumps(decision) + "\n"
            transcript += "Result: " + json.dumps(observation) + "\n"

        return {"answer": FALLBACK_ANSWER, "steps": steps}


if __name__ == "__main__":
    from app.llm import LLM
    from app.rag import RAG
    from app.vectorstore import build_store

    llm = LLM()
    rag = RAG(build_store(600, 100), llm)
    agent = Agent(llm, rag)

    while True:
        message = input("\nPaste a message or ask a question (empty to quit): ").strip()
        if message == "":
            break
        result = agent.run(message)
        for step in result["steps"]:
            print("  step", step["step"], "->", step["action"], "|", str(step.get("result", ""))[:100])
        print("ANSWER:", result["answer"])