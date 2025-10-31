"""Configuration management using python-decouple for environment variables."""

from pathlib import Path
from decouple import config

# Linear API Configuration
LINEAR_API_KEY = config("LINEAR_API_KEY", default="")
LINEAR_WORKSPACE_ID = config("LINEAR_WORKSPACE_ID", default="")

# Anthropic API Configuration
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")

# OpenAI API Configuration (used by mem0)
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_CHAT_ID = config("TELEGRAM_CHAT_ID", default="")

# mem0 Configuration
MEM0_API_KEY = config("MEM0_API_KEY", default="")

# Scheduling Configuration
LOCAL_TIMEZONE = config("LOCAL_TIMEZONE", default="Europe/Prague")
BRIEFING_TIME = config("BRIEFING_TIME", default="09:00")

# Storage Configuration
DATABASE_PATH = Path(config("DATABASE_PATH", default="~/.linear_chief/state.db")).expanduser()
CHROMADB_PATH = Path(config("CHROMADB_PATH", default="~/.linear_chief/chromadb")).expanduser()
MEM0_PATH = Path(config("MEM0_PATH", default="~/.linear_chief/mem0")).expanduser()
LOGS_PATH = Path(config("LOGS_PATH", default="~/.linear_chief/logs")).expanduser()

# Embedding Model Configuration
EMBEDDING_MODEL = config("EMBEDDING_MODEL", default="all-MiniLM-L6-v2")

# Cost Tracking
MONTHLY_BUDGET_USD = config("MONTHLY_BUDGET_USD", default=20.0, cast=float)


def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHROMADB_PATH.mkdir(parents=True, exist_ok=True)
    MEM0_PATH.mkdir(parents=True, exist_ok=True)
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
