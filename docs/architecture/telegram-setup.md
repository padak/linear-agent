# Telegram Bot Setup Guide

## Initial Setup (One-Time Configuration)

### 1. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts:
   - Bot name: `Linear Chief of Staff` (display name)
   - Bot username: `linear_chief_bot` (must end in "bot")
4. **Save the API token** - you'll receive something like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### 2. Get Your Chat ID

**Method 1: Using @userinfobot**
1. Search for `@userinfobot` in Telegram
2. Start chat and send any message
3. Bot replies with your user ID (e.g., `987654321`)
4. **This is your `TELEGRAM_CHAT_ID`**

**Method 2: Using API call**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":987654321}` in JSON response
4. **That number is your `TELEGRAM_CHAT_ID`**

### 3. Start the Bot Conversation

**IMPORTANT:** You must start a conversation with your bot before it can send messages!

1. Find your bot in Telegram search (use the username from step 1)
2. Click "Start" button or send `/start`
3. Bot won't respond yet (agent not running), but this authorizes it to message you

### 4. Configure Environment Variables

Add to `.env` file:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### 5. Test Configuration

Run test script to verify setup:
```bash
poetry run python -m linear_chief.test_telegram
```

Expected output:
```
✅ Telegram bot authenticated successfully
✅ Test message sent to chat 987654321
✅ Setup complete!
```

---

## Security Considerations

**Bot Token Security:**
- **Never commit** `.env` to git (already in `.gitignore`)
- Bot token grants full control of your bot - treat like a password
- If compromised: use `/revoke` with @BotFather to invalidate, then create new bot

**Chat ID Privacy:**
- Chat ID is not sensitive (just your Telegram user ID)
- But combined with bot token, allows anyone to message you
- Keep both confidential

**Access Control:**
- MVP: Bot only sends to configured `TELEGRAM_CHAT_ID` (single user)
- Phase 2: Add whitelist validation if making bot interactive

---

## Troubleshooting

### Bot doesn't send messages
**Problem:** "Forbidden: bot can't initiate conversation"
**Solution:** You must click "Start" in bot chat first (see step 3 above)

### Wrong chat ID
**Problem:** Messages go to wrong person or fail silently
**Solution:** Verify chat ID using Method 1 or 2 above. Delete old messages and retry.

### Bot token invalid
**Problem:** API returns 401 Unauthorized
**Solution:** Check token format (should have `:` separator). Get new token from @BotFather if needed.

---

## Phase 2: Bidirectional Setup

When adding conversational queries (Phase 2), additional setup required:

1. **Webhook or Polling:**
   - MVP uses one-way sending (no webhook needed)
   - Phase 2 needs message polling: `python-telegram-bot` handles this automatically

2. **Commands Registration:**
   ```python
   # Register bot commands with @BotFather
   /help - Show available commands
   /status - Show briefing status
   /blocked - Show blocked issues
   /stale - Show stale issues
   ```

3. **Access Control:**
   - Add `TELEGRAM_ALLOWED_USER_IDS` to .env (comma-separated)
   - Bot ignores messages from unauthorized users

---

## Architecture Integration

**Configuration Loading:**
```python
# config.py
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = config("TELEGRAM_CHAT_ID")
```

**Telegram Bot Component:**
```python
# telegram/bot.py
from telegram import Bot

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.bot = Bot(token)
        self.chat_id = chat_id

    async def send_briefing(self, text: str):
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode="Markdown"
        )
```

**Environment Variables Reference:**
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | N/A | Bot API token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ Yes | N/A | Your Telegram user ID |
| `TELEGRAM_ALERT_CHAT_ID` | ❌ No | Same as above | Separate chat for alerts (optional) |

---
