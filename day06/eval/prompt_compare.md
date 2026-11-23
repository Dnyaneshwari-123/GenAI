## Comparison (10 questions, results in eval/results.json)

Scored with `eval/fill_compare.py`, then checked by reading the answers.

| Criteria | Version 1 | Version 2 |
|---|---|---|
| Valid JSON (answer, confidence, follow_up) | 10/10 | 10/10 |
| Confidence is high/medium/low | 4/10 | 10/10 |
| Simple answers (≤60 words) | 7/10 | 10/10 |
| Gives a record-based answer | 7/10 | 6/10 |
| Confidence matches missing info | 7/10 | 10/10 |
| Follow-up is a question | 3/10 | 10/10 |

## Findings

- v1 mixed number and word confidence values (0.2, 0.95, "high", "low") because its prompt never defines the format. v2 used high/medium/low every time.
- v1 sometimes contradicted itself. In question 10 it said the records had no information but gave confidence 0.9. v2 correctly returned low, because the only sales-platform record covers the fake-buyer UPI scam, not a seller who never delivers.
- Most v1 follow-ups were statements such as "No further information available." Only 3 of 10 were questions. All 10 v2 follow-ups were questions that help the next step.
- v1 answers could run long (question 1 first returned six sentences). v2 stayed within 3 short sentences.
- v2 scores lower on "record-based answer" because it declines to answer when the records do not cover the question, which is the intended behaviour. The row only checks that the answer does not admit missing information.
- Retrieval returns unrelated records for both prompts. For example, question 2 (online harassment) matched "Impersonation on social media" and "Online job fraud", and question 10 matched "Lottery fraud". This comes from `smart_search.py`, not from the prompts.
- The first evaluation run lost four v2 answers to Groq rate-limit errors (429). `run_eval.py` now waits between calls, retries, and refuses to save error responses. `results.json` was regenerated with all 20 real answers.

## Failure examples

- **v1, question 10:** answer "The records do not provide information on what to do if an online seller takes your payment and disappears.", confidence 0.9, follow_up "No further information available." The confidence contradicts the answer and the follow-up is not a question.
- **v2, question 2:** the answer is correct ("Our records do not have information on where to report online harassment."), but `matched` still lists unrelated records (Frauds using online sales platforms, Impersonation on social media, Online job fraud). v2 does not filter weak matches.

## Conclusion

**Better prompt: v2.** It gives a consistent schema (10/10 vs 4/10), shorter answers, confidence that agrees with the answer, and follow-ups that are questions. Its weakness is that it still passes through weak retrieval matches, so the fix belongs in the search step.

## Security

The old Gemini key was revoked on GitHub and in Google AI Studio on 18 november 2026. The current key is stored only in `.env`, which is gitignored, and no key appears in git history.