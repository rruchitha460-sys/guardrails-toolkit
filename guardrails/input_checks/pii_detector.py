"""
PII detection check.

Regex-based to start (fast, no dependencies, good enough for common
patterns like email/phone/card numbers). You can later swap in
Microsoft Presidio for NER-based detection (names, addresses) without
changing the pipeline interface.
"""

import re
from guardrails.pipeline import CheckResult

PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"),  # India-style mobile; extend as needed
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),  # Indian PAN: 5 letters, 4 digits, 1 letter
}


def check_pii(text: str, **context) -> CheckResult:
    found = {}
    for label, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[label] = len(matches)

    if found:
        types_found = ", ".join(found.keys())
        return CheckResult(
            name="pii_detector",
            passed=False,
            reason=f"PII detected: {types_found}",
            score=min(1.0, 0.3 * sum(found.values())),
            metadata={"pii_types": found},
        )

    return CheckResult(name="pii_detector", passed=True)