# Coding Standards

## Core Standards

- **Languages & Runtimes:** Python 3.11+, no Python 2 compatibility needed
- **Style & Linting:**
  - Use `black` for code formatting (line length: 100)
  - Use `mypy` for type checking with strict mode
  - Use `ruff` for fast linting (replaces flake8, isort)
- **Test Organization:** Tests mirror src structure (`tests/unit/`, `tests/integration/`)

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | snake_case | `briefing_agent.py` |
| Classes | PascalCase | `BriefingAgent` |
| Functions/Methods | snake_case | `generate_briefing()` |
| Constants | UPPER_SNAKE_CASE | `MAX_TOKEN_LIMIT` |
| Private methods | _leading_underscore | `_build_prompt()` |
| Async functions | snake_case with async prefix | `async def fetch_issues()` |

## Critical Rules

- **Never use `print()` in production code:** Use `logger.info()` or `logger.debug()` from `logging` module
- **All async functions must be awaited or run in event loop:** No forgetting `await` keyword
- **External API calls must use retry decorator:** `@retry(stop=stop_after_attempt(3), wait=wait_exponential())`
- **No secrets in code:** Use `config.py` to load from environment variables
- **All public functions must have type hints:** `def foo(bar: str) -> int:`
- **Database queries must use SQLAlchemy ORM:** Never raw SQL strings (SQL injection risk)
- **Telegram message length must be validated:** Chunk messages >4096 chars
- **All exceptions must be logged before raising:** `logger.error("...", exc_info=True)` before `raise`
- **All public modules, classes, and functions MUST have docstrings:** Use Google-style docstrings with Args, Returns, Raises sections (enforced by `pydocstyle` linter)
- **Docstring coverage target: 100% for public APIs:** Use `interrogate` tool to measure coverage (fail CI if <100%)

---
