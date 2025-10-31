# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Linear Chief of Staff** is an autonomous AI agent that monitors Linear issues and generates intelligent briefings using Anthropic's Agent SDK. Built as a learning project to explore agent patterns, persistent memory, and semantic search.

**Current Status:** Sessions 1-2 complete (Linear + Agent SDK + Telegram + Memory Layer + Intelligence). Sessions 3-5 pending (Scheduling + Testing + Deployment).

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt        # Production deps
pip install -r requirements-dev.txt    # Dev + test deps
```

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/unit/ -v                    # Unit tests only
python -m pytest tests/integration/ -v             # Integration tests only
python -m pytest tests/unit/test_memory.py -v      # Specific test file

# Run with coverage
python -m pytest --cov=src/linear_chief --cov-report=html

# Run integration test scripts
python test_integration.py          # E2E test (Linear + Agent SDK + Telegram)
python test_memory_integration.py   # Memory layer test (mem0 + ChromaDB)
```

### Code Quality
```bash
# Format code (line length: 100)
black src/ tests/

# Lint code
ruff src/ tests/

# Type check
mypy src/

# All checks together
black src/ tests/ && ruff src/ tests/ && mypy src/
```

## Architecture Overview

### Core Components

**Monolithic async Python agent** with these modules:

1. **`src/linear_chief/linear/`** - Linear GraphQL API client
   - `LinearClient` fetches issues via httpx with retry logic
   - `get_my_relevant_issues()` aggregates assigned + created + subscribed issues
   - Uses hand-written GraphQL queries (not gql library)

2. **`src/linear_chief/agent/`** - Anthropic Agent SDK integration
   - `BriefingAgent` wraps Agent SDK for briefing generation
   - System prompt configures "Chief of Staff" role
   - Uses Claude Sonnet 4 model

3. **`src/linear_chief/telegram/`** - Telegram bot delivery
   - `TelegramBriefingBot` sends briefings via python-telegram-bot
   - Handles message chunking (>4096 chars)

4. **`src/linear_chief/memory/`** - Persistent memory layer
   - `MemoryManager` wraps mem0 for briefing context + user preferences
   - `IssueVectorStore` uses ChromaDB + sentence-transformers for semantic search
   - In-memory fallback when mem0 not configured
   - All storage in `~/.linear_chief/` (configurable via .env)

5. **`src/linear_chief/intelligence/`** - Issue analysis
   - `IssueAnalyzer` detects stagnation, blocking, calculates priority (1-10)
   - `AnalysisResult` dataclass with insights

6. **`src/linear_chief/config.py`** - Configuration management
   - Loads all settings from .env using python-decouple
   - `ensure_directories()` creates required paths

### Data Flow

```
Scheduler → LinearClient → Intelligence → Agent SDK → Telegram
                ↓              ↓              ↓
            Memory Layer   Priority      Briefing
            (mem0 + ChromaDB) Ranking    Generation
```

### Storage Paths (Configurable via .env)

All data stored in `~/.linear_chief/`:
- `state.db` - SQLite database (future: issue history, metrics)
- `chromadb/` - Vector embeddings for semantic search
- `mem0/` - mem0 local Qdrant storage + history.db
- `logs/` - JSON-structured logs

## Critical Coding Standards

### Python-Specific Rules

- **Python 3.11+ required** - Uses modern type hints and async/await
- **All async functions must be awaited** - No forgetting `await` keyword
- **Never use `print()`** - Use `logger.info()` or `logger.debug()` from logging module
- **All public functions must have type hints** - `def foo(bar: str) -> int:`
- **All public APIs must have Google-style docstrings** - Args, Returns, Raises sections
- **External API calls must use retry decorator** - `@retry(stop=stop_after_attempt(3), wait=wait_exponential())`
- **No secrets in code** - Use `config.py` to load from .env
- **All exceptions must be logged before raising** - `logger.error("...", exc_info=True)` then `raise`

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | snake_case | `briefing_agent.py` |
| Classes | PascalCase | `BriefingAgent` |
| Functions/Methods | snake_case | `generate_briefing()` |
| Constants | UPPER_SNAKE_CASE | `MAX_TOKEN_LIMIT` |
| Private methods | _leading_underscore | `_build_prompt()` |
| Async functions | snake_case | `async def fetch_issues()` |

### Testing Standards

- Tests mirror src structure: `tests/unit/` and `tests/integration/`
- Use pytest fixtures for test data
- Use pytest-asyncio for async tests: `@pytest.mark.asyncio`
- Use pytest-mock for mocking external APIs
- Integration tests should clean up after themselves (temp dirs, test data)

