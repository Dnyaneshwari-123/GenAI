import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.records import load_records  # noqa: E402
from ui.xray import LEVEL_COLOR, call_1930_html, run_xray  # noqa: E402

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
FEEDBACK_FILE = ROOT / "data" / "feedback.jsonl"

SAMPLES = {
    "Fake KYC SMS": "Dear customer, your SBI KYC will expire today. Update immediately at bit.ly/sbi-kyc or your account will be blocked.",
    "Lottery": "Congratulations! You won a lottery of Rs 25,00,000. Pay a processing fee of Rs 5,000 to claim your prize.",
    "AnyDesk call": "Hi, I am from your bank. Please install AnyDesk and tell me the 9-digit code. Also share your OTP to stop the block.",
    "Money already lost": "I got a message to approve a collect request on my UPI app to receive a refund. I entered my UPI PIN and Rs 5000 was debited from my account.",
    "Genuine bank OTP": "Your OTP is 482913. Do not share it with anyone. - HDFC Bank",
}

st.set_page_config(page_title="CyberSuraksha", page_icon="🛡️", layout="wide")


def init_state():
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("thread_id", None)
    st.session_state.setdefault("pending", None)
    st.session_state.setdefault("pending_question", "")
    st.session_state.setdefault("rated", {})
    st.session_state.setdefault("next_id", 1)
    st.session_state.setdefault("xray_text", "")


def call_api(path, payload):
    try:
        response = requests.post(API_URL + path, json=payload, timeout=90)
    except requests.exceptions.RequestException:
        return None, "I cannot reach the CyberSuraksha API at " + API_URL + ". Start it with: uvicorn app.main:app --reload"
    if response.status_code != 200:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        return None, "API error " + str(response.status_code) + ": " + str(detail)[:300]
    return response.json(), None


def add_message(role, content, citations=None, question="", mode="", known=None):
    message = {
        "id": st.session_state.next_id,
        "role": role,
        "content": content,
        "citations": citations or [],
        "question": question,
        "mode": mode,
        "known": known,
    }
    st.session_state.next_id += 1
    st.session_state.messages.append(message)


def save_feedback(message, rating):
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "mode": message["mode"],
        "question": message["question"][:300],
        "answer": message["content"][:500],
        "sources": len(message["citations"]),
        "rating": rating,
    }
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rate(message_id, rating):
    for message in st.session_state.messages:
        if message["id"] == message_id:
            save_feedback(message, rating)
            st.session_state.rated[message_id] = rating


def feedback_counts():
    up = 0
    down = 0
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    rating = json.loads(line)["rating"]
                except (ValueError, KeyError):
                    continue
                if rating == "up":
                    up += 1
                elif rating == "down":
                    down += 1
    return up, down


def show_citations(citations):
    seen = set()
    lines = []
    for c in citations:
        key = (c["page"], c["source"])
        if key in seen:
            continue
        seen.add(key)
        lines.append("- **Page " + str(c["page"]) + "** · [" + c["title"] + "](" + c["source"] + "#page=" + str(c["page"]) + ")")
    if lines:
        with st.expander("📚 Sources (" + str(len(lines)) + ")"):
            st.markdown("\n".join(lines))


def ask_backend(question, mode):
    if mode == "Ask (RAG)":
        data, error = call_api("/ask", {"question": question})
        if error:
            return error, [], None
        return data["answer"], data.get("citations", []), data.get("known")

    payload = {"message": question}
    if st.session_state.thread_id:
        payload["thread_id"] = st.session_state.thread_id
    data, error = call_api("/agent", payload)
    if error:
        return error, [], None
    st.session_state.thread_id = data["thread_id"]
    if data["status"] == "needs_approval":
        st.session_state.pending = data
        st.session_state.pending_question = question
        return None, [], None
    return data["answer"], data.get("citations", []), None


def finish_approval(approve):
    pending = st.session_state.pending
    question = st.session_state.pending_question
    st.session_state.pending = None
    data, error = call_api("/agent", {"thread_id": pending["thread_id"], "approve": approve})
    if error:
        add_message("assistant", error, question=question, mode="Agent (LangGraph)")
    else:
        add_message("assistant", data["answer"], data.get("citations", []), question=question, mode="Agent (LangGraph)")


