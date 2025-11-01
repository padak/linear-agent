# API Documentation

Complete API reference for Linear Chief of Staff modules, classes, and methods.

## Table of Contents

- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [Core Modules](#core-modules)
  - [Orchestrator](#orchestrator)
  - [Linear Client](#linear-client)
  - [Briefing Agent](#briefing-agent)
  - [Telegram Bot](#telegram-bot)
- [Intelligence Layer](#intelligence-layer)
- [Memory Layer](#memory-layer)
  - [Memory Manager](#memory-manager)
  - [Vector Store](#vector-store)
- [Storage Layer](#storage-layer)
  - [Database](#database)
  - [Models](#models)
  - [Repositories](#repositories)
- [Scheduling](#scheduling)

---

## Configuration

### `config.py`

Environment configuration using python-decouple.

#### Configuration Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LINEAR_API_KEY` | str | "" | Linear API key for authentication |
| `LINEAR_WORKSPACE_ID` | str | "" | Linear workspace identifier |
| `ANTHROPIC_API_KEY` | str | "" | Anthropic API key for Claude |
| `OPENAI_API_KEY` | str | "" | OpenAI API key for mem0 embeddings |
| `TELEGRAM_BOT_TOKEN` | str | "" | Telegram bot token |
| `TELEGRAM_CHAT_ID` | str | "" | Target Telegram chat ID |
| `MEM0_API_KEY` | str | "" | mem0 API key (optional) |
| `LOCAL_TIMEZONE` | str | "Europe/Prague" | Timezone for scheduling |
| `BRIEFING_TIME` | str | "09:00" | Daily briefing time (HH:MM) |
| `DATABASE_PATH` | Path | "~/.linear_chief/state.db" | SQLite database path |
| `CHROMADB_PATH` | Path | "~/.linear_chief/chromadb" | ChromaDB storage path |
| `MEM0_PATH` | Path | "~/.linear_chief/mem0" | mem0 storage path |
| `LOGS_PATH` | Path | "~/.linear_chief/logs" | Logs directory |
| `EMBEDDING_MODEL` | str | "all-MiniLM-L6-v2" | sentence-transformers model |
| `MONTHLY_BUDGET_USD` | float | 20.0 | Monthly budget limit |

#### Functions

##### `ensure_directories()`

Create necessary directories if they don't exist.

```python
from linear_chief.config import ensure_directories

ensure_directories()
```

---

## CLI Commands

### `python -m linear_chief <command>`

All CLI commands are defined in `__main__.py`.

#### `init`

Initialize database schema.

```bash
python -m linear_chief init
```

**Output:**
- Creates SQLite database at `DATABASE_PATH`
- Initializes all tables (issue_history, briefings, metrics)

#### `test`

Test connections to all external services.

```bash
python -m linear_chief test
```

**Output:**
```
Testing service connections...

✓ Linear: OK
✓ Telegram: OK
```

#### `briefing`

Generate and send briefing immediately.

```bash
python -m linear_chief briefing
```

**Output:**
```
Generating briefing...

✓ Briefing generated and sent successfully!
  Issues: 12
  Cost: $0.0234
  Duration: 4.56s
  Briefing ID: 42
```

#### `start`

Start scheduler for daily briefings.

```bash
python -m linear_chief start
```

**Output:**
```
Starting briefing scheduler...

✓ Scheduler started successfully!
  Next briefing: 2025-11-02 09:00:00+01:00

Press Ctrl+C to stop...
```

#### `metrics`

Display metrics and statistics.

```bash
python -m linear_chief metrics --days=7
```

**Options:**
- `--days`: Number of days to look back (default: 7)

**Output:**
```
Metrics for last 7 days:

📊 Briefing Statistics:
  Total briefings: 7
  Total cost: $0.1638
  Average cost per briefing: $0.0234
  Sent successfully: 7
  Failed: 0

💰 API Cost Metrics:
  Total API calls: 7
  Total cost: $0.1638
  Average cost: $0.0234
  Min cost: $0.0198
  Max cost: $0.0267

📝 Recent Briefings:
ID  Generated At       Issues  Cost      Status
--  ----------------  -------  --------  ------
7   2025-11-01 09:00       12  $0.0234   sent
6   2025-10-31 09:00       10  $0.0198   sent
...
```

#### `history`

Show briefing history.

```bash
python -m linear_chief history --days=7 --limit=10
```

**Options:**
- `--days`: Number of days to look back (default: 7)
- `--limit`: Maximum number of briefings to show (default: 10)

**Output:**
```
Briefing history (last 7 days, max 10 entries):

============================================================
Briefing #7 - 2025-11-01 09:00
============================================================
Issues: 12
Status: sent
Cost: $0.0234

Content:
# Daily Linear Briefing - November 1, 2025

## Key Issues Requiring Attention
...
```

---

## Core Modules

### Orchestrator

**Module:** `orchestrator.py`

Main workflow coordinator that integrates all components.

#### Class: `BriefingOrchestrator`

```python
from linear_chief.orchestrator import BriefingOrchestrator

orchestrator = BriefingOrchestrator(
    linear_api_key="lin_api_...",
    anthropic_api_key="sk-ant-...",
    telegram_bot_token="1234567890:ABC...",
    telegram_chat_id="123456789"
)
```

##### `__init__(linear_api_key, anthropic_api_key, telegram_bot_token, telegram_chat_id)`

Initialize orchestrator with API credentials.

**Args:**
- `linear_api_key` (str): Linear API key
- `anthropic_api_key` (str): Anthropic API key
- `telegram_bot_token` (str): Telegram bot token
- `telegram_chat_id` (str): Telegram chat ID

**Defaults:** Uses values from `config.py` if not provided.

##### `async generate_and_send_briefing() -> Dict[str, Any]`

Execute full 8-step briefing workflow.

**Workflow:**
1. Fetch issues from Linear
2. Analyze issues (priority, stagnation, blocking)
3. Save issue snapshots to database
4. Add issues to vector store
5. Get agent context from memory
6. Generate briefing via Messages API
7. Send briefing via Telegram
8. Archive briefing and metrics to database

**Returns:**
```python
{
    "success": True,
    "briefing_id": 42,
    "issue_count": 12,
    "cost_usd": 0.0234,
    "duration_seconds": 4.56,
    "error": None
}
```

**Raises:**
- `Exception`: If critical workflow step fails

**Example:**
```python
import asyncio

orchestrator = BriefingOrchestrator()
result = await orchestrator.generate_and_send_briefing()

if result["success"]:
    print(f"Briefing sent! ID: {result['briefing_id']}")
else:
    print(f"Failed: {result['error']}")
```

##### `async test_connections() -> Dict[str, bool]`

Test all external service connections.

**Returns:**
```python
{
    "linear": True,
    "telegram": True
}
```

**Example:**
```python
results = await orchestrator.test_connections()

if all(results.values()):
    print("All services connected!")
else:
    failed = [k for k, v in results.items() if not v]
    print(f"Failed: {failed}")
```

---

### Linear Client

**Module:** `linear/client.py`

GraphQL client for Linear API.

#### Class: `LinearClient`

```python
from linear_chief.linear import LinearClient

client = LinearClient(api_key="lin_api_...")
```

##### `__init__(api_key: str)`

Initialize Linear API client.

**Args:**
- `api_key` (str): Linear API key

##### `async query(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

Execute a GraphQL query against Linear API.

**Args:**
- `query` (str): GraphQL query string
- `variables` (dict, optional): Query variables

**Returns:**
- Response data dictionary

**Raises:**
- `httpx.HTTPError`: If request fails
- `Exception`: If GraphQL returns errors

**Retry Policy:** 3 attempts with exponential backoff (2s, 4s, 8s)

**Example:**
```python
query = """
query {
  viewer {
    id
    name
    email
  }
}
"""

result = await client.query(query)
print(result["viewer"]["name"])
```

##### `async get_issues(team_ids: Optional[List[str]] = None, assignee_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]`

Fetch issues from Linear.

**Args:**
- `team_ids` (list, optional): Team IDs to filter by
- `assignee_id` (str, optional): Assignee user ID to filter by
- `limit` (int): Maximum issues to return (default: 50)

**Returns:**
- List of issue dictionaries

**Example:**
```python
# Get all issues
issues = await client.get_issues(limit=100)

# Get issues for specific team
issues = await client.get_issues(team_ids=["team-uuid"], limit=50)

# Get issues assigned to user
issues = await client.get_issues(assignee_id="user-uuid", limit=50)
```

##### `async get_viewer() -> Dict[str, Any]`

Get authenticated user (viewer) information.

**Returns:**
```python
{
    "id": "user-uuid",
    "name": "John Doe",
    "email": "john@example.com"
}
```

##### `async get_teams() -> List[Dict[str, Any]]`

Fetch all teams accessible to the authenticated user.

**Returns:**
```python
[
    {
        "id": "team-uuid",
        "name": "Engineering",
        "key": "ENG",
        "description": "Engineering team"
    }
]
```

##### `async get_my_relevant_issues(limit: int = 100) -> List[Dict[str, Any]]`

Fetch all issues relevant to authenticated user:
- Assigned to me
- Created by me
- Subscribed to

Returns deduplicated list.

**Args:**
- `limit` (int): Maximum issues per category (default: 100)

**Returns:**
- Deduplicated list of issue dictionaries

**Example:**
```python
issues = await client.get_my_relevant_issues()
print(f"Found {len(issues)} relevant issues")

for issue in issues:
    print(f"{issue['identifier']}: {issue['title']}")
```

##### Context Manager Support

```python
async with LinearClient(api_key="...") as client:
    issues = await client.get_my_relevant_issues()
```

---

### Briefing Agent

**Module:** `agent/briefing_agent.py`

Anthropic Messages API wrapper for briefing generation.

#### Class: `BriefingAgent`

```python
from linear_chief.agent import BriefingAgent

agent = BriefingAgent(
    api_key="sk-ant-...",
    model="claude-sonnet-4-20250514"
)
```

##### `__init__(api_key: str, model: str = "claude-sonnet-4-20250514")`

Initialize the briefing agent.

**Args:**
- `api_key` (str): Anthropic API key
- `model` (str): Claude model to use

**Supported Models:**
- `claude-sonnet-4-20250514` (default)
- `claude-3-5-sonnet-20241022`
- Other Claude models

##### `async generate_briefing(issues: List[Dict[str, Any]], user_context: Optional[str] = None, max_tokens: int = 2000) -> str`

Generate a briefing from Linear issues.

**Args:**
- `issues` (list): Issue dictionaries from Linear API
- `user_context` (str, optional): User preferences/context
- `max_tokens` (int): Maximum output tokens (default: 2000)

**Returns:**
- Generated briefing text (markdown)

**Example:**
```python
# Fetch issues
issues = await linear_client.get_my_relevant_issues()

# Generate briefing
briefing = await agent.generate_briefing(
    issues=issues,
    user_context="Focus on blocking issues",
    max_tokens=2000
)

print(briefing)
```

**Briefing Structure:**
1. Key Issues Requiring Attention (3-5 most critical)
2. Status Summary (brief overview)
3. Blockers & Risks (anything preventing progress)
4. Quick Wins (easy tasks for today)

##### `estimate_cost(input_tokens: int, output_tokens: int) -> float`

Estimate cost of API call.

**Args:**
- `input_tokens` (int): Input token count
- `output_tokens` (int): Output token count

**Returns:**
- Estimated cost in USD

**Pricing (Claude Sonnet 4, Nov 2024):**
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

**Example:**
```python
cost = agent.estimate_cost(
    input_tokens=3000,
    output_tokens=1000
)
print(f"Estimated cost: ${cost:.4f}")  # $0.0240
```

---

### Telegram Bot

**Module:** `telegram/bot.py`

Simple Telegram bot for message delivery.

#### Class: `TelegramBriefingBot`

```python
from linear_chief.telegram.bot import TelegramBriefingBot

bot = TelegramBriefingBot(
    bot_token="1234567890:ABC...",
    chat_id="123456789"
)
```

##### `__init__(bot_token: str, chat_id: str)`

Initialize Telegram bot.

**Args:**
- `bot_token` (str): Telegram bot API token
- `chat_id` (str): Target chat ID

##### `async send_briefing(message: str, parse_mode: Optional[str] = "Markdown") -> bool`

Send a briefing message to configured chat.

**Args:**
- `message` (str): Briefing text
- `parse_mode` (str, optional): Message format ("Markdown", "HTML", or None)

**Returns:**
- `True` if sent successfully, `False` otherwise

**Note:** Automatically handles messages >4096 chars by chunking.

**Example:**
```python
success = await bot.send_briefing(
    message="# Daily Briefing\n\nHere are your issues...",
    parse_mode="Markdown"
)

if success:
    print("Message sent!")
else:
    print("Failed to send")
```

##### `async test_connection() -> bool`

Test bot connection by fetching bot information.

**Returns:**
- `True` if connection successful, `False` otherwise

**Example:**
```python
if await bot.test_connection():
    print("Bot is connected!")
```

---

## Intelligence Layer

**Module:** `intelligence/analyzers.py`

Issue analysis for stagnation, blocking, and priority calculation.

### Class: `IssueAnalyzer`

```python
from linear_chief.intelligence import IssueAnalyzer

analyzer = IssueAnalyzer()
```

#### `analyze_issue(issue: Dict[str, Any]) -> AnalysisResult`

Perform complete analysis of an issue.

**Args:**
- `issue` (dict): Issue dictionary from Linear API

**Returns:**
- `AnalysisResult` dataclass with:
  - `priority` (int): Score 1-10
  - `is_stagnant` (bool): No updates for 3+ days
  - `is_blocked` (bool): Blocked by dependencies
  - `insights` (list): Actionable insights

**Example:**
```python
issues = await linear_client.get_my_relevant_issues()

for issue in issues:
    analysis = analyzer.analyze_issue(issue)

    print(f"{issue['identifier']}: Priority {analysis.priority}")

    if analysis.is_stagnant:
        print("  ⚠️ Stagnant!")

    if analysis.is_blocked:
        print("  🚫 Blocked!")

    for insight in analysis.insights:
        print(f"  💡 {insight}")
```

#### `detect_stagnation(issue: Dict[str, Any]) -> bool`

Detect if issue is stagnant (inactive for 3+ days).

**Criteria:**
- No updates for 3+ days AND
- Status is "In Progress" AND
- NOT labeled "On Hold" or "Waiting" AND
- No paused keywords in comments

**Args:**
- `issue` (dict): Issue dictionary

**Returns:**
- `True` if stagnant, `False` otherwise

#### `detect_blocking(issue: Dict[str, Any]) -> bool`

Detect if issue is blocked by external dependencies.

**Checks:**
- Blocked relationship to other issues
- "blocked" keywords in title/description
- Special blocked labels

**Args:**
- `issue` (dict): Issue dictionary

**Returns:**
- `True` if blocked, `False` otherwise

#### `calculate_priority(issue: Dict[str, Any]) -> int`

Calculate priority score (1-10) based on multiple factors.

**Factors:**
- Priority label (P0=10, P1=8, P2=5, P3=3, P4=1)
- Age (older = higher priority)
- Stagnation (stagnant = +2 points)
- Blocking (blocked = +3 points)
- Status (In Progress = +1 point)

**Args:**
- `issue` (dict): Issue dictionary

**Returns:**
- Priority score from 1-10 (10 = highest)

---

## Memory Layer

### Memory Manager

**Module:** `memory/mem0_wrapper.py`

Persistent agent memory using mem0.

#### Class: `MemoryManager`

```python
from linear_chief.memory import MemoryManager

memory = MemoryManager()
```

##### `__init__()`

Initialize MemoryManager with mem0 client or in-memory fallback.

**Fallback:** If `OPENAI_API_KEY` not set, uses in-memory storage.

##### `async add_briefing_context(briefing: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Add a briefing to agent memory for future context.

**Args:**
- `briefing` (str): Briefing text content
- `metadata` (dict, optional): Metadata (timestamp, issue count, etc.)

**Raises:**
- `Exception`: If mem0 API call fails after retries

**Retry Policy:** 3 attempts with exponential backoff

**Example:**
```python
await memory.add_briefing_context(
    briefing="# Daily Briefing...",
    metadata={
        "timestamp": "2025-11-01T09:00:00Z",
        "issue_count": 12
    }
)
```

##### `async get_agent_context(days: int = 7) -> List[Dict[str, Any]]`

Retrieve agent context from the last N days.

**Args:**
- `days` (int): Number of days of history (default: 7)

**Returns:**
- List of context items with metadata

**Example:**
```python
context = await memory.get_agent_context(days=7)

print(f"Retrieved {len(context)} context items")
for item in context:
    print(f"  - {item['metadata']['timestamp']}")
```

##### `async add_user_preference(preference: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Add a user preference to memory.

**Args:**
- `preference` (str): Preference description (e.g., "Focus on blocking issues")
- `metadata` (dict, optional): Metadata (category, priority, etc.)

**Example:**
```python
await memory.add_user_preference(
    preference="Always highlight P0 issues first",
    metadata={"category": "prioritization"}
)
```

##### `async get_user_preferences() -> List[Dict[str, Any]]`

Retrieve all user preferences.

**Returns:**
- List of user preferences with metadata

---

### Vector Store

**Module:** `memory/vector_store.py`

ChromaDB vector store for semantic search.

#### Class: `IssueVectorStore`

```python
from linear_chief.memory import IssueVectorStore

store = IssueVectorStore()
```

##### `__init__()`

Initialize ChromaDB client and embedding model.

**Embedding Model:** sentence-transformers (all-MiniLM-L6-v2, 384-dim)

##### `async add_issue(issue_id: str, title: str, description: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Add an issue to the vector store with its embedding.

**Args:**
- `issue_id` (str): Unique identifier (e.g., "PROJ-123")
- `title` (str): Issue title
- `description` (str): Issue description
- `metadata` (dict, optional): Metadata (status, assignee, labels, etc.)

**Example:**
```python
await store.add_issue(
    issue_id="ENG-123",
    title="Fix authentication bug",
    description="Users cannot login with SSO...",
    metadata={
        "state": "In Progress",
        "priority": 8
    }
)
```

##### `async search_similar(query: str, limit: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]`

Search for similar issues using semantic similarity.

**Args:**
- `query` (str): Search query text
- `limit` (int): Maximum results (default: 5)
- `filter_metadata` (dict, optional): Metadata filters (e.g., {"status": "In Progress"})

**Returns:**
- List of similar issues with metadata and similarity scores

**Example:**
```python
# Find similar issues
results = await store.search_similar(
    query="authentication problems with SSO",
    limit=5
)

for result in results:
    print(f"{result['issue_id']}: distance={result['distance']:.4f}")
    print(f"  {result['document'][:100]}...")

# With metadata filter
results = await store.search_similar(
    query="performance issues",
    limit=3,
    filter_metadata={"state": "In Progress"}
)
```

##### `async get_issue_embedding(issue_id: str) -> Optional[List[float]]`

Retrieve the embedding vector for a specific issue.

**Args:**
- `issue_id` (str): Issue identifier

**Returns:**
- Embedding vector (384-dim) or None if not found

##### `async delete_issue(issue_id: str) -> None`

Delete an issue from the vector store.

**Args:**
- `issue_id` (str): Issue identifier to delete

##### `get_stats() -> Dict[str, Any]`

Get vector store statistics.

**Returns:**
```python
{
    "total_issues": 247,
    "embedding_model": "all-MiniLM-L6-v2",
    "storage_path": "/Users/user/.linear_chief/chromadb"
}
```

---

## Storage Layer

### Database

**Module:** `storage/database.py`

SQLAlchemy engine setup and session management.

#### Functions

##### `get_engine(database_path: Union[Path, str] = DATABASE_PATH) -> Engine`

Create SQLAlchemy engine for SQLite database.

**Args:**
- `database_path` (Path | str): Database file path or ":memory:"

**Returns:**
- SQLAlchemy Engine instance

**Example:**
```python
from linear_chief.storage import get_engine

# Default database
engine = get_engine()

# Custom path
engine = get_engine("/tmp/test.db")

# In-memory
engine = get_engine(":memory:")
```

##### `init_db(engine=None) -> None`

Initialize database schema by creating all tables.

**Args:**
- `engine` (Engine, optional): SQLAlchemy engine

**Example:**
```python
from linear_chief.storage import init_db

init_db()  # Uses default engine
```

##### `get_session_maker(engine=None) -> sessionmaker`

Create session factory for database operations.

**Args:**
- `engine` (Engine, optional): SQLAlchemy engine

**Returns:**
- SessionMaker instance

##### `get_db_session(session_maker=None) -> Generator[Session, None, None]`

Get database session with automatic cleanup.

**Args:**
- `session_maker` (sessionmaker, optional): Session factory

**Yields:**
- SQLAlchemy Session

**Example:**
```python
from linear_chief.storage import get_session_maker, get_db_session

session_maker = get_session_maker()

for session in get_db_session(session_maker):
    # Use session for queries
    issues = session.query(IssueHistory).all()
    # Automatic commit on success, rollback on error
```

---

### Models

**Module:** `storage/models.py`

SQLAlchemy ORM models.

#### Class: `IssueHistory`

Track Linear issue snapshots over time.

**Columns:**
- `id` (int): Primary key
- `issue_id` (str): Issue identifier (e.g., "PROJ-123")
- `linear_id` (str): Linear UUID
- `title` (str): Issue title
- `state` (str): Issue state (e.g., "In Progress")
- `priority` (int): Priority level (0-4)
- `assignee_id` (str): Assignee UUID
- `assignee_name` (str): Assignee name
- `team_id` (str): Team UUID
- `team_name` (str): Team name
- `labels` (JSON): List of label names
- `extra_metadata` (JSON): Additional fields
- `snapshot_at` (datetime): Snapshot timestamp
- `created_at` (datetime): Record creation time

#### Class: `Briefing`

Archive of generated briefings.

**Columns:**
- `id` (int): Primary key
- `content` (str): Full briefing text (markdown)
- `issue_count` (int): Number of issues
- `agent_context` (JSON): Context used by agent
- `cost_usd` (float): Estimated cost
- `input_tokens` (int): Input token count
- `output_tokens` (int): Output token count
- `model_name` (str): Model identifier
- `delivery_status` (str): "pending", "sent", or "failed"
- `telegram_message_id` (str): Telegram message ID
- `error_message` (str): Error description
- `extra_metadata` (JSON): Additional fields
- `generated_at` (datetime): Generation timestamp
- `sent_at` (datetime): Delivery timestamp

#### Class: `Metrics`

Track operational metrics.

**Columns:**
- `id` (int): Primary key
- `metric_type` (str): Category (e.g., "api_call")
- `metric_name` (str): Identifier (e.g., "linear_fetch_issues")
- `value` (float): Numeric value
- `unit` (str): Unit (e.g., "count", "seconds", "usd")
- `extra_metadata` (JSON): Additional context
- `recorded_at` (datetime): Recording timestamp

---

### Repositories

**Module:** `storage/repositories.py`

Repository pattern implementations for data access.

#### Class: `IssueHistoryRepository`

Repository for IssueHistory operations.

##### `__init__(session: Session)`

Initialize repository with database session.

##### `save_snapshot(...) -> IssueHistory`

Save issue snapshot to history.

**Args:**
- `issue_id` (str): Issue identifier
- `linear_id` (str): Linear UUID
- `title` (str): Issue title
- `state` (str): Issue state
- `priority` (int, optional): Priority level
- `assignee_id` (str, optional): Assignee UUID
- `assignee_name` (str, optional): Assignee name
- `team_id` (str, optional): Team UUID
- `team_name` (str, optional): Team name
- `labels` (list, optional): Label names
- `extra_metadata` (dict, optional): Additional fields

**Returns:**
- Created IssueHistory instance

**Example:**
```python
from linear_chief.storage import (
    get_session_maker, get_db_session,
    IssueHistoryRepository
)

session_maker = get_session_maker()

for session in get_db_session(session_maker):
    repo = IssueHistoryRepository(session)

    snapshot = repo.save_snapshot(
        issue_id="ENG-123",
        linear_id="uuid-here",
        title="Fix bug",
        state="In Progress",
        priority=2,
        labels=["bug", "high-priority"]
    )
```

##### `get_latest_snapshot(issue_id: str) -> Optional[IssueHistory]`

Get most recent snapshot for an issue.

##### `get_snapshots_since(issue_id: str, since: datetime) -> List[IssueHistory]`

Get all snapshots for an issue since a specific time.

##### `get_all_latest_snapshots(days: int = 30) -> List[IssueHistory]`

Get latest snapshot for each unique issue in the last N days.

---

#### Class: `BriefingRepository`

Repository for Briefing operations.

##### `__init__(session: Session)`

Initialize repository with database session.

##### `create_briefing(...) -> Briefing`

Create new briefing record.

**Args:**
- `content` (str): Briefing text (markdown)
- `issue_count` (int): Number of issues
- `agent_context` (dict, optional): Context used
- `cost_usd` (float, optional): Estimated cost
- `input_tokens` (int, optional): Input tokens
- `output_tokens` (int, optional): Output tokens
- `model_name` (str, optional): Model identifier
- `extra_metadata` (dict, optional): Additional fields

**Returns:**
- Created Briefing instance

**Example:**
```python
from linear_chief.storage import BriefingRepository

for session in get_db_session(session_maker):
    repo = BriefingRepository(session)

    briefing = repo.create_briefing(
        content="# Daily Briefing...",
        issue_count=12,
        cost_usd=0.0234,
        input_tokens=3000,
        output_tokens=1000,
        model_name="claude-sonnet-4-20250514"
    )
```

##### `mark_as_sent(briefing_id: int, telegram_message_id: Optional[str] = None) -> None`

Mark briefing as successfully sent.

##### `mark_as_failed(briefing_id: int, error_message: str) -> None`

Mark briefing as failed with error message.

##### `get_recent_briefings(days: int = 7) -> List[Briefing]`

Get briefings from last N days.

##### `get_total_cost(days: int = 30) -> float`

Calculate total cost for last N days.

---

#### Class: `MetricsRepository`

Repository for Metrics operations.

##### `__init__(session: Session)`

Initialize repository with database session.

##### `record_metric(metric_type: str, metric_name: str, value: float, unit: str, extra_metadata: Optional[Dict[str, Any]] = None) -> Metrics`

Record a metric.

**Args:**
- `metric_type` (str): Category (e.g., "api_call")
- `metric_name` (str): Identifier (e.g., "linear_fetch_issues")
- `value` (float): Numeric value
- `unit` (str): Unit (e.g., "count", "seconds", "usd")
- `extra_metadata` (dict, optional): Additional context

**Returns:**
- Created Metrics instance

**Example:**
```python
from linear_chief.storage import MetricsRepository

for session in get_db_session(session_maker):
    repo = MetricsRepository(session)

    repo.record_metric(
        metric_type="api_cost",
        metric_name="anthropic_briefing",
        value=0.0234,
        unit="usd",
        extra_metadata={
            "input_tokens": 3000,
            "output_tokens": 1000
        }
    )
```

##### `get_metrics(metric_type: Optional[str] = None, metric_name: Optional[str] = None, days: int = 7) -> List[Metrics]`

Query metrics with optional filters.

##### `get_aggregated_metrics(metric_type: str, metric_name: str, days: int = 7) -> Dict[str, float]`

Get aggregated statistics for a metric.

**Returns:**
```python
{
    "sum": 0.1638,
    "avg": 0.0234,
    "min": 0.0198,
    "max": 0.0267,
    "count": 7
}
```

---

## Scheduling

**Module:** `scheduling/scheduler.py`

APScheduler wrapper for briefing automation.

### Class: `BriefingScheduler`

```python
from linear_chief.scheduling import BriefingScheduler

scheduler = BriefingScheduler(
    timezone="Europe/Prague",
    briefing_time="09:00"
)
```

#### `__init__(timezone: str = LOCAL_TIMEZONE, briefing_time: str = BRIEFING_TIME)`

Initialize scheduler with configuration.

**Args:**
- `timezone` (str): Timezone name (e.g., "Europe/Prague")
- `briefing_time` (str): Daily briefing time in HH:MM format

#### `start(briefing_job: Callable) -> None`

Start scheduler with daily briefing job.

**Args:**
- `briefing_job` (Callable): Function to execute for briefing generation

**Raises:**
- `RuntimeError`: If scheduler is already running
- `ValueError`: If briefing_time format is invalid

**Example:**
```python
from linear_chief.orchestrator import BriefingOrchestrator
import asyncio

orchestrator = BriefingOrchestrator()
scheduler = BriefingScheduler()

def briefing_job():
    asyncio.run(orchestrator.generate_and_send_briefing())

scheduler.start(briefing_job)
print(f"Next run: {scheduler.get_next_run_time()}")

# Keep running
try:
    while scheduler.is_running():
        time.sleep(1)
except KeyboardInterrupt:
    scheduler.stop()
```

#### `stop(wait: bool = True) -> None`

Stop scheduler gracefully.

**Args:**
- `wait` (bool): If True, wait for running jobs to complete

#### `is_running() -> bool`

Check if scheduler is running.

**Returns:**
- `True` if scheduler is active

#### `get_next_run_time() -> Optional[datetime]`

Get next scheduled briefing time.

**Returns:**
- Next run datetime or None if scheduler not running

#### `trigger_now() -> None`

Trigger briefing job immediately (for manual execution).

**Raises:**
- `RuntimeError`: If scheduler is not running

---

## Error Handling

All modules follow consistent error handling patterns:

1. **Logging:** All errors logged with `logger.error(..., exc_info=True)`
2. **Retry Logic:** External API calls use tenacity with exponential backoff
3. **Graceful Degradation:** Memory layer falls back to in-memory storage
4. **Clear Exceptions:** Meaningful error messages with context

**Common Patterns:**

```python
# Retry decorator for external APIs
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def api_call():
    # Your API call here
    pass

# Logging errors
import logging
logger = logging.getLogger(__name__)

try:
    result = await api_call()
except Exception as e:
    logger.error(f"API call failed: {e}", exc_info=True)
    raise
```

---

## Type Hints

All public APIs include comprehensive type hints:

```python
from typing import List, Dict, Any, Optional

async def fetch_data(
    ids: List[str],
    limit: int = 50,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    pass
```

---

## Complete Workflow Example

```python
import asyncio
from linear_chief.orchestrator import BriefingOrchestrator

async def main():
    # Initialize orchestrator (uses config.py defaults)
    orchestrator = BriefingOrchestrator()

    # Test connections
    print("Testing connections...")
    connections = await orchestrator.test_connections()

    if not all(connections.values()):
        print("Some connections failed!")
        return

    # Generate and send briefing
    print("Generating briefing...")
    result = await orchestrator.generate_and_send_briefing()

    if result["success"]:
        print(f"✓ Success!")
        print(f"  Briefing ID: {result['briefing_id']}")
        print(f"  Issues: {result['issue_count']}")
        print(f"  Cost: ${result['cost_usd']:.4f}")
        print(f"  Duration: {result['duration_seconds']:.2f}s")
    else:
        print(f"✗ Failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Additional Resources

- **Architecture:** [docs/architecture.md](/Users/padak/github/linear-agent/docs/architecture.md)
- **Coding Standards:** [docs/architecture/coding-standards.md](/Users/padak/github/linear-agent/docs/architecture/coding-standards.md)
- **Troubleshooting:** [docs/troubleshooting.md](/Users/padak/github/linear-agent/docs/troubleshooting.md)
- **CLAUDE.md:** [CLAUDE.md](/Users/padak/github/linear-agent/CLAUDE.md)
