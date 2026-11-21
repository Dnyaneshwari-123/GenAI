# CyberSuraksha — Project Card

**Name:** Dnyaneshwari Kale
**Project:** SJ-46 · Law (Cyber)

## Product
CyberSuraksha is a GenAI assistant that explains cyber law and tells people what to do after an online incident.

## User
Citizens and students who face online fraud, hacking or harassment.

## Problem
People don't know which law applies, where to report, or how fast to act. Because of this, they lose money and evidence.

## Data Source
- National Cyber Crime Reporting Portal (cybercrime.gov.in)
- 1930 cyber fraud helpline guidance

## Files
- `day01_intro.py`: prints the project card and asks for the user's name and question
- `day01_menu.py`: menu with about, sample questions, a rule check and exit

Security note: a Gemini key was committed by mistake in .env.example and was revoked on 16 Nov 2026. Real keys now live only in .env, which is gitignored.
Winner: Config B (chunk size 300, overlap 50, top-k 5), passing 15/15 against 14/15 for Config A (600/100, top-k 3).

The only difference was Q5 (“Why should I never share my OTP with a caller who says he is from my bank?”). With 600-character chunks and top-k 3, retrieval returned the OTP-based NBFC fraud section and an unrelated NEFT chunk, and missed the vishing section that actually answers the question. With 300-character chunks and top-k 5, the vishing passage was retrieved, so the check passed.

Both configs answered all three out-of-scope questions (Q13 to Q15) with “I don’t know” and cited sources for every answerable question. Smaller chunks plus a larger top-k improved coverage on this booklet, where each fraud type has a short, self-contained section. The trade-off is that top-k 5 passes more text to the LLM, which raises cost and the chance of noisy context.

Limitations: the eval is only 15 questions, retrieval is judged by keyword matching, and the winner is chosen by pass count, then retrieval hits, then smaller top-k.
## Day 10: Streamlit UI and Scam X-ray
cd day10
uvicorn app.main:app --reload        (terminal 1: the API)
streamlit run ui/app.py              (terminal 2: the UI)
python -m pytest tests -q            (19 tests)

![Scam X-ray](day10/docs/xray.png)
![Chat with citations](day10/docs/chat.png)
![I don't know for Q6](day10/docs/idk.png)

- Chat calls POST /ask or POST /agent, shows page-linked citations and saves 👍/👎 to data/feedback.jsonl.
- Scam X-ray runs locally: risk score, risky phrases in red (OTP, KYC, urgent, link, prize), the matched fraud pattern from the records, and a Call 1930 card when money is already lost.
- Limits: the X-ray uses fixed regex rules, so it can miss new scams. Money-lost detection reads first-person phrases such as "I paid" or "was debited", plus a checkbox.
- Privacy: the X-ray sends nothing to an API. Do not type real personal data in the chat, because questions are saved with the feedback.
## Day 11: Tests, linting and Docker

### Run the tests
    cd day11
    python -m pip install -r requirements-dev.txt
    python -m pytest          (63 tests, no API key or internet needed)
    ruff check .
    python -m mypy app/tools.py app/records.py ui/xray.py

The tests use a fake vector store and a fake LLM, so they cover the real FastAPI app, the RAG
class, the scam-score tool and the agent loop without any network call.

### Run with Docker
Needs Docker Desktop.

    cd day11
    copy .env.example .env      (then put your own Groq key in .env)
    docker compose up --build

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs
- Stop: Ctrl+C, then `docker compose down`

The first start takes a few minutes (build, then building the vector index). The index is kept
in a Docker volume, so later starts are fast. Without a key the stack still starts and the
Scam X-ray works, but the chat cannot answer.