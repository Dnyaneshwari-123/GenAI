# CyberSuraksha: interview prep

## 60-second pitch

CyberSuraksha is a GenAI assistant that tells people in India what to do after an online fraud: fake links, UPI and QR scams, OTP theft, fake customer-care numbers. The official advice sits in a long booklet, and an ordinary chatbot may invent steps, which is dangerous when money is at stake.

So I built a retrieval-based assistant on FastAPI. It searches 20 fraud records from the RBI BE(A)WARE booklet, gives only the best matches to a Groq model, and returns structured JSON: the answer, a confidence level, a follow-up question and the records used. When the records don't cover a question, it says so and points to 1930 and cybercrime.gov.in.

I measured it instead of guessing. A better chunk setup raised retrieval checks from 14/15 to 15/15, and a stricter prompt made the confidence format valid in 10 of 10 answers instead of 4. It has 71 tests, runs through GitHub Actions CI, is live on Render, and logs latency and tokens: about 2 seconds per model call and about 21 ms for a cached answer.

## Interview story: the hardest problem

**Getting messy user wording to the right fraud record, without letting the model make things up.**

- **The problem.** Users write short, informal sentences. The booklet is written in formal language and covers many overlapping scams (several involve OTPs, links or remote-access apps). My first search was lexical (TF-IDF), so it matched words, not meaning. For "What should I do if money is stolen through a fake link?" it returned Money mules, SMS scams and Lottery fraud. None of those answers the question.
- **How I found it.** I built a fixed set of questions and looked at the retrieved records for each one, not only the final answers. The chunking evaluation showed a concrete miss: with 600-character chunks and top-3 retrieval, the question about never sharing an OTP with a caller returned an unrelated NEFT chunk and missed the vishing section that answers it.
- **What I did.** I compared two chunk setups on 15 questions. Smaller chunks (300 characters, overlap 50) with top-5 retrieval retrieved the vishing passage and passed 15/15, against 14/15. Smaller chunks suit this booklet because each fraud type has a short, self-contained section.
- **The second layer.** Even with good retrieval, the model must not invent. I wrote prompt v2 with a fixed confidence scale and a rule to say "our records do not have this information" when confidence is low. In the comparison, v1 answered "the records do not provide this" with confidence 0.9, which contradicts itself. v2 returned low.
- **The pictorial PDF.** The source is a pictorial booklet, so I extract its text with pypdf and keep page numbers for citations. I also keep each scenario as a separate structured record (how it works, warning signs, precautions, source URL), so a chunk never mixes two scams.
- **What is still open.** Search still returns unrelated records for some questions, and the app hides the record list when confidence is low. The next fix is a similarity threshold and better handling of informal wording.

## 10 likely questions

### 1. What is RAG, and why did you use it?
RAG means retrieval-augmented generation: find the relevant text first, then give it to the model with the question. A plain model answers from memory and can invent steps, which is risky for fraud advice. With RAG the answer comes from the RBI records, and I can show which records were used.

### 2. How did you choose the chunk size?
I tested two setups on 15 questions. Config A (600 characters, overlap 100, top-3) passed 14/15. Config B (300, overlap 50, top-5) passed 15/15. The only difference was the OTP question, where B retrieved the section that answers it. The cost is that top-5 sends more text to the model, so tokens and noise go up. The test set is small and judged by keyword matching, so I treat this as evidence for this booklet, not a general rule.

### 3. How do you stop the model from hallucinating?
Four things. The prompt says to use only the records. The prompt defines confidence as high, medium or low. When confidence is low, the model must say the records don't have the information. And the app only shows the matched records when confidence isn't low, because for weak matches they would be misleading. This reduces the risk but doesn't remove it: with weakly related records, the model can still give generic advice.

### 4. How did you compare the two prompts?
I ran the same 10 fraud questions through v1 and v2 and scored each answer with a script, then read the answers myself. v2 used a valid confidence format in 10/10 answers against 4/10 for v1, kept 10/10 answers short against 7/10, and had a follow-up that is a question in 10/10 against 3/10. v1 mixed numbers and words for confidence because its prompt never defined the format. One run also lost four answers to rate-limit errors, so I changed the evaluation script to retry and never save error responses.

### 5. How do you handle prompt injection and security?
Input is limited to 3 to 500 characters. A pattern check blocks common attack phrases such as "ignore all previous instructions" and returns a safe refusal without calling the model. A test covers it. It is a regex list, so it stops common phrasings but not clever ones. On secrets: a Gemini key was committed by mistake in `.env.example`. I revoked it on 16 Nov 2026, and real keys now live only in `.env`, which is gitignored. Revoking the key was the real fix. Removing it from the files isn't enough, because it stays in git history.

### 6. What is lite mode, and what does it cost you?
The free Render plan has 512 MB of RAM, too little for an embedding model. Lite mode swaps the embedding store for TF-IDF from scikit-learn. It is much lighter, but it matches words rather than meaning, so paraphrased questions can retrieve worse. Full mode uses embeddings and runs locally with Docker Compose.

### 7. How did you test it?
71 tests with pytest, using a fake vector store and a fake LLM, so they cover the real FastAPI app, the RAG class, the scam-score tool and the agent loop with no network or API key. Ruff and mypy run alongside, and GitHub Actions runs ruff, pytest and a Docker build on every push.

### 8. How does it perform, and where are the limits?
I measured 10 questions locally. A model call takes a median of about 1,973 ms (p95 about 2,370 ms), a cached answer about 21 ms, and a request uses about 839 prompt and 254 completion tokens. The free Groq limit of 8,000 tokens per minute allows only about 7 uncached requests per minute, so the cache and input limits protect the quota. The cache is in memory and per instance, so it resets when the free service sleeps, and the first request after sleep can take about a minute. Ten requests is a small sample, so I'd call the p95 indicative.

### 9. Tell me about a bug you debugged.
CI failed in about 40 seconds although all 71 tests passed on my machine. I first guessed a missing scikit-learn, but the workflow already installed it. I recreated a clean environment with exactly the packages CI installs and saw `No module named 'pypdf'`: my lite-mode code needed it, and the workflow didn't install it. I added it to the workflow. The lesson is to reproduce the failure in a clean environment before guessing.

### 10. What would you improve next?
First, retrieval: add a similarity threshold so unrelated records are never passed to the model, and test hybrid keyword plus embedding search. Second, informal wording: normalise Hinglish and slang, and add test questions written the way users actually write. Third, a larger, labelled evaluation set, with a persistent cache and per-user rate limiting. Fourth, stronger injection defence than a regex list.