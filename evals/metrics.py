"""
Metrics for the guardrails eval run.

Computes precision/recall/false-positive-rate overall and per check,
by comparing what actually happened (pipeline result) vs what should
have happened (TestCase.expected_pass / expected_failed_check).

Framing (guardrail check = "detector"):
- True Positive  (TP): expected_pass=False, pipeline correctly blocked it
- False Negative (FN): expected_pass=False, pipeline let it through (MISS - bad)
- True Negative  (TN): expected_pass=True,  pipeline correctly passed it
- False Positive (FP): expected_pass=True,  pipeline wrongly blocked it (annoying - bad)
"""

from dataclasses import dataclass, field


@dataclass
class EvalOutcome:
    """One test case's actual result, paired with its expectation."""
    case_id: str
    category: str
    expected_pass: bool
    actual_pass: bool
    expected_failed_check: str | None
    actually_failed_checks: list[str]
    latency_ms: float

    @property
    def correct(self) -> bool:
        return self.expected_pass == self.actual_pass

    @property
    def outcome_type(self) -> str:
        if self.expected_pass and self.actual_pass:
            return "TN"  # correctly passed
        if self.expected_pass and not self.actual_pass:
            return "FP"  # wrongly blocked a good input/output
        if not self.expected_pass and not self.actual_pass:
            return "TP"  # correctly blocked a bad input/output
        return "FN"      # missed a bad input/output


@dataclass
class EvalReport:
    outcomes: list[EvalOutcome] = field(default_factory=list)

    def add(self, outcome: EvalOutcome) -> None:
        self.outcomes.append(outcome)

    def summary(self) -> dict:
        total = len(self.outcomes)
        if total == 0:
            return {"total": 0}

        counts = {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
        for o in self.outcomes:
            counts[o.outcome_type] += 1

        accuracy = (counts["TP"] + counts["TN"]) / total
        # precision/recall framed around "detecting bad input/output"
        precision = counts["TP"] / (counts["TP"] + counts["FP"]) if (counts["TP"] + counts["FP"]) else None
        recall = counts["TP"] / (counts["TP"] + counts["FN"]) if (counts["TP"] + counts["FN"]) else None
        avg_latency = sum(o.latency_ms for o in self.outcomes) / total

        return {
            "total": total,
            "accuracy": accuracy,
            "precision": precision,   # of things we blocked, how many deserved it
            "recall": recall,         # of things that deserved blocking, how many we caught
            "false_positive_rate": counts["FP"] / total,
            "false_negative_rate": counts["FN"] / total,
            "avg_latency_ms": avg_latency,
            "counts": counts,
        }

    def by_category(self) -> dict[str, dict]:
        categories: dict[str, list[EvalOutcome]] = {}
        for o in self.outcomes:
            categories.setdefault(o.category, []).append(o)

        result = {}
        for cat, outcomes in categories.items():
            correct = sum(o.correct for o in outcomes)
            result[cat] = {
                "total": len(outcomes),
                "correct": correct,
                "accuracy": correct / len(outcomes),
            }
        return result

    def failures(self) -> list[EvalOutcome]:
        """Cases where the pipeline disagreed with expectation - the interesting ones."""
        return [o for o in self.outcomes if not o.correct]