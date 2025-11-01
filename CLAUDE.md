# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Linear Chief of Staff** is an autonomous AI agent that monitors Linear issues and generates intelligent briefings using Anthropic's Messages API. Built as a learning project to explore agent patterns, persistent memory, and semantic search.

**Current Status:** Sessions 1-3 complete (Linear + Messages API + Telegram + Memory Layer + Intelligence + Scheduling + Storage + CLI). Sessions 4-5 pending (Testing + Deployment).

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt        # Production deps
pip install -r requirements-dev.txt    # Dev + test deps
```

### CLI Commands

```bash
# Initialize database
python -m linear_chief init

# Test service connections
python -m linear_chief test

# Generate manual briefing
python -m linear_chief briefing

# Start scheduler (daily briefings)
python -m linear_chief start

# View metrics and cost tracking
python -m linear_chief metrics --days=7

# View briefing history
python -m linear_chief history --days=7 --limit=10
```

### Running Tests
```bash
# Run all tests (79 tests total)
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/unit/ -v                    # Unit tests (30 tests)
python -m pytest tests/integration/ -v             # Integration tests (49 tests)
python -m pytest tests/unit/test_storage.py -v     # Storage tests (16 tests)
python -m pytest tests/unit/test_scheduler.py -v   # Scheduler tests (14 tests)

# Run with coverage
python -m pytest --cov=src/linear_chief --cov-report=html

# Run integration test scripts
python test_integration.py          # E2E test (Linear + Messages API + Telegram)
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

2. **`src/linear_chief/agent/`** - Anthropic Messages API integration
   - `BriefingAgent` wraps Messages API for briefing generation
   - System prompt configures "Chief of Staff" role
   - Uses Claude Sonnet 4 model (claude-sonnet-4-20250514)
   - Note: Documentation may reference "Agent SDK" - actual implementation uses Messages API

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

6. **`src/linear_chief/storage/`** - Persistent storage layer
   - SQLAlchemy ORM models (IssueHistory, Briefing, Metrics)
   - Repository pattern implementations
   - SQLite database with WAL mode for concurrency

7. **`src/linear_chief/scheduling/`** - Automated scheduling
   - `BriefingScheduler` wraps APScheduler with timezone support
   - Daily briefing job with CronTrigger
   - Manual trigger and graceful shutdown

8. **`src/linear_chief/orchestrator.py`** - Main workflow coordinator
   - 8-step workflow: Linear → Intelligence → Agent → Telegram
   - Integrates memory, storage, and metrics
   - Cost tracking and error handling

9. **`src/linear_chief/__main__.py`** - CLI interface
   - Commands: init, test, briefing, start, metrics, history
   - Rich table formatting for output
   - Proper error handling and logging

10. **`src/linear_chief/config.py`** - Configuration management
    - Loads all settings from .env using python-decouple
    - `ensure_directories()` creates required paths

### Data Flow

```
Scheduler (APScheduler)
    ↓
Orchestrator (8-step workflow)
    ↓
1. LinearClient → fetch issues
2. Intelligence → analyze (priority, stagnation, blocking)
3. Storage → save snapshots
4. VectorStore → add embeddings
5. Memory → get context (mem0)
6. Agent (Messages API) → generate briefing
7. Telegram → send message
8. Storage → archive + metrics
```

### Storage Paths (Configurable via .env)

All data stored in `~/.linear_chief/`:
- `state.db` - SQLite database (issue history, briefings, metrics)
- `chromadb/` - Vector embeddings for semantic search
- `mem0/` - mem0 local Qdrant storage + history.db
- `logs/` - JSON-structured logs (future)

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

**Current Stack (Sessions 1-3 complete):**
- **Anthropic Messages API** (Claude Sonnet 4) - Primary intelligence layer
  - Note: Docs may reference "Agent SDK" but implementation uses Messages API
  - Agent SDK (claude-agent-sdk) is too new/unstable for production use
- **mem0 0.1.19** - Conversation memory (local Qdrant storage)
- **ChromaDB 0.4.24** - Vector store for issue embeddings
- **sentence-transformers** (all-MiniLM-L6-v2) - Local embeddings (384-dim)
- **httpx 0.26.0** - Async HTTP client for Linear GraphQL
- **python-telegram-bot 20.8** - Telegram integration
- **APScheduler 3.10.4** - Daily briefing scheduler
- **SQLAlchemy 2.0.34** - SQLite ORM for state persistence
- **tenacity 9.0.0** - Retry logic with exponential backoff
- **python-decouple 3.8** - .env configuration
- **tabulate 0.9.0** - CLI table formatting

**Future Stack (Sessions 4-5 pending):**
- python-json-logger - Structured JSON logging
- Comprehensive test coverage (target: >80%)
- Production deployment (systemd service)

## Important Notes for Future Claude Instances

### mem0 Configuration Gotchas

mem0 0.1.19 requires specific initialization:
- **CRITICAL:** MemoryConfig expects `vector_store.config` as **dict**, not QdrantConfig object
  - Correct: `{"provider": "qdrant", "config": {"collection_name": "mem0", "path": str(path)}}`
  - Wrong: `{"provider": "qdrant", "config": QdrantConfig(...)}`
