"""
Shared toxicity detection core.

Keyword/pattern-based to start (no model dependency, works offline,
good enough to demo the guardrail concept). Swap in a real classifier
(e.g. a HuggingFace toxic-comment model) later without touching the
pipeline interface - just change what happens inside `score_toxicity`.

Used by both input_checks/toxicity_filter.py and
output_checks/toxicity_filter.py with different thresholds:
- input: lenient (users venting shouldn't get hard-blocked easily)
- output: strict (the bot's own words should never be toxic)
"""

import re

# Deliberately mild example list - keeps the demo safe/portfolio-appropriate
# while proving the mechanism. Swap for a proper lexicon or model in production.
TOXIC_PATTERNS = [
    re.compile(r"\b(idiot|stupid|dumb(ass)?|moron|shut up)\b", re.IGNORECASE),
    re.compile(r"\b(hate you|kill yourself|worthless)\b", re.IGNORECASE),
    re.compile(r"\b(f+u+c+k+|sh+i+t+|b+i+t+c+h+)\w*", re.IGNORECASE),
]


def score_toxicity(text: str) -> tuple[float, list[str]]:
    """Returns (score 0-1, list of matched terms)."""
    matches = []
    for pattern in TOXIC_PATTERNS:
        found = pattern.findall(text)
        if found:
            matches.extend([str(f) for f in found])

    if not matches:
        return 0.0, []

    score = min(1.0, 0.35 * len(matches))
    return score, matches