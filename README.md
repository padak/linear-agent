# Linear Chief of Staff

Intelligent Linear monitoring agent with AI-powered briefings using Anthropic's Agent SDK.

## 🚀 Status: MVP Core Complete!

**What's Working:**
- ✅ Linear GraphQL API integration
- ✅ Claude Sonnet 4 briefing generation
- ✅ Telegram bot delivery
- ✅ Environment configuration
- ✅ Integration test script

**What's Next:**
- ⏳ Memory layer (mem0 + ChromaDB)
- ⏳ Scheduling (APScheduler)
- ⏳ Persistence (SQLAlchemy)

## Features

- 🤖 **Agent SDK Integration**: Autonomous reasoning with Anthropic Claude
- 🧠 **Persistent Memory**: User preference learning with mem0
- 🔍 **Semantic Search**: Issue similarity via ChromaDB + sentence-transformers
- 📊 **Intelligent Briefings**: Daily summaries with learned prioritization
- 💬 **Conversational Interface**: Ask questions via Telegram
- ⏰ **Scheduled Delivery**: APScheduler for daily briefings

## Technology Stack

- **Agent Framework**: Anthropic Agent SDK
- **Memory Layer**: mem0 (persistent context + preferences)
- **Vector Store**: ChromaDB (semantic search)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Linear API**: httpx with hand-written GraphQL queries
- **Telegram**: python-telegram-bot
- **Database**: SQLite + SQLAlchemy (async)
- **Scheduler**: APScheduler

## Setup

### Prerequisites

- Python 3.11+
- Poetry (dependency management)
- Linear API key
- Anthropic API key
- Telegram bot token

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
pip install -r requirements-dev.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# LINEAR_API_KEY, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, etc.
```

### Configuration

Edit `.env` with your credentials:

```bash
LINEAR_API_KEY=your-linear-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id
LOCAL_TIMEZONE=Europe/Prague
BRIEFING_TIME=09:00
```

## Usage

### Run Tests

```bash
poetry run pytest
```

### Generate Manual Briefing

```bash
poetry run python -m linear_chief.cli briefing
```

### Start Scheduler (Daily Briefings)

```bash
poetry run python -m linear_chief.scheduler start
```

### View Metrics

```bash
poetry run python -m linear_chief.cli metrics
```

## Project Structure

```
linear-agent/
├── src/linear_chief/
│   ├── agent/           # Anthropic Agent SDK integration
│   ├── linear/          # Linear API client
│   ├── telegram/        # Telegram bot
│   ├── intelligence/    # Issue analysis & ranking
│   ├── memory/          # mem0 + ChromaDB integration
│   ├── storage/         # SQLite + SQLAlchemy
│   ├── scheduling/      # APScheduler
│   └── utils/           # Logging, cost tracking
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test data
└── docs/                # Documentation
```

## Development

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint code
poetry run ruff src/ tests/

# Type check
poetry run mypy src/

# Run tests with coverage
poetry run pytest --cov=linear_chief --cov-report=html
```

## Architecture

See `docs/architecture.md` for detailed architecture documentation.

## Budget

Target: **<$20/month** for Anthropic API costs
- 30 daily briefings × ~2K tokens × $0.003/1K tokens ≈ $1.80/month base
- Buffer for conversational queries and experimentation

## License

Private project - see LICENSE file.