def chat_page():
    st.header("💬 Ask CyberSuraksha")
    st.caption("Answers come from the RBI BE(A)WARE booklet, with page citations. If the booklet does not answer, I say so.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                if message["known"] is False:
                    st.caption("ℹ️ No passage in the booklet supports an answer, so I said \"I don't know\".")
                show_citations(message["citations"])
                if message["id"] in st.session_state.rated:
                    icon = "👍" if st.session_state.rated[message["id"]] == "up" else "👎"
                    st.caption("Thanks, your feedback " + icon + " was saved.")
                else:
                    c1, c2, _ = st.columns([1, 1, 8])
                    c1.button("👍", key="up_" + str(message["id"]), on_click=rate, args=(message["id"], "up"))
                    c2.button("👎", key="down_" + str(message["id"]), on_click=rate, args=(message["id"], "down"))

    pending = st.session_state.pending
    if pending:
        info = pending["pending"]
        st.warning(
            "**Reviewer approval needed.** Risk score " + str(info["risk_score"])
            + " (" + ", ".join(info["fired_rules"]) + ").\n\n**Draft answer:** " + info["draft_answer"]
        )
        a, b, _ = st.columns([1, 1, 6])
        a.button("✅ Approve", on_click=finish_approval, args=(True,), key="approve_btn")
        b.button("⛔ Reject", on_click=finish_approval, args=(False,), key="reject_btn")

    prompt = st.chat_input("Ask about a scam, or paste a message...", disabled=pending is not None)
    if prompt:
        mode = st.session_state.mode
        add_message("user", prompt)
        with st.spinner("Searching the booklet..."):
            answer, citations, known = ask_backend(prompt, mode)
        if answer is not None:
            add_message("assistant", answer, citations, question=prompt, mode=mode, known=known)
        st.rerun()


def set_sample(text):
    st.session_state.xray_text = text


def xray_page(records):
    st.header("🔍 Scam X-ray")
    st.caption("Paste an SMS, WhatsApp or email text. This check runs on your computer and the text is not sent to any API.")

    columns = st.columns(len(SAMPLES))
    for column, (name, text) in zip(columns, SAMPLES.items()):
        column.button(name, key="sample_" + name, on_click=set_sample, args=(text,), use_container_width=True)

    text = st.text_area("Message to check", key="xray_text", height=160, placeholder="Paste the message here, then press Ctrl+Enter")
    lost_checked = st.checkbox("I already paid money or shared an OTP / PIN", key="xray_lost")

    if not text.strip():
        st.info("Paste a message or pick an example above.")
        return

    result = run_xray(text, records, lost_checked)

    if result["lost"]:
        st.markdown(call_1930_html(), unsafe_allow_html=True)

    left, right = st.columns([1, 2])
    with left:
        color = LEVEL_COLOR[result["level"]]
        st.markdown(
            '<div style="text-align:center;border:2px solid ' + color + ';border-radius:16px;padding:16px">'
            '<div style="font-size:14px;letter-spacing:2px">RISK SCORE</div>'
            '<div style="font-size:80px;font-weight:800;color:' + color + ';line-height:1.1">' + str(result["score"]) + "</div>"
            '<div style="font-size:20px;font-weight:700;color:' + color + '">' + result["level"].upper() + " RISK</div></div>",
            unsafe_allow_html=True,
        )
        st.write(result["advice"])
    with right:
        st.subheader("Your message, with risky phrases in red")
        st.markdown(
            '<div style="border:1px solid #cccccc;border-radius:12px;padding:16px;line-height:1.9;font-size:17px">'
            + result["html"] + "</div>",
            unsafe_allow_html=True,
        )
        if result["hits"]:
            counts = {}
            for hit in result["hits"]:
                counts[hit["category"]] = counts.get(hit["category"], 0) + 1
            st.write("  ".join("🔴 **" + name + "** × " + str(n) for name, n in counts.items()))
        else:
            st.success("No risky phrases found.")

    if result["fired"]:
        st.subheader("Rules that fired")
        st.table([{"Rule": r["rule"], "Points": r["weight"], "Matched text": r["matched"]} for r in result["fired"]])

    pattern = result["pattern"]
    if pattern:
        st.subheader("Matched fraud pattern: " + pattern["fraud_name"])
        st.write("**How it works:** " + pattern["how_it_works"])
        st.write("**What to do:** " + pattern["precautions"])
        st.caption("Source: [RBI BE(A)WARE booklet](" + pattern["source_url"] + ")")
    elif result["score"] < 25:
        st.info("No known fraud pattern matched. This does not prove the message is safe. If unsure, call your bank on the number printed on your card.")

    st.caption("This is a rule-based check. It can miss new scams and can flag harmless messages. 1930 is the National Cyber Crime Helpline.")


init_state()
records = load_records()

with st.sidebar:
    st.title("🛡️ CyberSuraksha")
    page = st.radio("Page", ["💬 Chat", "🔍 Scam X-ray"], key="page")
    st.radio("Chat engine", ["Ask (RAG)", "Agent (LangGraph)"], key="mode",
             help="Ask uses POST /ask. Agent uses POST /agent with memory and a reviewer approval step.")
    if st.button("New conversation"):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.session_state.pending = None
        st.rerun()
    up, down = feedback_counts()
    st.metric("Feedback saved", str(up + down), "👍 " + str(up) + "   👎 " + str(down), delta_color="off")
    st.caption("API: " + API_URL)

if page == "💬 Chat":
    chat_page()
else:
    xray_page(records)