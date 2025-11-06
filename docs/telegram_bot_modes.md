# Telegram Bot Modes - Quick Reference

## Overview

Linear Chief of Staff supports two Telegram bot modes:
1. **send_only** (default) - Simple one-way message delivery
2. **interactive** - Full bidirectional communication with handlers

## Configuration

### Environment Variable
```bash
# .env
TELEGRAM_MODE=send_only  # or "interactive"
```

### Default Behavior
- **Default:** `send_only` (backward compatible)
- **No breaking changes:** Existing installations work without modification

## send_only Mode

### Use Case
- Daily briefing delivery only
- No user interaction needed
- Minimal resource usage
- Production-ready default

### Implementation
Uses `TelegramBriefingBot` class:
```python
from linear_chief.telegram import TelegramBriefingBot

bot = TelegramBriefingBot(
    bot_token=TELEGRAM_BOT_TOKEN,
    chat_id=TELEGRAM_CHAT_ID,
)
await bot.send_briefing("Daily briefing message")
```

### Features
- ✅ Send messages
- ✅ Markdown formatting
- ✅ Connection testing
- ❌ No user commands
- ❌ No callbacks
- ❌ No feedback keyboards

## interactive Mode

### Use Case
- User commands (/start, /help, /status)
- Feedback collection (thumbs up/down)
- Issue actions (mark done, unsubscribe)
- Future conversation features

### Implementation
Uses `TelegramApplication` class:
```python
from linear_chief.telegram import TelegramApplication

app = TelegramApplication(
    bot_token=TELEGRAM_BOT_TOKEN,
    chat_id=TELEGRAM_CHAT_ID,
    polling=True,  # Enable for interactive mode
)

# Start bot (listens for messages)
await app.start()

# Send briefing with feedback keyboard
await app.send_briefing("Daily briefing...", briefing_id=123)

# Graceful shutdown
await app.stop()
```

### Features
- ✅ Send messages with keyboards
- ✅ Handle user commands
- ✅ Process feedback
- ✅ Issue actions
- ✅ Message chunking
- ✅ Connection testing

## Handler Registration (Interactive Mode)

### Command Handlers
| Command | Handler | Description |
|---------|---------|-------------|
| `/start` | `start_handler` | Welcome message |
| `/help` | `help_handler` | Available commands |
| `/status` | `status_handler` | Briefing statistics |

### Callback Handlers
| Pattern | Handler | Description |
|---------|---------|-------------|
| `^feedback_` | `feedback_callback_handler` | Thumbs up/down |
| `^issue_(done\|unsub)_` | `issue_action_callback_handler` | Issue actions |

### Message Handlers
| Filter | Handler | Description |
|--------|---------|-------------|
| `TEXT & ~COMMAND` | `text_message_handler` | User messages |

## Architecture Comparison

### send_only Mode
```
Orchestrator
    ↓
TelegramBriefingBot
    ↓
Bot.send_message()
    ↓
User receives message
```

### interactive Mode
```
Orchestrator                    User
    ↓                             ↓
TelegramApplication          Commands/Callbacks
    ↓                             ↓
Bot.send_message()          Handlers process
    ↓                             ↓
User receives message       Store feedback
with feedback keyboard
```

## Orchestrator Integration

### Mode Selection
```python
from linear_chief.orchestrator import BriefingOrchestrator

# Automatically uses TELEGRAM_MODE from config
orchestrator = BriefingOrchestrator()

# Or explicitly specify
orchestrator = BriefingOrchestrator(telegram_mode="interactive")
```

### Briefing Workflow
Both modes use the same interface:
```python
result = await orchestrator.generate_and_send_briefing()
# Returns: {"success": bool, "briefing_id": int, ...}
```

**send_only:** Sends plain message
**interactive:** Sends message with feedback keyboard

## Running Interactive Bot

### Option 1: Standalone Script
```bash
python examples/interactive_bot_example.py
```

### Option 2: With Orchestrator
```python
from linear_chief.orchestrator import BriefingOrchestrator

# Create orchestrator with interactive mode
orchestrator = BriefingOrchestrator(telegram_mode="interactive")

# Generate and send briefing (includes feedback keyboard)
await orchestrator.generate_and_send_briefing()
```

