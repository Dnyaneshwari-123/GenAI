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