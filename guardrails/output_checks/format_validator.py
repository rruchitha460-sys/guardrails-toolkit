"""
Output format check.

Two things this catches:
1. Empty / degenerate responses (LLM returned nothing useful)
2. Optional: strict JSON-schema conformance, if the app expects
   structured output (context["expected_schema"] = {...})
"""

import json
from guardrails.pipeline import CheckResult

MIN_RESPONSE_LENGTH = 3


def check_format(text: str, **context) -> CheckResult:
    stripped = text.strip()

    if len(stripped) < MIN_RESPONSE_LENGTH:
        return CheckResult(
            name="format_validator",
            passed=False,
            reason="response too short / empty",
        )

    expected_schema = context.get("expected_schema")
    if expected_schema:
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as e:
            return CheckResult(
                name="format_validator",
                passed=False,
                reason=f"invalid JSON: {e}",
            )

        missing = [k for k in expected_schema if k not in parsed]
        if missing:
            return CheckResult(
                name="format_validator",
                passed=False,
                reason=f"missing required keys: {missing}",
                metadata={"parsed": parsed},
            )

    return CheckResult(name="format_validator", passed=True)