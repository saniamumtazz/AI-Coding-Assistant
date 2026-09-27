"""
core/static_checks.py
-----------------------
Fast, deterministic, LLM-independent checks using Python's `ast` module.
These run instantly, need no API key, and catch a set of well-known
issues so the LLM's job is reserved for what it's actually good at:
judgment calls, style, and explanations — not things a parser can
already tell you for free.

Only used for Python source. Other languages skip straight to the
LLM-based review.
"""

import ast
import re
from dataclasses import dataclass
from typing import List


@dataclass
class Issue:
    line: int
    severity: str  # "warning" | "info"
    category: str
    message: str

    def __str__(self) -> str:
        return f"L{self.line} [{self.severity.upper()}] ({self.category}) {self.message}"


LONG_FUNCTION_THRESHOLD = 40  # lines


def analyze_python_source(source: str) -> List[Issue]:
    issues: List[Issue] = []

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [Issue(line=e.lineno or 0, severity="warning", category="syntax",
                       message=f"Syntax error: {e.msg}")]

    issues += _check_bare_except(tree)
    issues += _check_mutable_defaults(tree)
    issues += _check_wildcard_imports(tree)
    issues += _check_eval_exec(tree)
    issues += _check_long_functions(tree)
    issues += _check_unused_imports(tree, source)
    issues += _check_todo_comments(source)

    return sorted(issues, key=lambda i: i.line)


def _check_bare_except(tree: ast.AST) -> List[Issue]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            out.append(Issue(node.lineno, "warning", "error-handling",
                              "Bare 'except:' catches every exception, including "
                              "KeyboardInterrupt/SystemExit — catch a specific exception instead."))
    return out


def _check_mutable_defaults(tree: ast.AST) -> List[Issue]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in list(node.args.defaults) + list(node.args.kw_defaults):
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    out.append(Issue(node.lineno, "warning", "mutable-default",
                                      f"Function '{node.name}' uses a mutable default argument "
                                      "(list/dict/set) — it is shared across all calls. Use "
                                      "None and initialize inside the function instead."))
    return out


def _check_wildcard_imports(tree: ast.AST) -> List[Issue]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    out.append(Issue(node.lineno, "info", "imports",
                                      f"Wildcard import from '{node.module}' pollutes the "
                                      "namespace and hides where names come from."))
    return out


def _check_eval_exec(tree: ast.AST) -> List[Issue]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                out.append(Issue(node.lineno, "warning", "security",
                                  f"Use of '{node.func.id}()' can execute arbitrary code — "
                                  "avoid it on any untrusted input."))
    return out


def _check_long_functions(tree: ast.AST) -> List[Issue]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, "end_lineno", None)
            if end_line:
                length = end_line - node.lineno
                if length > LONG_FUNCTION_THRESHOLD:
                    out.append(Issue(node.lineno, "info", "maintainability",
                                      f"Function '{node.name}' is ~{length} lines long — "
                                      "consider splitting it into smaller functions."))
    return out


def _check_unused_imports(tree: ast.AST, source: str) -> List[Issue]:
    out = []
    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = (alias.asname or alias.name).split(".")[0]
                imported_names.append((node.lineno, name))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                imported_names.append((node.lineno, name))

    for lineno, name in imported_names:
        # crude but dependency-free: count occurrences of the name outside the import line itself
        pattern = re.compile(rf"\b{re.escape(name)}\b")
        occurrences = len(pattern.findall(source))
        if occurrences <= 1:
            out.append(Issue(lineno, "info", "imports",
                              f"'{name}' is imported but doesn't appear to be used anywhere."))
    return out


def _check_todo_comments(source: str) -> List[Issue]:
    out = []
    for i, line in enumerate(source.splitlines(), start=1):
        if re.search(r"#\s*(TODO|FIXME|XXX)\b", line):
            out.append(Issue(i, "info", "housekeeping", f"Unresolved marker in comment: {line.strip()}"))
    return out
