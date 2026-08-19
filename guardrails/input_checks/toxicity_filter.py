"""
Input toxicity check - lenient threshold.

Users venting frustration ("this app is so stupid") shouldn't get
hard-blocked - that's a bad UX and not actually a safety issue. We
flag/block only at higher toxicity scores.
"""

from guardrails.pipeline import CheckResult
from guardrails.toxicity_core import score_toxicity

INPUT_THRESHOLD = 0.6  # only block clearly toxic input


def check_toxicity_input(text: str, **context) -> CheckResult:
    score, matches = score_toxicity(text)

    if score >= INPUT_THRESHOLD:
        return CheckResult(
            name="toxicity_filter_input",
            passed=False,
            reason=f"toxic content detected (score={score:.2f})",
            score=score,
            metadata={"matched_terms": matches},
        )

    return CheckResult(name="toxicity_filter_input", passed=True, score=score)