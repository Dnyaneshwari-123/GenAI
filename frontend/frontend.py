"""CyberSuraksha web frontend (Streamlit). Talks to the deployed FastAPI service.

Run:  streamlit run frontend.py
Set the API address with the API_URL environment variable (or in the sidebar).
"""
import os

import requests
import streamlit as st
from chunking import chunk_records, compare

DEFAULT_API = os.getenv("API_URL", "https://genai-er7z.onrender.com")
SAMPLES = [
    "What precautions should I take before scanning a QR code?",
    "What are the warning signs of a SIM-swap scam?",
    "How can I identify a fake customer-care number?",
    "What should I do if someone asks me to install a screen-sharing app?",
]
LABEL = {
    "high": ":green[**High confidence**]",
    "medium": ":orange[**Partly covered by our records**]",
    "low": ":gray[**Not covered by our records**]",
}

st.set_page_config(page_title="CyberSuraksha", page_icon="🛡️", layout="centered")


def level(confidence):
    """v1 sometimes returns a number, v2 returns high/medium/low."""
    if isinstance(confidence, (int, float)):
        return "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
    text = str(confidence or "low").lower()
    return text if text in ("high", "medium") else "low"


@st.cache_data(ttl=30, show_spinner=False)
def get_json(base, path):
    response = requests.get(base + path, timeout=90)
    response.raise_for_status()
    return response.json()


def explain(status, body):
    detail = body.get("detail") if isinstance(body, dict) else None
    if status == 422:
        return "Questions must be between 3 and 500 characters."
    if status == 400:
        return detail if isinstance(detail, str) else "That question was rejected."
    if status == 503:
        return "The language model is not set up on the server. Check the API key."
    if status == 502:
        return "The language model service failed, often a rate limit. Wait a few seconds and try again."
    return f"Something went wrong (code {status}). Try again."


def ask(api, version, question):
    try:
        response = requests.post(
            f"{api}/chat",
            json={"question": question, "prompt_version": version},
            timeout=90,
        )
    except requests.RequestException:
        return {"error": "Could not reach the server. Check the API URL and your connection."}
    try:
        body = response.json()
    except ValueError:
        body = {}
    return body if response.ok else {"error": explain(response.status_code, body)}


def show_reply(reply):
    if "error" in reply:
        st.error(reply["error"])
        return
    lv = level(reply.get("confidence"))
    st.markdown(LABEL[lv])
    st.write(reply.get("answer", ""))
    if lv == "low":
        st.caption("Check with your bank, call 1930, or report at cybercrime.gov.in.")
    if reply.get("follow_up"):
        st.caption("💬 " + reply["follow_up"])
    if lv != "low" and reply.get("matched"):
        st.caption("Records used: " + ", ".join(reply["matched"]))


# ---------- sidebar: server status, options, stats ----------
with st.sidebar:
    st.header("Server")
    api = st.text_input("API URL", DEFAULT_API).rstrip("/")
    version = st.selectbox("Prompt version", ["v2", "v1"], help="v2 gives short answers with a fixed confidence format.")
    try:
        with st.spinner("Contacting the server. The free tier can take a minute to wake up…"):
            health = get_json(api, "/health")
        if health.get("llm_ready"):
            st.success(f"Online · {health.get('mode', 'full')} mode · {health['records']} records")
        else:
            st.warning("Online, but the language model is not ready.")
    except (requests.RequestException, ValueError, KeyError):
        st.error("Server unreachable.")

    if st.button("Show server stats"):
        try:
            stats = requests.get(f"{api}/metrics", timeout=30).json()
            st.metric("Requests", stats.get("requests", 0))
            st.metric("Median LLM call", f"{stats['p50_ms']} ms" if stats.get("p50_ms") is not None else "n/a")
            st.metric("Cache hit rate", f"{round(stats.get('cache_hit_rate', 0) * 100)}%")
            st.metric("Avg tokens in / out", f"{stats.get('avg_prompt_tokens', 0)} / {stats.get('avg_completion_tokens', 0)}")
        except (requests.RequestException, ValueError):
            st.error("Stats are not available.")

# ---------- main page ----------
st.title("🛡️ CyberSuraksha")
st.write("Ask what to do after an online fraud. Answers come only from the RBI BE(A)WARE fraud records.")

tab_ask, tab_chunks = st.tabs(["Ask", "How the records are chunked"])

with tab_ask:
    st.warning("Lost money to a scam? Call **1930** right away, then report at cybercrime.gov.in.", icon="🚨")

    if "chat" not in st.session_state:
        st.session_state.chat = []

    history = st.container()
    typed = st.chat_input("Ask about an online fraud…", max_chars=500)
    question = typed or st.session_state.pop("pending", None)

    if question:
        if len(question.strip()) < 3:
            st.warning("Please type at least 3 characters.")
        else:
            st.session_state.chat.append({"role": "user", "content": question.strip()})
            with st.spinner("Looking through the records…"):
                reply = ask(api, version, question.strip())
            st.session_state.chat.append({"role": "assistant", "content": reply})

    with history:
        if not st.session_state.chat:
            st.caption("Pick a question or type your own.")
            for number, sample in enumerate(SAMPLES):
                st.button(sample, key=f"s{number}", on_click=lambda s=sample: st.session_state.update(pending=s))
        for message in st.session_state.chat:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    show_reply(message["content"])

with tab_chunks:
    st.write(
        "Before the assistant can search the records, each record is cut into small overlapping chunks. "
        "Change the settings to see how many chunks you get."
    )
    try:
        records = get_json(api, "/records?limit=100")
    except (requests.RequestException, ValueError):
        records = None
        st.error("Could not load the records from the server.")

    if records:
        left, right = st.columns(2)
        size = left.slider("Chunk size (characters)", 100, 1200, 600, 50)
        overlap = right.slider("Overlap (characters)", 0, 300, 100, 25)

        if overlap >= size:
            st.error("Overlap must be smaller than the chunk size.")
        else:
            chunks = chunk_records(records, size, overlap)
            st.metric(f"Chunks with size {size} and overlap {overlap}", len(chunks))

            st.subheader("Compared with the two tested setups")
            st.dataframe(
                compare(records, [("A: 600 / 100", 600, 100), ("B: 300 / 50", 300, 50)]),
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Counts are computed here from each record's text, so they can differ from the "
                "server's search index. In the evaluation, config B passed 15/15 questions and config A 14/15."
            )

            st.subheader("Look at one record")
            names = [r["fraud_name"] for r in records]
            chosen = st.selectbox("Record", names)
            for chunk in [c for c in chunks if c["record"] == chosen]:
                with st.expander(f"Chunk {chunk['part']} ({len(chunk['text'])} characters)"):
                    st.write(chunk["text"])
