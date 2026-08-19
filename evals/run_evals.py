"""
Eval runner.

Runs every TestCase through the actual GuardrailPipeline and builds an
EvalReport comparing expected vs actual outcomes. This is what proves
the guardrails work - not just "it runs," but "it catches what it
should and doesn't over-block."

Usage:
    python -m evals.run_eval
"""

from guardrails.pipeline import GuardrailPipeline
from guardrails.input_checks.pii_detector import check_pii
from guardrails.input_checks.prompt_injection import check_prompt_injection
from guardrails.input_checks.toxicity_filter import check_toxicity_input
from guardrails.output_checks.format_validator import check_format
from guardrails.output_checks.hallucination_check import check_hallucination
from guardrails.output_checks.toxicity_filter import check_toxicity_output

from evals.test_cases import ALL_TEST_CASES, TestCase
from evals.metrics import EvalOutcome, EvalReport


def build_pipeline() -> GuardrailPipeline:
    return GuardrailPipeline(
        input_checks=[check_pii, check_prompt_injection, check_toxicity_input],
        output_checks=[check_format, check_toxicity_output, check_hallucination],
    )


def run_case(pipeline: GuardrailPipeline, case: TestCase) -> EvalOutcome:
    if case.stage == "input":
        result = pipeline.validate_input(case.text, **case.context)
    else:
        result = pipeline.validate_output(case.text, **case.context)

    return EvalOutcome(
        case_id=case.id,
        category=case.category,
        expected_pass=case.expected_pass,
        actual_pass=result.passed,
        expected_failed_check=case.expected_failed_check,
        actually_failed_checks=[c.name for c in result.failed_checks()],
        latency_ms=result.total_latency_ms,
    )


def run_eval(test_cases: list[TestCase] = ALL_TEST_CASES) -> EvalReport:
    pipeline = build_pipeline()
    report = EvalReport()
    for case in test_cases:
        report.add(run_case(pipeline, case))
    return report


def print_report(report: EvalReport) -> None:
    summary = report.summary()
    print("=" * 50)
    print("EVAL SUMMARY")
    print("=" * 50)
    print(f"Total cases:  {summary['total']}")
    print(f"Accuracy:     {summary['accuracy']:.1%}")
    print(f"Precision:    {summary['precision']:.1%}" if summary['precision'] is not None else "Precision:    n/a")
    print(f"Recall:       {summary['recall']:.1%}" if summary['recall'] is not None else "Recall:       n/a")
    print(f"FP rate:      {summary['false_positive_rate']:.1%}")
    print(f"FN rate:      {summary['false_negative_rate']:.1%}")
    print(f"Avg latency:  {summary['avg_latency_ms']:.2f}ms")
    print(f"Counts:       {summary['counts']}")

    print("\nBy category:")
    for cat, stats in report.by_category().items():
        print(f"  {cat:<25} {stats['correct']}/{stats['total']} correct ({stats['accuracy']:.0%})")

    failures = report.failures()
    if failures:
        print(f"\n{len(failures)} FAILURE(S) - pipeline disagreed with expectation:")
        for f in failures:
            print(f"  [{f.outcome_type}] {f.case_id}: expected_pass={f.expected_pass} "
                  f"actual_pass={f.actual_pass} failed_checks={f.actually_failed_checks}")
    else:
        print("\nNo failures - pipeline matched every expectation.")


if __name__ == "__main__":
    report = run_eval()
    print_report(report)