"""
core/analyzer.py
------------------
The AI Coding Assistant's orchestration layer: combines the
deterministic static checks (core.static_checks, Python-only) with
LLM-based review/explanation/debugging (any language) into one
`CodeAssistant` API used by both the CLI and the dashboard.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from core.llm_client import LLMProvider
from core.static_checks import analyze_python_source, Issue
from core.prompts import (
    explain_prompt,
    review_prompt,
    improvement_prompt,
    debug_prompt,
    diff_review_prompt,
)
from utils.common import get_logger

logger = get_logger(__name__)


@dataclass
class ReviewResult:
    static_issues: List[Issue] = field(default_factory=list)
    llm_review: str = ""


class CodeAssistant:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def explain(self, code: str, language: str = "python") -> str:
        logger.info("Explaining %d chars of %s code", len(code), language)
        return self.provider.generate(explain_prompt(code, language))

    def review(self, code: str, language: str = "python", run_static: Optional[bool] = None) -> ReviewResult:
        """Combined review: fast deterministic static checks (Python only)
        plus an LLM pass that is told about the static findings so it
        doesn't just repeat them."""
        run_static = language.lower() == "python" if run_static is None else run_static
        static_issues = analyze_python_source(code) if run_static else []

        findings_text = "\n".join(f"- {issue}" for issue in static_issues)
        llm_review = self.provider.generate(review_prompt(code, language, findings_text))

        return ReviewResult(static_issues=static_issues, llm_review=llm_review)

    def suggest_improvements(self, code: str, language: str = "python") -> str:
        return self.provider.generate(improvement_prompt(code, language))

    def debug(self, code: str, traceback_text: str, language: str = "python") -> str:
        return self.provider.generate(debug_prompt(code, traceback_text, language))

    def review_diff(self, diff_text: str) -> str:
        return self.provider.generate(diff_review_prompt(diff_text))