- Needs OPENAI_API_KEY env var (for embeddings)
- Returns `list` not `dict` from `get_all()` (handle both types)
- Custom storage path via MemoryConfig to avoid `/tmp/qdrant`
- Falls back to in-memory if API key missing (graceful degradation)

### Linear API Quirks

- Issue filtering uses 3 sources: assigned + created + subscribed
- Subscriber syntax: `subscribers: {email: {eq: "user@email.com"}}`
- Must deduplicate by issue ID (same issue can appear in multiple sources)
- GraphQL errors often mean incorrect field nesting or filter syntax

### ChromaDB Best Practices

- Use `upsert()` instead of `add()` to prevent duplicate ID warnings
- ChromaDB persists data in `~/.linear_chief/chromadb` by default
- Clear ChromaDB: `rm -rf ~/.linear_chief/chromadb` to reset vector store
- Warnings about duplicate IDs are harmless but indicate inefficiency

### SQLAlchemy Reserved Words

- **Never use `metadata` as column name** - it's reserved by SQLAlchemy
- Use `extra_metadata` instead for JSON metadata columns
- This applies to models: IssueHistory, Briefing, Metrics

### Test Execution Notes

- All tests (79 total): `python -m pytest tests/ -v`
- `test_integration.py` requires all API keys (Linear, Anthropic, Telegram)
- `test_memory_integration.py` downloads sentence-transformers model (~90MB) on first run
- Integration tests with ChromaDB create persistent data in `~/.linear_chief/chromadb`
- Use `rm -rf ~/.linear_chief/chromadb` to reset vector store between test runs

### Environment Variables

- **TOKENIZERS_PARALLELISM=false** - Prevents fork warnings from sentence-transformers
- Add this to your `.env` file to suppress "huggingface/tokenizers forked" warnings

### Budget & Cost Tracking

Target: **<$20/month**
- Anthropic API: ~$1.80/month (30 briefings × 4K tokens × $0.003/1K)
- OpenAI API (mem0 embeddings): ~$0.10/month if used
- All other components run locally (zero cost)

## File Structure Reference

```
src/linear_chief/
├── __main__.py      # CLI entry point (init, test, briefing, start, metrics, history)
├── orchestrator.py  # Main 8-step workflow coordinator
├── config.py        # Environment configuration
├── agent/           # Messages API wrapper (BriefingAgent)
├── linear/          # Linear GraphQL client (LinearClient)
├── telegram/        # Telegram bot (TelegramBriefingBot)
├── memory/          # mem0 + ChromaDB (MemoryManager, IssueVectorStore)
├── intelligence/    # Issue analysis (IssueAnalyzer, AnalysisResult)
├── scheduling/      # APScheduler (BriefingScheduler)
├── storage/         # SQLAlchemy models (IssueHistory, Briefing, Metrics)
│   ├── database.py  # Engine and session management
│   ├── models.py    # ORM models
│   └── repositories.py  # Repository pattern
└── utils/           # Logging, retry (future)

tests/
├── unit/            # Unit tests with mocking (30 tests)
│   ├── test_intelligence.py  # Intelligence layer tests (17 tests)
│   ├── test_memory.py         # Memory layer tests (10 tests)
│   ├── test_storage.py        # Storage layer tests (16 tests)
│   └── test_scheduler.py      # Scheduler tests (14 tests)
├── integration/     # Integration tests (49 tests)
│   ├── test_embeddings.py     # Embedding tests (8 tests)
│   └── test_workflow.py       # Workflow tests (6 tests)
└── fixtures/        # Test data

scripts/
└── setup_db.py      # Database initialization script

Root-level test scripts:
├── test_integration.py         # E2E test (Linear → Messages API → Telegram)
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

### Running Messages API (BriefingAgent)

```python
from src.linear_chief.agent import BriefingAgent

agent = BriefingAgent(ANTHROPIC_API_KEY)
briefing = await agent.generate_briefing(issues, user_context="context")
```

### Working with Orchestrator

```python
from src.linear_chief.orchestrator import BriefingOrchestrator

orchestrator = BriefingOrchestrator()
result = await orchestrator.generate_and_send_briefing()
# Returns: {"success": bool, "briefing_id": int, "cost_usd": float, ...}
```

### Database Operations

```python
from src.linear_chief.storage import (
    get_session_maker, get_db_session,
    IssueHistoryRepository, BriefingRepository
)

session_maker = get_session_maker()
for session in get_db_session(session_maker):
    issue_repo = IssueHistoryRepository(session)
    issue_repo.save_snapshot(issue_id="PROJ-123", ...)

    briefing_repo = BriefingRepository(session)
    recent = briefing_repo.get_recent_briefings(days=7)
```

### Scheduling

```python
from src.linear_chief.scheduling import BriefingScheduler

scheduler = BriefingScheduler(timezone="Europe/Prague", briefing_time="09:00")
scheduler.start(briefing_job_callback)
# Graceful shutdown
scheduler.stop()
```
