# Examples

This directory contains example scripts demonstrating various features of Linear Chief of Staff.

## Interactive Bot Example

**File:** `interactive_bot_example.py`

**Description:** Runs the Telegram bot in interactive mode for bidirectional communication with users.

### Prerequisites

1. Configure Telegram bot settings in `.env`:
   ```bash
   TELEGRAM_MODE=interactive
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_CHAT_ID=your-chat-id
   ```

2. Ensure logging is configured (default: INFO level):
   ```bash
   LOG_LEVEL=INFO
   LOG_FORMAT=console
   ```

### Usage

```bash
python examples/interactive_bot_example.py
```

### Expected Output

```
2025-11-05 16:17:26 | INFO     | linear_chief.utils.logging | Logging configured
2025-11-05 16:17:26 | INFO     | __main__ | Starting Telegram bot in interactive mode...
Starting Telegram bot in interactive mode...
Press Ctrl+C to stop

# When users send messages, you'll see logs like:
2025-11-05 16:18:30 | INFO     | linear_chief.agent.context_builder | Using cached data for CSM-93
2025-11-05 16:18:31 | INFO     | linear_chief.agent.context_builder | Fetching AI-1819 from Linear API
```

### Features

The interactive bot supports:

- **Commands:**
  - `/start` - Welcome message
  - `/help` - List available commands
  - `/status` - System status

- **Natural language queries:**
  - "What issues am I working on?"
  - "Give me details on CSM-93"
  - "What's blocking AI-1819?"

- **Issue ID detection:**
  - Automatically detects issue IDs (e.g., CSM-93, AI-1819)
  - Fetches real-time details from Linear API
  - Uses intelligent caching (1-hour TTL)

- **Cache logging:**
  - Cache hits: `INFO: Using cached data for {issue_id}`
  - Cache misses: `INFO: Fetching {issue_id} from Linear API`
  - Cache saves: `INFO: Saved {issue_id} to local DB cache`

### Stopping the Bot

Press `Ctrl+C` to gracefully shut down:

```
^C
2025-11-05 16:20:00 | INFO     | __main__ | Shutting down bot...
Stopping bot...
2025-11-05 16:20:01 | INFO     | __main__ | Bot stopped
Bot stopped
```

### Troubleshooting

**No logs appearing:**
- Check `LOG_LEVEL` in `.env` (should be `INFO` or `DEBUG`)
- Verify `LOG_FORMAT=console` (not `json`)
- Logs appear on stderr (may be buffered)

**Bot not responding:**
- Ensure `TELEGRAM_MODE=interactive` in `.env`
- Check bot is started in Telegram (click "Start" button)
- Verify API keys are correct: `python -m linear_chief test`

**Cache not working:**
- Database must be initialized: `python -m linear_chief init`
- Check `~/.linear_chief/state.db` exists
- Verify `CACHE_TTL_HOURS` in `.env` (default: 1 hour)

### Configuration

All configuration via `.env` file:

```bash
# Telegram Configuration
TELEGRAM_MODE=interactive
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_CHAT_ID=your-chat-id

# Conversation Configuration
CONVERSATION_ENABLED=true
CONVERSATION_MAX_HISTORY=50
CONVERSATION_CONTEXT_DAYS=30

# Cache Configuration
CACHE_TTL_HOURS=1

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=console
LOG_FILE=  # Leave empty for console-only
```

### See Also

- **Main README:** `/README.md` - Setup and installation
- **Troubleshooting:** `/docs/troubleshooting.md` - Common issues
- **Telegram Modes:** `/docs/telegram_bot_modes.md` - Bot configuration
