# Security

## Input Validation

- **Validation Library:** Pydantic (for DTO models)
- **Validation Location:** At API boundary (Linear client, config loading)
- **Required Rules:**
  - All environment variables must be validated on startup (missing API keys → fail fast)
  - Linear issue data must be sanitized (strip HTML, limit description length)
  - Telegram message content must escape Markdown special chars

## Authentication & Authorization

- **Auth Method:** API key-based for all external services (no OAuth for MVP)
- **Session Management:** N/A (no user sessions, agent runs as single user)
- **Required Patterns:**
  - API keys loaded from environment variables only
  - Never log API keys (mask in logs: `LINEAR_API_KEY=sk-***...***`)

## Secrets Management

- **Development:** `.env` file (gitignored) loaded via `python-decouple`
- **Production (Phase 1 - systemd):** Environment variables set in systemd service file (`/etc/systemd/system/linear-chief.service`)
- **Production (Phase 2 - cloud):** Migrate to OS keychain (macOS Keychain, Linux `secret-tool`) or cloud secret manager (AWS Secrets Manager, GCP Secret Manager)
  - **Upgrade Path:** Implement `SecretsProvider` interface with multiple backends (env vars, keychain, cloud)
  - **Migration Timeline:** Before remote deployment (Week 4+)
- **Code Requirements:**
  - NEVER hardcode secrets
  - Access via `config.py` module only (abstracts secret provider)
  - No secrets in logs or error messages

## API Security

- **Rate Limiting:** Respect external API limits (Linear: 100 req/min, Telegram: 30 msg/sec)
- **CORS Policy:** N/A (no web interface)
- **Security Headers:** N/A (no HTTP server)
- **HTTPS Enforcement:** All external API calls use HTTPS (httpx verifies SSL by default)

## Phase 2: Bidirectional Telegram Security

**Threat Model:** When agent accepts user commands/queries, must prevent:
1. Unauthorized users sending commands to bot
2. Command injection or prompt injection attacks
3. Abuse via excessive queries (DoS)

### Chat ID Validation

**Implementation:**
```python
# telegram/bot.py
class TelegramBot:
    def __init__(self, token, allowed_chat_ids):
        self.bot = Bot(token)
        self.allowed_chat_ids = set(allowed_chat_ids)

    async def on_message(self, update):
        chat_id = update.message.chat.id

        # Validate sender
        if chat_id not in self.allowed_chat_ids:
            logger.warning(f"Unauthorized message from {chat_id}")
            await self.bot.send_message(
                chat_id=chat_id,
                text="⛔ Unauthorized. This bot is private."
            )
            return  # Ignore message

        # Process authorized message
        await self.handle_command(update.message)
```

**Configuration:**
```bash
# .env
TELEGRAM_ALLOWED_CHAT_IDS=987654321,123456789  # Comma-separated list
```

**Multi-User Phase:**
- Store authorized users in database instead of .env
- Add admin commands: `/add_user 123456789`, `/remove_user 123456789`
- Require admin approval for new users

### Command Authorization

**Principle:** All commands require authentication, even from allowed chat IDs.

**Implementation:**
```python
AUTHORIZED_COMMANDS = {
    "/help", "/status", "/blocked", "/stale",
    "/query"  # Natural language queries
}

async def handle_command(self, message):
    command = message.text.split()[0]

    if command not in AUTHORIZED_COMMANDS:
        await self.bot.send_message(
            chat_id=message.chat.id,
            text=f"⛔ Unknown command: {command}. Use /help for available commands."
        )
        return

    # Execute authorized command
    await self.execute_command(command, message)
```

**Prompt Injection Prevention:**
- Sanitize user input before passing to LLM
- Use structured commands, not free-form text (where possible)
- Validate query length (max 500 characters)

### Rate Limiting

**Prevent abuse via excessive queries:**

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests=10, window_minutes=1):
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.requests = defaultdict(list)  # chat_id -> [timestamp, ...]

    def is_allowed(self, chat_id):
        now = datetime.now()

        # Remove old requests outside window
        self.requests[chat_id] = [
            ts for ts in self.requests[chat_id]
            if now - ts < self.window
        ]

        # Check limit
        if len(self.requests[chat_id]) >= self.max_requests:
            return False

        # Allow and record
        self.requests[chat_id].append(now)
        return True

# Usage
rate_limiter = RateLimiter(max_requests=10, window_minutes=1)

async def on_message(self, update):
    chat_id = update.message.chat.id

    if not rate_limiter.is_allowed(chat_id):
        await self.bot.send_message(
            chat_id=chat_id,
            text="⏱️ Rate limit exceeded. Try again in 1 minute."
        )
        return

    # Process message
    await self.handle_command(update.message)
```

**Configuration:**
- `RATE_LIMIT_QUERIES_PER_MINUTE` - Default 10
- `RATE_LIMIT_BRIEFINGS_PER_DAY` - Default 5 (manual triggers)

### Data Privacy (Phase 2)

**User Queries and Context:**
- Store queries in database for learning (with user consent)
- Implement data retention policy (delete queries > 90 days)
- Provide `/delete_my_data` command for GDPR compliance

**Logging:**
- Log commands but not query content (may contain sensitive info)
- Mask user IDs in logs: `chat_id=***54321` (last 5 digits only)

---

## Security Checklist (Phase 2 Launch)

Before enabling bidirectional Telegram:
- [ ] Chat ID whitelist configured in .env
- [ ] Rate limiting enabled
- [ ] Command injection tests pass
- [ ] Unknown command handling tested
- [ ] Data retention policy documented
- [ ] Privacy policy provided to users (if storing queries)

## Data Protection

- **Encryption at Rest:** SQLite database file permissions set to 0600 (owner read/write only)
- **Encryption in Transit:** All API calls use TLS 1.2+ (httpx default)
- **PII Handling:** No PII stored (issue IDs and titles only, no user emails or names)
- **Logging Restrictions:** Never log issue descriptions (may contain sensitive data)

## Dependency Security

- **Scanning Tool:** `safety` library (checks dependencies for known vulnerabilities)
- **Update Policy:** Update dependencies monthly, security patches immediately
- **Approval Process:** Review changelogs before updating major versions

## Security Testing

- **SAST Tool:** Bandit (Python security linter) in GitHub Actions (future)
- **DAST Tool:** Not applicable (no web interface)
- **Penetration Testing:** Not applicable for MVP (single-user local deployment)

---
