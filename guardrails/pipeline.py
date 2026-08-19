"""
Core guardrails pipeline.

This is the reusable orchestrator - it doesn't know about any specific
app. You register input/output checks, and it runs them, times them,
and returns a structured result you can log or act on.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
import time


@dataclass
class CheckResult:
    """Result of a single guardrail check."""
    name: str
    passed: bool
    reason: Optional[str] = None       # why it failed (if it did)
    score: Optional[float] = None      # confidence/severity, 0-1, if applicable
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of running the full input or output pipeline."""
    passed: bool
    checks: list[CheckResult]
    stage: str                          # "input" or "output"
    total_latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


# A check is just a callable: (text: str, **context) -> CheckResult
CheckFn = Callable[..., CheckResult]


class GuardrailPipeline:
    def __init__(
        self,
        input_checks: Optional[list[CheckFn]] = None,
        output_checks: Optional[list[CheckFn]] = None,
        fail_fast: bool = False,
        logger: Optional[Any] = None,
    ):
        """
        input_checks / output_checks: lists of check functions to run, in order.
        fail_fast: if True, stop at the first failed check instead of running all.
        logger: optional GuardrailLogger instance - if given, every run is logged.
        """
        self.input_checks = input_checks or []
        self.output_checks = output_checks or []
        self.fail_fast = fail_fast
        self.logger = logger

    def _run_checks(self, checks: list[CheckFn], text: str, stage: str, **context) -> PipelineResult:
        results: list[CheckResult] = []
        start = time.perf_counter()

        for check_fn in checks:
            check_start = time.perf_counter()
            try:
                result = check_fn(text, **context)
            except Exception as e:
                # a check that crashes should never crash the app - treat as a fail-open
                # with a visible reason so it shows up in eval/logs
                result = CheckResult(
                    name=getattr(check_fn, "__name__", "unknown_check"),
                    passed=True,
                    reason=f"check errored, fail-open: {e}",
                )
            result.latency_ms = (time.perf_counter() - check_start) * 1000
            results.append(result)

            if self.fail_fast and not result.passed:
                break

        total_latency_ms = (time.perf_counter() - start) * 1000
        pipeline_result = PipelineResult(
            passed=all(c.passed for c in results),
            checks=results,
            stage=stage,
            total_latency_ms=total_latency_ms,
        )

        if self.logger:
            self.logger.log(pipeline_result, text=text, **context)

        return pipeline_result

    def validate_input(self, text: str, **context) -> PipelineResult:
        return self._run_checks(self.input_checks, text, stage="input", **context)

    def validate_output(self, text: str, **context) -> PipelineResult:
        """context can include e.g. retrieved_context=[...] for hallucination checks."""
        return self._run_checks(self.output_checks, text, stage="output", **context)