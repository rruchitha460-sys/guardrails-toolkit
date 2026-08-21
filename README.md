# Guardrails & Evaluation Toolkit

A reusable guardrails + evaluation framework for LLM applications — with a live demo chatbot proving it works end-to-end.

Instead of hardcoding safety checks into a single app, this project ships a pluggable `GuardrailPipeline` that any LLM application can import: register input/output checks, run them, and log the results. It's paired with an evaluation harness that measures precision, recall, and false-positive rate on real test cases — not just a claim that the checks work.

**Live demo:** https://guardrails-toolkit.vercel.app
**Backend API:** https://guardrails-toolkit.onrender.com

> Note: the backend runs on Render's free tier, which sleeps after inactivity. The first request after idle time may take 30–50 seconds to wake up.

---

## What it does

Every message sent to the demo chatbot passes through two checkpoints:

```
User query
    ↓
[INPUT GATE]  → PII detector, prompt injection detector, toxicity filter
    ↓ (if passed)
Retrieval (keyword-based RAG over a small knowledge base)
    ↓
Response generation
    ↓
[OUTPUT GATE] → format validator, toxicity filter, hallucination check
    ↓ (if passed)
Response returned to the user, with the full guardrail trail
```

Every check result — pass/fail, reason, latency — is logged (MongoDB, with an automatic in-memory fallback if no database is configured).

## Guardrail checks

| Check | Side | What it does |
|---|---|---|
| `pii_detector` | Input | Regex-based detection of email, phone, credit card, Aadhaar, and PAN numbers |
| `prompt_injection` | Input | Pattern-matches 5 attack categories: instruction override, role/jailbreak framing, system prompt extraction, fake delimiters, jailbreak keywords |
| `toxicity_filter` (input) | Input | Lenient threshold — avoids hard-blocking users who are simply venting |
| `format_validator` | Output | Catches empty/degenerate responses, optional JSON schema validation |
| `toxicity_filter` (output) | Output | Strict threshold — the bot's own words are held to a much higher bar than user input |
| `hallucination_check` | Output | Sentence-level grounding check against retrieved RAG context; flags unsupported claims |

## Evaluation

`evals/test_cases.py` defines 19 labeled test cases (clean queries, PII, injection attempts, toxic input/output, grounded vs. hallucinated responses). `evals/run_eval.py` replays them through the real pipeline, and `evals/metrics.py` scores the results using detection framing (true/false positive/negative).

Run it yourself:
```bash
python -m evals.run_eval
```

Latest run: **100% accuracy, precision, and recall** across all 19 cases, with sub-millisecond average check latency.

## Project structure

```
guardrails-toolkit/
├── guardrails/              # the reusable framework
│   ├── pipeline.py          # orchestrator — register checks, run, log
│   ├── logger.py            # MongoDB logging with in-memory fallback
│   ├── toxicity_core.py     # shared toxicity scoring logic
│   ├── input_checks/        # pii_detector, prompt_injection, toxicity_filter
│   └── output_checks/       # format_validator, hallucination_check, toxicity_filter
├── evals/
│   ├── test_cases.py        # 19 labeled test cases
│   ├── run_eval.py          # runs the suite against the pipeline
│   └── metrics.py           # precision/recall/FP-FN scoring
├── demo_app/
│   ├── main.py               # FastAPI app — /chat, /stats, /health
│   ├── knowledge_base.py     # tiny keyword-retrieval RAG source
│   └── frontend/index.html   # standalone UI showing live guardrail gates
└── dashboard/
    └── app.py                # Streamlit view — live stats + on-demand eval runs
```

## Running locally

```bash
git clone https://github.com/rruchitha460-sys/guardrails-toolkit.git
cd guardrails-toolkit
pip install -r requirements.txt

uvicorn demo_app.main:app --reload
```

Then open `demo_app/frontend/index.html` directly in a browser (no build step needed) — update the `API_BASE` constant near the top of the file to `http://localhost:8000` for local use.

Run the eval suite anytime with:
```bash
python -m evals.run_eval
```

## Deployment

- **Backend:** FastAPI on [Render](https://render.com), Python 3.11 (pinned via `runtime.txt`)
- **Frontend:** static HTML on [Vercel](https://vercel.com), root directory `demo_app/frontend`
- **Logging:** MongoDB Atlas (optional — set `MONGO_URI` as an environment variable; falls back to in-memory logging if unset)

## Tech stack

Python · FastAPI · MongoDB · pymongo · HTML/CSS/JS
