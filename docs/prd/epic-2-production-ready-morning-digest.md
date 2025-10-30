# Epic 2: Production-Ready Morning Digest

**Expanded Goal:**

Build production-grade infrastructure around the validated prototype: scheduling, Telegram delivery, state persistence, error handling, and logging. The system should run autonomously for 7+ days without intervention and deliver reliable morning briefings.

## Story 2.1: SQLite State Persistence

**As a** system,
**I want** to persist issue state and briefing history in SQLite,
**so that** I can track changes over time and avoid re-processing identical issues.

**Acceptance Criteria:**
1. `src/linear_chief/storage/models.py` defines SQLAlchemy models: `Issue`, `Briefing`
2. `Issue` table tracks: `linear_id`, `title`, `state`, `last_updated`, `last_seen_at`, `labels_json`
3. `Briefing` table tracks: `id`, `generated_at`, `issue_count`, `tokens_used`, `telegram_message_id`
4. `src/linear_chief/storage/db.py` provides `Database` class with methods: `save_issues()`, `get_last_briefing()`, `mark_issue_seen()`
5. Database file created at `~/.linear_chief/state.db` or configurable path
6. Schema migrations handled (for MVP: drop/recreate on schema change is acceptable)
7. Unit tests verify CRUD operations
8. Integration test persists 50 issues, retrieves them, verifies data integrity

## Story 2.2: Telegram Bot Integration

**As a** user,
**I want** to receive briefings via Telegram,
**so that** I can read them on mobile without opening Linear or checking email.

**Acceptance Criteria:**
1. `src/linear_chief/telegram_bot.py` module created with `TelegramNotifier` class
2. `TelegramNotifier.send_briefing(briefing_text: str)` sends formatted message via Bot API
3. Briefing uses Telegram Markdown formatting: **bold** for issue IDs, headers (###), bullet points
4. Messages exceeding 4096 chars are chunked into multiple messages
5. Bot token and chat ID configured via environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
6. Error handling: retry on network failures, log and skip on 4xx errors
7. Unit tests mock Bot API responses
8. Manual test sends sample briefing to actual Telegram account and verifies formatting

## Story 2.3: Scheduled Briefing Generation

**As a** user,
**I want** the system to automatically generate and send a briefing at 9:00 AM daily,
**so that** I receive updates without manual triggering.

**Acceptance Criteria:**
1. `src/linear_chief/scheduler.py` implements scheduling using `APScheduler` (if Agent SDK doesn't support native scheduling)
2. OR if Agent SDK supports scheduling: document and use native scheduler
3. Scheduler triggers `generate_and_send_briefing()` daily at 9:00 AM local time
4. Orchestrator workflow: fetch issues → generate briefing → persist state → send to Telegram → log metrics
5. Scheduler runs as long-running process (not cron job for MVP simplicity)
6. Graceful shutdown: catches SIGTERM/SIGINT and completes in-flight briefing
7. Logging includes: start time, issue count, tokens used, Telegram delivery status, errors
8. Manual test: set schedule to "next minute", verify briefing arrives on time (±1 min acceptable)

## Story 2.4: Robust Error Handling and Retry Logic

**As a** system operator,
**I want** the system to handle transient failures gracefully,
**so that** a single API error doesn't crash the entire agent.

**Acceptance Criteria:**
1. All API clients (Linear, Anthropic, Telegram) implement exponential backoff retry (use `tenacity` library)
2. Linear API: retry on 5xx (max 3 retries), fail after exhaustion
3. Anthropic API: retry on 5xx and rate limit (max 3 retries)
4. Telegram API: retry on network errors (max 3 retries)
5. If briefing generation fails after retries, log error and skip that day's briefing (don't crash scheduler)
6. Structured error logging includes: timestamp, error type, request payload, response status
7. Unit tests simulate network failures and verify retry behavior
8. Integration test: mock API to return 500, verify system retries and eventually logs failure

## Story 2.5: Comprehensive Logging and Observability

**As a** developer/operator,
**I want** structured JSON logs for all system events,
**so that** I can debug issues and analyze agent performance.

**Acceptance Criteria:**
1. Logging configured in `src/linear_chief/logging_config.py` using `python-json-logger`
2. All modules use logger: `logger = logging.getLogger(__name__)`
3. Log levels: DEBUG for API requests/responses, INFO for briefing generation, WARNING for retries, ERROR for failures
4. JSON log format includes: `timestamp`, `level`, `module`, `message`, `extra` (context fields)
5. Logs written to `~/.linear_chief/logs/agent.log` (rotated daily, keep 7 days)
6. Token usage logged after each Anthropic call: `{"event": "token_usage", "tokens": 1234, "cost_usd": 0.05}`
7. No PII logged (no issue descriptions, only IDs and metadata)
8. Manual review: generate 3 briefings, verify logs are parseable JSON and contain all required fields

---
