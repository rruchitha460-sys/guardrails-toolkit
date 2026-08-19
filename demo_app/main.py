"""
Demo app - a small RAG-style support chatbot with guardrails wired in
on both sides of the LLM call.

Flow per request:
    1. validate_input()   -> block PII / injection / severe toxicity before it reaches the "LLM"
    2. retrieve()          -> pull relevant knowledge base chunks
    3. generate()          -> produce a response (mock by default, or Claude API if key is set)
    4. validate_output()   -> check format / toxicity / hallucination against retrieved context
    5. return response + full guardrail trail (for transparency / the frontend to render)

Run: uvicorn demo_app.main:app --reload
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from guardrails.pipeline import GuardrailPipeline, PipelineResult
from guardrails.input_checks.pii_detector import check_pii
from guardrails.input_checks.prompt_injection import check_prompt_injection
from guardrails.input_checks.toxicity_filter import check_toxicity_input
from guardrails.output_checks.format_validator import check_format
from guardrails.output_checks.hallucination_check import check_hallucination
from guardrails.output_checks.toxicity_filter import check_toxicity_output
from guardrails.logger import GuardrailLogger

from demo_app.knowledge_base import retrieve

app = FastAPI(title="Guardrails Demo - Support Bot")

# Allow the static frontend (opened via file:// or a separate dev server)
# to call this API - fine for a portfolio demo, tighten origins for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = GuardrailLogger(mongo_uri=os.environ.get("MONGO_URI"))

pipeline = GuardrailPipeline(
    input_checks=[check_pii, check_prompt_injection, check_toxicity_input],
    output_checks=[check_format, check_toxicity_output, check_hallucination],
    logger=logger,
)


def generate_response(query: str, context: list[str]) -> str:
    """
    Placeholder generator so the demo runs with zero API keys.
    Swap this out for a real Claude API call (see commented block below)
    once you're ready to demo with a live LLM.
    """
    if not context:
        return "I don't have information on that in my knowledge base yet."
    # naive "grounded" answer: just surface the most relevant chunk
    return f"Based on our docs: {context[0]}"

    # --- to use the real Claude API instead, uncomment and set ANTHROPIC_API_KEY ---
    # import anthropic
    # client = anthropic.Anthropic()
    # context_text = "\n".join(context)
    # message = client.messages.create(
    #     model="claude-sonnet-4-6",
    #     max_tokens=300,
    #     messages=[{
    #         "role": "user",
    #         "content": f"Context:\n{context_text}\n\nQuestion: {query}\n\n"
    #                    f"Answer only using the context above.",
    #     }],
    # )
    # return message.content[0].text


class ChatRequest(BaseModel):
    query: str


def _serialize(result: PipelineResult) -> dict:
    return {
        "passed": result.passed,
        "stage": result.stage,
        "latency_ms": round(result.total_latency_ms, 2),
        "checks": [
            {"name": c.name, "passed": c.passed, "reason": c.reason}
            for c in result.checks
        ],
    }


@app.post("/chat")
def chat(request: ChatRequest) -> dict:
    input_result = pipeline.validate_input(request.query)
    if not input_result.passed:
        return {
            "response": None,
            "blocked_at": "input",
            "input_guardrails": _serialize(input_result),
        }

    context = retrieve(request.query)
    response_text = generate_response(request.query, context)

    output_result = pipeline.validate_output(response_text, retrieved_context=context)
    if not output_result.passed:
        return {
            "response": None,
            "blocked_at": "output",
            "input_guardrails": _serialize(input_result),
            "output_guardrails": _serialize(output_result),
        }

    return {
        "response": response_text,
        "blocked_at": None,
        "input_guardrails": _serialize(input_result),
        "output_guardrails": _serialize(output_result),
        "retrieved_context": context,
    }


@app.get("/stats")
def stats() -> dict:
    """Powers the dashboard - aggregate pass/fail rates per check."""
    return logger.stats()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}