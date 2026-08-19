"""
Tiny in-memory knowledge base for the demo app.

Real RAG projects use FAISS/embeddings for retrieval (you already have
that skill from Veriscope) - this file keeps things simple with
keyword-overlap retrieval so the demo app has zero external
dependencies and runs instantly. Swap `retrieve()` for a FAISS lookup
later without touching main.py's interface.
"""

import re

KNOWLEDGE_BASE = [
    {
        "id": "doc1",
        "text": "Our support hours are Monday to Friday, 9 AM to 6 PM IST. "
                "We do not offer weekend support currently.",
    },
    {
        "id": "doc2",
        "text": "Refunds are processed within 5-7 business days after approval. "
                "You can request a refund from the Orders page within 30 days of purchase.",
    },
    {
        "id": "doc3",
        "text": "The Pro plan costs ₹999/month and includes unlimited projects, "
                "priority support, and API access. The Free plan is limited to 3 projects.",
    },
    {
        "id": "doc4",
        "text": "To reset your password, go to Settings > Security > Reset Password. "
                "A reset link is sent to your registered email.",
    },
    {
        "id": "doc5",
        "text": "Our data centers are located in Mumbai and Bangalore. "
                "All customer data is encrypted at rest using AES-256.",
    },
]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve(query: str, top_k: int = 2) -> list[str]:
    """Simple keyword-overlap retrieval - returns top_k most relevant doc texts."""
    query_words = _tokenize(query)
    scored = []
    for doc in KNOWLEDGE_BASE:
        doc_words = _tokenize(doc["text"])
        overlap = len(query_words & doc_words)
        if overlap > 0:
            scored.append((overlap, doc["text"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]