#!/usr/bin/env python3
"""
cli.py
------
Command-line interface for the AI Coding Assistant.

Examples:
    python cli.py explain --file data/sample_code/buggy_example.py
    python cli.py review --file data/sample_code/buggy_example.py
    python cli.py improve --file data/sample_code/buggy_example.py
    python cli.py debug --file data/sample_code/buggy_example.py --traceback "ZeroDivisionError: division by zero"
    python cli.py github-review --url https://github.com/psf/requests/blob/main/src/requests/models.py
    python cli.py pr-review --url https://github.com/owner/repo/pull/123
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from core.analyzer import CodeAssistant
from core.llm_client import get_provider
from core.github_client import fetch_file_from_github, fetch_pr_diff
from utils.common import get_logger

load_dotenv()
logger = get_logger("cli")


def build_assistant(args) -> CodeAssistant:
    provider_name = args.provider or os.getenv("LLM_PROVIDER", "openai")
    key_env = f"{provider_name.upper()}_API_KEY"
    api_key = args.api_key or os.getenv(key_env, "")
    if provider_name != "mock" and not api_key:
        logger.warning(
            "No API key found for provider '%s' — falling back to 'mock'. "
            "Set %s in your .env for real output.", provider_name, key_env,
        )
        provider_name = "mock"
    return CodeAssistant(get_provider(provider_name, api_key))


def _read_code(args) -> str:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if args.code:
        return args.code
    print("Provide either --file or --code", file=sys.stderr)
    sys.exit(1)


def cmd_explain(args, assistant: CodeAssistant):
    code = _read_code(args)
    print(assistant.explain(code, args.language))


def cmd_review(args, assistant: CodeAssistant):
    code = _read_code(args)
    result = assistant.review(code, args.language)
    if result.static_issues:
        print("=== Static Analysis ===")
        for issue in result.static_issues:
            print(issue)
        print()
    print("=== AI Review ===")
    print(result.llm_review)


def cmd_improve(args, assistant: CodeAssistant):
    code = _read_code(args)
    print(assistant.suggest_improvements(code, args.language))


def cmd_debug(args, assistant: CodeAssistant):
    code = _read_code(args)
    traceback_text = args.traceback
    if traceback_text and os.path.isfile(traceback_text):
        with open(traceback_text, "r", encoding="utf-8") as f:
            traceback_text = f.read()
    print(assistant.debug(code, traceback_text, args.language))


def cmd_github_review(args, assistant: CodeAssistant):
    gh_file = fetch_file_from_github(args.url, token=os.getenv("GITHUB_TOKEN"))
    language = args.language or (gh_file.path.rsplit(".", 1)[-1] if "." in gh_file.path else "text")
    print(f"Fetched {gh_file.owner}/{gh_file.repo}@{gh_file.ref}:{gh_file.path} ({len(gh_file.content)} chars)\n")
    result = assistant.review(gh_file.content, language)
    if result.static_issues:
        print("=== Static Analysis ===")
        for issue in result.static_issues:
            print(issue)
        print()
    print("=== AI Review ===")
    print(result.llm_review)


def cmd_pr_review(args, assistant: CodeAssistant):
    diff_text = fetch_pr_diff(args.url, token=os.getenv("GITHUB_TOKEN"))
    print(f"Fetched diff ({len(diff_text)} chars)\n")
    print(assistant.review_diff(diff_text))


def main():
    parser = argparse.ArgumentParser(description="AI Coding Assistant")
    parser.add_argument("--provider", choices=["openai", "gemini", "mock"], help="LLM provider to use")
    parser.add_argument("--api-key", help="Override the API key from .env")

    sub = parser.add_subparsers(dest="command", required=True)

    def add_code_args(p):
        p.add_argument("--file", help="Path to a source file")
        p.add_argument("--code", help="Raw code as a string (alternative to --file)")
        p.add_argument("--language", default="python")

    p_explain = sub.add_parser("explain", help="Explain what a piece of code does")
    add_code_args(p_explain)
    p_explain.set_defaults(func=cmd_explain)

    p_review = sub.add_parser("review", help="Find issues (static + AI review)")
    add_code_args(p_review)
    p_review.set_defaults(func=cmd_review)

    p_improve = sub.add_parser("improve", help="Suggest improvements")
    add_code_args(p_improve)
    p_improve.set_defaults(func=cmd_improve)

    p_debug = sub.add_parser("debug", help="Diagnose an error/traceback")
    add_code_args(p_debug)
    p_debug.add_argument("--traceback", required=True, help="Traceback text, or a path to a file containing it")
    p_debug.set_defaults(func=cmd_debug)

    p_gh = sub.add_parser("github-review", help="Fetch a file from GitHub and review it")
    p_gh.add_argument("--url", required=True, help="github.com blob URL or raw.githubusercontent.com URL")
    p_gh.add_argument("--language", help="Override auto-detected language")
    p_gh.set_defaults(func=cmd_github_review)

    p_pr = sub.add_parser("pr-review", help="Fetch a GitHub PR diff and review it")
    p_pr.add_argument("--url", required=True, help="github.com/<owner>/<repo>/pull/<number> URL")
    p_pr.set_defaults(func=cmd_pr_review)

    args = parser.parse_args()
    assistant = build_assistant(args)
    args.func(args, assistant)


if __name__ == "__main__":
    sys.exit(main())
