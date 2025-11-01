# Linear Chief of Staff

Intelligent Linear monitoring agent with AI-powered briefings using Anthropic's Messages API.

## 🚀 Status: Sessions 1-3 Complete!

**What's Working:**
- ✅ Linear GraphQL API integration
- ✅ Claude Sonnet 4 briefing generation (Messages API)
- ✅ Telegram bot delivery
- ✅ Memory layer (mem0 + ChromaDB)
- ✅ Intelligence layer (priority, stagnation, blocking detection)
- ✅ Scheduling (APScheduler with timezone support)
- ✅ Persistent storage (SQLAlchemy + SQLite)
- ✅ CLI interface (init, test, briefing, start, metrics, history)
- ✅ Cost tracking and metrics
- ✅ 79 passing tests (unit + integration)

**What's Next:**
- ⏳ Enhanced testing and coverage (Session 4)
- ⏳ Production deployment with systemd (Session 5)

## Features

- 🤖 **Messages API Integration**: Intelligent briefings with Claude Sonnet 4
- 🧠 **Persistent Memory**: Briefing context and user preferences with mem0
- 🔍 **Semantic Search**: Issue similarity via ChromaDB + sentence-transformers
- 📊 **Intelligent Analysis**: Automatic priority calculation, stagnation detection, blocker identification
- 💬 **Telegram Delivery**: Automated daily briefings via Telegram bot
- ⏰ **Scheduled Execution**: APScheduler with timezone support for daily briefings
- 💾 **Persistent Storage**: SQLite database for issue history, briefings, and metrics
- 💰 **Cost Tracking**: Real-time monitoring of Anthropic API costs
- 🛠️ **CLI Interface**: Complete command-line interface for management

## Technology Stack

- **AI Layer**: Anthropic Messages API (Claude Sonnet 4)
- **Memory Layer**: mem0 0.1.19 (persistent context + preferences)
- **Vector Store**: ChromaDB 0.4.24 (semantic search)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, 384-dim)
- **Linear API**: httpx 0.26.0 with hand-written GraphQL queries
- **Telegram**: python-telegram-bot 20.8
- **Database**: SQLite + SQLAlchemy 2.0.34
- **Scheduler**: APScheduler 3.10.4 with timezone support
- **Retry Logic**: tenacity 9.0.0 with exponential backoff

## Setup

### Prerequisites

