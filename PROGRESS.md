# PROGRESS: CyberSuraksha

Live demo: https://genai-er7z.onrender.com (health check at `/health`, API docs at `/docs`)

Rule: an item is `[x]` only when its proof exists in the repo or in a measured number.

## Day 1: Project card and menu
- [x] `day01_intro.py` prints the project card and asks for the user's name and question
- [x] `day01_menu.py` offers about, sample questions, a rule check and exit
- [x] README project card: product, user, problem, data source

## Day 2: Command-line tool over sample records
- [x] `day02/app/cli.py` and `records.py` work on `data/sample_records.json`

## Day 3: Collecting and structuring the data
- [x] `day03/app/fetch.py` downloads the sources: the BE(A)WARE PDF, a consumer awareness page and an RBI press release (`data/raw/`)
- [x] `day03/app/ingest.py` and `models.py` turn them into `data/records.json`
- [x] Text is extracted from the 39-page pictorial PDF with pypdf and saved in `data/raw/beaware_text.txt`

## Day 4: Search API and data exploration
- [x] `day04/analysis/explore.py` explores the records
- [x] `day04/app/main.py` and `smart_search.py` serve keyword search over the records

## Day 5: User questions
- [x] `day05/docs/user_questions.json` holds the 10 user questions reused by the Day 6 prompt evaluation

## Day 6: Prompt evaluation and key safety
- [x] `prompts/system.txt`, `task_v1.txt`, `task_v2.txt`
- [x] `eval/run_eval.py` retries on errors and never saves an error response
- [x] `eval/results.json` holds 20 real answers (10 questions x v1 and v2)
- [x] `eval/prompt_compare.md` table filled, winner v2 (valid confidence format 10/10 against 4/10)
- [x] Old Gemini key revoked on 16 Nov 2026 (GitHub and Google AI Studio); `.env` is gitignored

## Day 7: Embeddings and vector search
- [x] `day07/app/chunking.py`, `embed.py` and `vectorstore.py` (Chroma) build the search index from the PDF
- [x] `day07/eval/run_search.py` records the results in `search_results.md`

## Day 8: RAG with an evaluation
- [x] `day08/app/rag.py` answers from retrieved chunks, with RAG prompts in `prompts/`
- [x] 15-question evaluation set (12 answerable, 3 not answerable) in `eval/eval_set.json`, run by `run_eval.py`, with threshold tuning in `tune_threshold.py`
- [x] Config A (600/100, top-k 3): 14/15 passed, retrieval hit 11/12. Config B (300/50, top-k 5): 15/15 passed, retrieval hit 12/12. Both had 0 errors and 12/12 cited answers
- [x] Winner: config B. The only difference was question 5 (OTP), where config A found no matching chunk
- [x] Results in `eval_results.json` and `winner_table.md`

## Day 9: Agent
- [x] `day09/app/agent_loop.py`, `graph.py` and `tools.py` implement the tool-using agent
- [ ] `day09/demo.md` filled from a real run of the agent

## Day 10: Streamlit UI and Scam X-ray
- [x] Chat with page-linked citations and thumbs up/down saved to `data/feedback.jsonl`
- [x] Scam X-ray: risk score, risky phrases, matched fraud pattern, Call 1930 card

## Day 11: Tests, linting and Docker
- [x] 71 pytest tests with a fake vector store and a fake LLM (no network needed)
- [x] ruff and mypy checks
- [x] Dockerfile and `docker compose up --build`

## Day 12: CI and deployment
- [x] `.github/workflows/ci.yml` runs ruff, pytest and a Docker build
- [x] CI badge in the README
- [x] PR #1 merged
- [x] Deployed on Render as a Docker service (`Dockerfile.render`, lite mode, free plan)
- [x] `/health` works publicly and returns `llm_ready: true`
- [x] Live URL in the README

## Day 13: Production hardening and README
- [x] `app/prod.py`: input limits (3 to 500 characters), prompt-injection guard, TTL cache, latency and token logging
- [x] `/metrics` endpoint and `scripts/bench.py`
- [x] `tests/test_prod.py` includes the prompt-injection test
- [x] README "Production notes" with measured numbers (median 1,973 ms, p95 2,370 ms, cache hit about 21 ms, about 839 / 254 tokens)
- [x] README problem, Mermaid architecture diagram and results table
- [x] `docs/resume.md` with 3 resume bullets
- [x] Streamlit frontend in `frontend/` (`frontend.py` and `chunking.py`)
- [ ] Demo video link added to the README

## Day 14: Interview preparation
- [x] `docs/interview.md`: 60-second pitch, hardest-problem story, 10 questions and answers
- [ ] Hinglish test result checked and recorded (`bank wala bola app daalo`)
- [ ] Demo rehearsed twice
- [ ] Final tag `final` pushed

## Day 15: Final test and demo day
- [ ] Final test (45 minutes)
- [ ] 5-minute live demo and 3-minute Q&A

## Release checks
- [ ] CI is green on pull request #3
- [ ] Pull request #3 merged into `main`
- [ ] Render deploys from `main`