"""Quick manual test — run this to see the pipeline working end-to-end."""

from guardrails.pipeline import GuardrailPipeline
from guardrails.input_checks.pii_detector import check_pii
from guardrails.output_checks.format_validator import check_format

pipeline = GuardrailPipeline(
    input_checks=[check_pii],
    output_checks=[check_format],
)

print("=== Input: clean query ===")
result = pipeline.validate_input("What's the weather like in Bangalore?")
print(f"passed={result.passed}  latency={result.total_latency_ms:.2f}ms")
for c in result.checks:
    print(f"  - {c.name}: passed={c.passed} reason={c.reason}")

print("\n=== Input: query with PII ===")
result = pipeline.validate_input("My email is ruchitha@example.com and phone is 9876543210")
print(f"passed={result.passed}  latency={result.total_latency_ms:.2f}ms")
for c in result.checks:
    print(f"  - {c.name}: passed={c.passed} reason={c.reason} metadata={c.metadata}")

print("\n=== Output: empty response ===")
result = pipeline.validate_output("")
print(f"passed={result.passed}")
for c in result.checks:
    print(f"  - {c.name}: passed={c.passed} reason={c.reason}")

print("\n=== Output: good response ===")
result = pipeline.validate_output("The weather in Bangalore is pleasant today, around 24°C.")
print(f"passed={result.passed}")
for c in result.checks:
    print(f"  - {c.name}: passed={c.passed} reason={c.reason}")