- Python 3.11+
- Linear API key ([Get one here](https://linear.app/settings/api))
- Anthropic API key ([Get one here](https://console.anthropic.com/settings/keys))
- Telegram bot token ([Create via @BotFather](https://t.me/botfather))
- OpenAI API key (optional, for mem0 embeddings)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd linear-agent

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt        # Production dependencies
pip install -r requirements-dev.txt    # Development + test dependencies

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: LINEAR_API_KEY, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# Optional: OPENAI_API_KEY (for mem0)
```

### Configuration

Edit `.env` with your credentials:

```bash
# Required
LINEAR_API_KEY=lin_api_...
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_CHAT_ID=123456789

# Optional (for mem0 embeddings)
OPENAI_API_KEY=sk-...

# Scheduling
LOCAL_TIMEZONE=Europe/Prague
BRIEFING_TIME=09:00

# Storage paths (defaults to ~/.linear_chief/)
DATABASE_PATH=~/.linear_chief/state.db
CHROMADB_PATH=~/.linear_chief/chromadb
MEM0_PATH=~/.linear_chief/mem0

# Optional: Disable tokenizer warnings
TOKENIZERS_PARALLELISM=false
```

**Get your Telegram Chat ID:**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789}`

## Usage

### Initialize Database

```bash
python -m linear_chief init
```

### Test Service Connections

```bash
python -m linear_chief test
```

Expected output:
```
Testing service connections...

✓ Linear: OK
✓ Telegram: OK
```

### Generate Manual Briefing

```bash
python -m linear_chief briefing
```

This will:
1. Fetch issues from Linear
2. Analyze issues (priority, stagnation, blocking)
3. Generate briefing via Claude Sonnet 4
4. Send briefing to Telegram
5. Store briefing and metrics

### Start Scheduler (Daily Briefings)

```bash
python -m linear_chief start
```

Output:
```
✓ Scheduler started successfully!
  Next briefing: 2025-11-02 09:00:00+01:00

Press Ctrl+C to stop...
```

### View Metrics and Cost Tracking

```bash
# Last 7 days (default)
python -m linear_chief metrics

# Last 30 days
python -m linear_chief metrics --days=30
```

### View Briefing History

```bash
# Last 7 days, max 10 briefings
python -m linear_chief history

# Custom range
python -m linear_chief history --days=30 --limit=20
```

### Run Tests

```bash
# All tests (79 tests)
python -m pytest tests/ -v

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# With coverage
python -m pytest --cov=src/linear_chief --cov-report=html
```

## Project Structure

```
linear-agent/
├── src/linear_chief/
│   ├── __main__.py      # CLI entry point (init, test, briefing, start, metrics, history)
│   ├── orchestrator.py  # Main 8-step workflow coordinator
│   ├── config.py        # Environment configuration
│   ├── agent/           # Messages API wrapper (BriefingAgent)
│   ├── linear/          # Linear GraphQL client (LinearClient)
│   ├── telegram/        # Telegram bot (TelegramBriefingBot)
│   ├── intelligence/    # Issue analysis (IssueAnalyzer, priority, stagnation, blocking)
│   ├── memory/          # mem0 + ChromaDB (MemoryManager, IssueVectorStore)
│   ├── storage/         # SQLite + SQLAlchemy (models, repositories, database)
│   └── scheduling/      # APScheduler (BriefingScheduler)
├── tests/
│   ├── unit/            # Unit tests (30 tests)
│   ├── integration/     # Integration tests (49 tests)
│   └── fixtures/        # Test data
├── docs/
│   ├── api.md           # Complete API reference
│   ├── troubleshooting.md  # Troubleshooting guide
│   ├── architecture.md  # Architecture documentation
│   └── ...              # Additional documentation
└── CLAUDE.md            # Development guide for Claude Code
```

## Architecture

### Data Flow

```
Scheduler (APScheduler)
    ↓
Orchestrator (8-step workflow)
    ↓
1. LinearClient → fetch issues
2. Intelligence → analyze (priority, stagnation, blocking)
3. Storage → save snapshots to SQLite
4. VectorStore → add embeddings to ChromaDB
5. Memory → get context from mem0
6. Agent (Messages API) → generate briefing with Claude
7. Telegram → send message
8. Storage → archive briefing + metrics
```

### Storage

All data stored in `~/.linear_chief/`:
- `state.db` - SQLite database (issue history, briefings, metrics)
- `chromadb/` - Vector embeddings for semantic search
- `mem0/` - mem0 local Qdrant storage + history.db
- `logs/` - Application logs (future)

See [docs/architecture.md](/Users/padak/github/linear-agent/docs/architecture.md) for detailed architecture documentation.

## Documentation

### For Users (Human-Readable Guides)

- **[API Reference](docs/api.md)** - Complete API documentation with examples
- **[Deployment Guide](docs/deployment.md)** - Production deployment with systemd
- **[Backup Strategy](docs/backup-strategy.md)** - Backup procedures and scripts
- **[Logging Guide](docs/logging.md)** - Configure structured logging
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common errors and solutions
- **[Filtering Strategy](docs/filtering-strategy.md)** - How issue filtering works

### For AI Assistants (Claude Code Instructions)

- **[CLAUDE.md](CLAUDE.md)** - Primary development guide and coding standards
- **[Architecture](docs/architecture.md)** - High-level design decisions
- **[Architecture Details](docs/architecture/)** - Detailed technical specifications
- **[PRD](docs/prd.md)** - Product requirements and epics
- **[Progress](docs/progress.md)** - Implementation status (Sessions 1-5 complete)

### Reports & Implementation Notes

- **[Test Coverage Analysis](docs/reports/)** - Coverage reports and test strategies
- **[Logging Implementation](docs/reports/)** - Structured logging summary
- **[E2E Tests](tests/e2e/)** - End-to-end integration tests

## Development

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

# Run tests with coverage
python -m pytest --cov=src/linear_chief --cov-report=html
```

### Development Commands

See [CLAUDE.md](CLAUDE.md) for complete development guide including:
- Environment setup
- Testing strategies
- Common patterns
- Technology decisions
- Known gotchas

## Cost & Budget

Target: **<$20/month**

**Estimated Costs:**
- Anthropic API (Claude Sonnet 4): ~$1.80/month
  - 30 daily briefings × 4K tokens × $0.003/1K input + $0.015/1K output
- OpenAI API (mem0 embeddings): ~$0.10/month (optional)
- All other components run locally: $0

**Actual Pricing (Nov 2024):**
- Claude Sonnet 4: $3.00/M input tokens, $15.00/M output tokens
- OpenAI embeddings: $0.10/M tokens

**Monitor costs:**
```bash
python -m linear_chief metrics --days=30
```

## Troubleshooting

**Common issues:**
- API connection failures → Check `.env` API keys
- Database errors → Run `python -m linear_chief init`
- Telegram not working → Verify `TELEGRAM_CHAT_ID` and bot started
- mem0 fallback → Add `OPENAI_API_KEY` to `.env` (optional)

See [docs/troubleshooting.md](docs/troubleshooting.md) for complete troubleshooting guide.

## Contributing

This is a personal learning project. See [CLAUDE.md](CLAUDE.md) for development guidelines.

## License

Private project - see LICENSE file.