### Option 3: Separate Processes
```bash
# Terminal 1: Run interactive bot (handles user queries)
TELEGRAM_MODE=interactive python -m linear_chief.telegram.application

# Terminal 2: Run scheduler (sends daily briefings)
python -m linear_chief start
```

## Message Chunking

Both modes support automatic message chunking for long briefings:

**Telegram limit:** 4096 characters per message

**Chunking strategy:**
1. Try splitting at paragraph boundary (`\n\n`)
2. Fall back to sentence boundary (`. `, `! `, `? `)
3. Fall back to word boundary (` `)
4. Hard cut if no boundaries found

**Feedback keyboard:** Only attached to final chunk

## Error Handling

### Connection Errors
```python
success = await bot.test_connection()
if not success:
    logger.error("Telegram connection failed")
```

### Send Errors
```python
success = await bot.send_briefing("message")
if not success:
    # Logged automatically, returns False
    pass
```

### Handler Errors
All handlers include try/except blocks:
- Log error with context
- Send user-friendly error message
- Don't crash the bot

## Migration Guide

### From send_only to interactive

1. **Update .env:**
   ```bash
   TELEGRAM_MODE=interactive
   ```

2. **Restart services:**
   ```bash
   # Stop scheduler
   pkill -f "linear_chief start"

   # Start with new mode
   python -m linear_chief start
   ```

3. **Verify:**
   - Briefings now have thumbs up/down buttons
   - `/help` command works in Telegram
   - Feedback is stored in database

### Rollback
Change `.env` back to `send_only` and restart. No data loss.

## Performance Considerations

### send_only Mode
- **Memory:** ~10 MB
- **CPU:** Minimal (only during send)
- **Network:** One-time connection per briefing

### interactive Mode
- **Memory:** ~20 MB (includes handler registry)
- **CPU:** Low (event-driven)
- **Network:** Persistent connection (polling)

**Recommendation:** Use `send_only` for production unless you need user interaction.

## Security Notes

### Token Protection
- Never commit tokens to git
- Use `.env` file (in `.gitignore`)
- Validate tokens at initialization

### Callback Validation
- All callbacks use regex pattern matching
- Callback data is validated before processing
- User actions logged for audit trail

### Error Disclosure
- Internal errors logged server-side
- Generic errors sent to users
- Stack traces never exposed

## Troubleshooting

### Bot Not Responding
1. Check `TELEGRAM_MODE` in `.env`
2. Verify bot token is correct
3. Test connection: `python -m linear_chief test`
4. Check logs: `~/.linear_chief/logs/`

### Feedback Not Saved
1. Ensure `TELEGRAM_MODE=interactive`
2. Check database: `sqlite3 ~/.linear_chief/state.db`
3. Verify handlers registered: Check startup logs
4. Test callback pattern matching

### Polling Not Working
1. Only one process can poll at a time
2. Check if another instance is running
3. Use `polling=True` in TelegramApplication
4. Verify network connectivity

## API Reference

### TelegramBriefingBot (send_only)
```python
class TelegramBriefingBot:
    def __init__(bot_token: str, chat_id: str)
    async def send_briefing(message: str, parse_mode: str = "Markdown") -> bool
    async def test_connection() -> bool
```

### TelegramApplication (interactive)
```python
class TelegramApplication:
    def __init__(bot_token: str, chat_id: str, polling: bool = True)
    async def start() -> None
    async def stop() -> None
    async def send_briefing(message: str, briefing_id: int = None, parse_mode: str = "Markdown") -> bool
    async def test_connection() -> bool
    @property def is_running() -> bool
```

## Further Reading

- **Implementation Details:** `docs/phase_2.4_implementation_report.md`
- **Handler Documentation:** `src/linear_chief/telegram/handlers.py`
- **Callback Documentation:** `src/linear_chief/telegram/callbacks.py`
- **Keyboard Builders:** `src/linear_chief/telegram/keyboards.py`

---

**Last Updated:** November 5, 2025
**Status:** Production Ready
