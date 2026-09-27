# 🧑‍💻 AI Coding Assistant

A Python-powered AI coding assistant that **explains code, finds bugs,
suggests improvements, and helps debug errors** — for pasted snippets,
local files, or code pulled straight from a **GitHub file URL or pull
request**.

## ✨ Features

- 📖 **Code explanation** — plain-language walkthroughs of what code does and why
- 🔍 **Hybrid code review** — instant, deterministic **AST-based static checks**
  (bare `except:`, mutable default args, wildcard imports, `eval`/`exec` use,
  overly long functions, unused imports, stray TODOs) combined with an
  **LLM-based judgment pass** for logic bugs, naming, and style
- 🛠 **Improvement suggestions** — idiomatic refactors with before/after snippets
- 🐛 **Debugging assistant** — paste code + a traceback, get root cause + fix
- 🔗 **GitHub file review** — paste a `github.com/.../blob/...` URL, the assistant
  fetches and reviews the real file
- 🔀 **GitHub PR diff review** — paste a PR URL, get PR-review-style comments
  on just the changed lines
- 🔌 **Pluggable LLM providers** — OpenAI or Google Gemini, one flag to switch
- 🛡 **Resilient** — exponential-backoff retry around every network call
- 🧪 **Offline mock provider** — every feature (including the test suite) runs
  with zero API key using deterministic mock output

## 🧱 Tech Stack

Python · `ast` (static analysis) · Streamlit · Requests · GitHub REST/raw
content · OpenAI API / Gemini API · Prompt Engineering · pytest

## 📂 Project Structure

```
ai-coding-assistant/
├── app.py                     # Streamlit dashboard (4 tabs)
├── cli.py                     # CLI: explain / review / improve / debug / github-review / pr-review
├── core/
│   ├── llm_client.py           # LLMProvider interface: OpenAI / Gemini / Mock + retry logic
│   ├── static_checks.py          # AST-based deterministic checks (no LLM, no API key needed)
│   ├── prompts.py                 # All prompt-engineering templates
│   ├── analyzer.py                 # CodeAssistant: combines static checks + LLM
│   └── github_client.py             # Fetch a GitHub file or PR diff by URL
├── utils/
│   └── common.py                     # Logging + retry-with-backoff decorator
├── data/sample_code/
│   └── buggy_example.py               # Intentionally buggy file to demo the review pipeline
├── tests/
│   ├── test_static_checks.py           # Static analyzer assertions
│   ├── test_prompts.py                  # Prompt-template assertions
│   ├── test_github_client.py             # URL-parsing tests (no network)
│   └── test_analyzer.py                   # Orchestration tests (offline, mock provider)
├── outputs/                                 # Reserved for saved review output
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Getting Started

```bash
git clone https://github.com/saniamumtazz/ai-coding-assistant.git
cd ai-coding-assistant
pip install -r requirements.txt
cp .env.example .env
# paste your OPENAI_API_KEY or GEMINI_API_KEY into .env
```

### Run the dashboard
```bash
streamlit run app.py
```

### Or use the CLI
```bash
# Explain a file
python cli.py explain --file data/sample_code/buggy_example.py

# Hybrid review: instant static checks + AI judgment pass
python cli.py review --file data/sample_code/buggy_example.py

# Suggest improvements
python cli.py improve --file data/sample_code/buggy_example.py

# Debug an error
python cli.py debug --file data/sample_code/buggy_example.py --traceback "ZeroDivisionError: division by zero"

# Review a real file straight from GitHub
python cli.py github-review --url https://github.com/psf/requests/blob/main/src/requests/models.py

# Review a pull request's diff
python cli.py pr-review --url https://github.com/owner/repo/pull/123
```

Add `--provider mock` to any command to explore without an API key.

## 🧪 Running Tests

```bash
pytest -v
```

21 tests, all fully offline (mock LLM provider, no network) — safe to wire
into a GitHub Actions CI workflow that runs on every push.

## 🛠 How It Works

1. **Static layer** (`core/static_checks.py`) — parses Python with the `ast`
   module and flags a fixed set of well-known issues instantly, for free,
   with zero hallucination risk.
2. **Prompt layer** (`core/prompts.py`) — dedicated, tuned templates for
   explaining, reviewing, improving, debugging, and diff-reviewing.
3. **Provider layer** (`core/llm_client.py`) — an `LLMProvider` interface
   makes OpenAI/Gemini/future-providers drop-in swappable, with
   exponential-backoff retry wrapping every real API call.
4. **Orchestration** (`core/analyzer.py`) — `CodeAssistant.review()` runs the
   static pass first and *feeds those findings into the LLM prompt*, so the
   LLM is explicitly told "don't repeat these, add judgment on top."
5. **GitHub integration** (`core/github_client.py`) — converts a normal
   `github.com/.../blob/...` URL into its raw-content URL, and fetches a PR's
   diff using GitHub's built-in `.diff` URL suffix — no API token required
   for public repos.

## 🔮 Possible Extensions

- Support more languages' static checks (currently Python-only; LLM review
  already works for any language)
- Auto-post review comments back to a GitHub PR via the GitHub API
- A pre-commit hook / GitHub Action that runs `review` on changed files
- Inline diff annotations instead of a flat comment list

## 📄 License

MIT
