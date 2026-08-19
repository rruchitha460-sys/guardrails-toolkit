"""
Output toxicity check - strict threshold.

The bot's own words are held to a much higher bar than user input -
any detectable toxicity in a generated response is a failure, since
it reflects on the system, not a venting user.
"""

from guardrails.pipeline import CheckResult
from guardrails.toxicity_core import score_toxicity

OUTPUT_THRESHOLD = 0.1  # block on almost any toxic signal


def check_toxicity_output(text: str, **context) -> CheckResult:
    score, matches = score_toxicity(text)

    if score >= OUTPUT_THRESHOLD:
        return CheckResult(
            name="toxicity_filter_output",
            passed=False,
            reason=f"toxic content in response (score={score:.2f})",
            score=score,
            metadata={"matched_terms": matches},
        )

    return CheckResult(name="toxicity_filter_output", passed=True, score=score)