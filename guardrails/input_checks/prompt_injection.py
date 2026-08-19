"""
Prompt injection detection check.

Pattern-based detector for the most common injection techniques:
- instruction override attempts ("ignore previous instructions")
- role-play/jailbreak framing ("you are now DAN", "pretend you have no rules")
- system prompt extraction attempts ("repeat your system prompt")
- delimiter/context escape attempts (fake "### SYSTEM" blocks, etc.)

This is intentionally simple (regex/keyword-based) so it's fast and has
zero dependencies. It won't catch everything - it's a first line of
defense. A stronger version could layer in a small classifier model,
but for a portfolio project, showing you understand *what* to detect
and *why* matters more than sophistication.
"""

import re
from guardrails.pipeline import CheckResult

INJECTION_PATTERNS = {
    "instruction_override": re.compile(
        r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|earlier)\s+"
        r"(instructions?|prompts?|rules?|context)\b",
        re.IGNORECASE,
    ),
    "role_override": re.compile(
        r"\b(you are now|act as|pretend (you are|to be)|from now on you|"
        r"you have no (restrictions?|rules?|limits?))\b",
        re.IGNORECASE,
    ),
    "system_prompt_leak": re.compile(
        r"\b(repeat|print|reveal|show me|what is)\s+(your\s+)?(system\s+prompt|"
        r"instructions?|initial prompt)\b",
        re.IGNORECASE,
    ),
    "fake_delimiter": re.compile(
        r"(###\s*system|<\s*/?system\s*>|\[\s*system\s*\]|"
        r"---\s*end of (instructions?|context)\s*---)",
        re.IGNORECASE,
    ),
    "jailbreak_keyword": re.compile(
        r"\b(DAN mode|developer mode|jailbreak|no ethical guidelines|"
        r"unfiltered response)\b",
        re.IGNORECASE,
    ),
}


def check_prompt_injection(text: str, **context) -> CheckResult:
    matched = []
    for label, pattern in INJECTION_PATTERNS.items():
        if pattern.search(text):
            matched.append(label)

    if matched:
        return CheckResult(
            name="prompt_injection",
            passed=False,
            reason=f"possible injection pattern(s): {', '.join(matched)}",
            score=min(1.0, 0.4 * len(matched)),
            metadata={"matched_patterns": matched},
        )

    return CheckResult(name="prompt_injection", passed=True)