## Key Technology Decisions

**Current Stack (Sessions 1-2 complete):**
- Anthropic Agent SDK (Claude Sonnet 4) - Primary intelligence layer
- mem0 0.1.19 - Conversation memory (local Qdrant storage)
- ChromaDB 0.4.24 - Vector store for issue embeddings
- sentence-transformers (all-MiniLM-L6-v2) - Local embeddings (384-dim)
- httpx 0.26.0 - Async HTTP client
- python-telegram-bot 20.8 - Telegram integration
- tenacity - Retry logic with exponential backoff
- python-decouple - .env configuration

**Future Stack (Sessions 3-5 pending):**
- APScheduler 3.10.x - Daily briefing scheduler
- SQLAlchemy 2.0+ - SQLite ORM for state persistence

## Important Notes for Future Claude Instances

### mem0 Configuration Gotchas

mem0 0.1.19 requires specific initialization:
- Needs OPENAI_API_KEY env var (for embeddings)
- Returns `list` not `dict` from `get_all()` (handle both types)
- Custom storage path via MemoryConfig to avoid `/tmp/qdrant`
- Falls back to in-memory if API key missing (graceful degradation)

### Linear API Quirks

- Issue filtering uses 3 sources: assigned + created + subscribed
- Subscriber syntax: `subscribers: {email: {eq: "user@email.com"}}`
- Must deduplicate by issue ID (same issue can appear in multiple sources)
- GraphQL errors often mean incorrect field nesting or filter syntax

### Test Execution Notes

- `test_integration.py` requires all API keys (Linear, Anthropic, Telegram)
- `test_memory_integration.py` downloads sentence-transformers model (~90MB) on first run
- Integration tests with ChromaDB create persistent data in `~/.linear_chief/chromadb`
- Use `rm -rf ~/.linear_chief/chromadb` to reset vector store between test runs

### Budget & Cost Tracking

Target: **<$20/month**
- Anthropic API: ~$1.80/month (30 briefings × 4K tokens × $0.003/1K)
- OpenAI API (mem0 embeddings): ~$0.10/month if used
- All other components run locally (zero cost)

## File Structure Reference

```
src/linear_chief/
├── agent/           # Agent SDK wrapper (BriefingAgent)
├── linear/          # Linear GraphQL client
├── telegram/        # Telegram bot
├── memory/          # mem0 + ChromaDB (MemoryManager, IssueVectorStore)
├── intelligence/    # Issue analysis (IssueAnalyzer, AnalysisResult)
├── scheduling/      # APScheduler (future)
├── storage/         # SQLAlchemy models (future)
├── utils/           # Logging, retry (future)
└── config.py        # Environment configuration

tests/
├── unit/            # Unit tests with mocking
├── integration/     # Integration tests with real services
└── fixtures/        # Test data

Root-level test scripts:
├── test_integration.py         # E2E test (Linear → Agent SDK → Telegram)
├── test_memory_integration.py  # Memory layer test (mem0 + ChromaDB)
```

## Documentation

- **Architecture:** `docs/architecture.md` - High-level design decisions
- **Tech Stack:** `docs/architecture/tech-stack.md` - Technology choices and rationale
- **Coding Standards:** `docs/architecture/coding-standards.md` - Python style guide
- **Progress:** `docs/progress.md` - Implementation status by session
- **PRD:** `docs/prd.md` - Product requirements (sharded in `docs/prd/`)

## Common Development Patterns

### Adding a New API Integration

1. Create module in `src/linear_chief/<service>/`
2. Add config vars to `config.py` and `.env.example`
3. Implement async client with retry logic (use tenacity)
4. Add comprehensive error handling with logging
5. Create unit tests with mocking in `tests/unit/`
6. Create integration tests in `tests/integration/`

### Working with mem0

```python
from src.linear_chief.memory import MemoryManager

memory = MemoryManager()
await memory.add_briefing_context("briefing text", metadata={"key": "value"})
context = await memory.get_agent_context(days=7)
```

### Working with ChromaDB

```python
from src.linear_chief.memory import IssueVectorStore

store = IssueVectorStore()
await store.add_issue("PROJ-123", "Title", "Description", metadata={})
results = await store.search_similar("query text", limit=5)
```

### Running Agent SDK

```python
from src.linear_chief.agent import BriefingAgent

agent = BriefingAgent(ANTHROPIC_API_KEY)
briefing = await agent.generate_briefing(issues, user_context="context")
```
