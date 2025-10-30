# Error Handling Strategy

## General Approach

- **Error Model:** Exception-based with custom exception hierarchy
- **Exception Hierarchy:**
  - `LinearChiefError` (base)
    - `LinearAPIError` (Linear API failures)
    - `TelegramDeliveryError` (Telegram send failures)
    - `BriefingGenerationError` (Agent SDK failures)
    - `StorageError` (SQLite errors)
- **Error Propagation:** Exceptions bubble up to orchestrator, which logs and decides whether to retry or skip briefing

## Logging Standards

- **Library:** `python-json-logger` 2.0.x
- **Format:** JSON with structured fields for parsing
- **Levels:**
  - DEBUG: API request/response details (masked secrets)
  - INFO: Briefing generation start/completion, token usage
  - WARNING: Retries, rate limit warnings
  - ERROR: Failed API calls after retries, briefing failures
- **Required Context:**
  - Correlation ID: UUID per briefing generation (tracks full workflow)
  - Service Context: Module name, function name
  - User Context: User ID (Linear user ID, not PII)

**Example Log Entry:**
```json
{
  "timestamp": "2025-01-30T09:00:15.123Z",
  "level": "INFO",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "module": "linear_chief.orchestrator",
  "event": "briefing_generated",
  "issue_count": 8,
  "tokens_used": 1234,
  "cost_usd": 0.05,
  "duration_ms": 2500
}
```

## Error Handling Patterns

### External API Errors

- **Retry Policy:** Exponential backoff (1s, 2s, 4s) with max 3 attempts (tenacity library)
- **Circuit Breaker:** Not implemented for MVP (single user, low volume)
- **Timeout Configuration:** 30s per API call
- **Error Translation:** Map HTTP status codes to custom exceptions
  - 429 (rate limit) → Wait and retry
  - 4xx (client error) → Log and fail (no retry)
  - 5xx (server error) → Retry with backoff

**Alert Hooks:**
- If all retries exhausted for critical operations (Linear API, Anthropic API), trigger alert hooks:
  - Send Telegram message: "⚠️ Briefing generation failed: {error_summary}. Check logs."
  - Log ERROR with correlation_id for debugging
- Missed briefings are requeued for next hour (max 3 requeue attempts)
- After 3 failed attempts, alert user and mark briefing as "permanently_failed"

### Business Logic Errors

- **Custom Exceptions:** `StagnationDetectionError`, `InvalidIssueDataError`
- **User-Facing Errors:** Telegram message: "⚠️ Briefing generation failed. Check logs."
- **Error Codes:** Simple enum: `LINEAR_API_FAIL`, `TELEGRAM_SEND_FAIL`, `AGENT_SDK_TIMEOUT`

### Data Consistency

- **Transaction Strategy:** SQLAlchemy transactions for atomic briefing saves
- **Compensation Logic:** If Telegram delivery fails after DB save, mark briefing status as "failed"
- **Idempotency:** Briefing generation is idempotent (re-running produces same result for same timestamp)

---
