"""
Hallucination check.

Checks whether a generated response is actually grounded in the
retrieved context (for a RAG app), instead of the LLM making things up.

Approach: sentence-level overlap between the response and the
retrieved context, using word-overlap similarity (Jaccard-style).
This is a lightweight, dependency-free stand-in for a proper NLI
("does the context entail this sentence?") or embedding-similarity
check - upgrade path is swapping `_sentence_grounded` to use
sentence-transformers cosine similarity or an NLI model, without
touching the pipeline interface.

Usage:
    pipeline.validate_output(
        response_text,
        retrieved_context=["chunk 1 text...", "chunk 2 text..."]
    )

If no retrieved_context is passed in context, this check passes
automatically (it only applies to RAG-style responses).
"""

import re
from guardrails.pipeline import CheckResult

MIN_GROUNDED_RATIO = 0.5   # at least half the response's sentences must be grounded
OVERLAP_THRESHOLD = 0.5    # word-overlap ratio to call a sentence "grounded"

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
    "of", "and", "or", "for", "with", "this", "that", "it", "as", "by",
    "be", "has", "have", "had", "not", "but", "so", "if", "then",
}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS}


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s.strip()]


def _sentence_grounded(sentence: str, context_words: set[str]) -> bool:
    sentence_words = _tokenize(sentence)
    if not sentence_words:
        return True  # nothing substantive to ground (e.g. "Sure!")
    overlap = len(sentence_words & context_words) / len(sentence_words)
    return overlap >= OVERLAP_THRESHOLD


def check_hallucination(text: str, **context) -> CheckResult:
    retrieved_context = context.get("retrieved_context")

    if not retrieved_context:
        # not a RAG call - nothing to ground against, so don't penalize
        return CheckResult(
            name="hallucination_check",
            passed=True,
            reason="no retrieved_context provided, check skipped",
        )

    context_words: set[str] = set()
    for chunk in retrieved_context:
        context_words |= _tokenize(chunk)

    sentences = _split_sentences(text)
    if not sentences:
        return CheckResult(name="hallucination_check", passed=True)

    grounded_flags = [_sentence_grounded(s, context_words) for s in sentences]
    grounded_ratio = sum(grounded_flags) / len(grounded_flags)

    ungrounded_sentences = [
        s for s, grounded in zip(sentences, grounded_flags) if not grounded
    ]

    if grounded_ratio < MIN_GROUNDED_RATIO:
        return CheckResult(
            name="hallucination_check",
            passed=False,
            reason=f"only {grounded_ratio:.0%} of response grounded in retrieved context",
            score=1 - grounded_ratio,
            metadata={"ungrounded_sentences": ungrounded_sentences},
        )

    return CheckResult(
        name="hallucination_check",
        passed=True,
        score=1 - grounded_ratio,
        metadata={"grounded_ratio": grounded_ratio},
    )