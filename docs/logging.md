# Logging Guide

This guide covers the structured logging system for Linear Chief of Staff. The application uses `python-json-logger` to provide both JSON-structured logs (for production) and human-readable console logs (for development).

## Table of Contents

- [Configuration](#configuration)
- [Log Formats](#log-formats)
- [Using Structured Logging](#using-structured-logging)
- [Context Injection](#context-injection)
- [Performance Logging](#performance-logging)
- [Best Practices](#best-practices)
- [Integration with Monitoring Tools](#integration-with-monitoring-tools)
- [Troubleshooting](#troubleshooting)

## Configuration

### Environment Variables

Configure logging via `.env` file:

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Format: "console" (development) or "json" (production)
LOG_FORMAT=console

# Optional: Path to log file for persistent logs
LOG_FILE=~/.linear_chief/logs/app.log
```

### Default Settings

- **LOG_LEVEL**: `INFO` - Good balance between visibility and noise
- **LOG_FORMAT**: `console` - Human-readable for development
- **LOG_FILE**: `None` - Logs only to stderr by default

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed diagnostic information | GraphQL query details, internal state |
| **INFO** | General informational messages | Workflow steps, API calls, success events |
| **WARNING** | Warning messages for non-critical issues | Deprecated features, recoverable errors |
| **ERROR** | Error messages for failures | API failures, database errors |
| **CRITICAL** | Critical failures requiring immediate attention | System crashes, data corruption |

## Log Formats

### Console Format (Development)

Human-readable logs with color coding:

```
2025-11-01 09:00:15 | INFO     | linear_chief.orchestrator | Fetching issues from Linear [request_id=briefing-a1b2c3d4]
2025-11-01 09:00:16 | INFO     | linear_chief.orchestrator | Fetched issues from Linear [request_id=briefing-a1b2c3d4]
2025-11-01 09:00:17 | ERROR    | linear_chief.linear.client | GraphQL query failed [request_id=briefing-a1b2c3d4]
```

**Color Coding:**
- DEBUG: Cyan
- INFO: Green
- WARNING: Yellow
- ERROR: Red
- CRITICAL: Magenta

### JSON Format (Production)

Structured JSON logs for parsing and analysis:

```json
{
  "timestamp": "2025-11-01T09:00:15Z",
  "level": "INFO",
  "logger": "linear_chief.orchestrator",
  "message": "Fetching issues from Linear",
  "process": 12345,
  "thread": 67890,
  "request_id": "briefing-a1b2c3d4",
  "step": 1,
  "total_steps": 8,
  "operation": "fetch_issues"
}
```

```json
{
  "timestamp": "2025-11-01T09:00:16Z",
  "level": "INFO",
  "logger": "linear_chief.agent.briefing_agent",
  "message": "Briefing generated successfully",
  "request_id": "briefing-a1b2c3d4",
  "service": "Anthropic",
  "input_tokens": 3245,
  "output_tokens": 987,
  "total_tokens": 4232,
  "model": "claude-sonnet-4-20250514"
}
```

## Using Structured Logging

### Basic Usage

```python
from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)

# Simple log message
logger.info("Operation completed")

# Structured log with extra fields
logger.info("Briefing generated", extra={
    "briefing_id": 123,
    "issue_count": 15,
    "cost_usd": 0.05,
    "duration_seconds": 2.34
})
```

### Error Logging with Stack Traces

```python
try:
    result = await dangerous_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        extra={
            "operation": "dangerous_operation",
            "error_type": type(e).__name__,
            "retry_attempt": 3
        },
        exc_info=True  # Include full stack trace
    )
    raise
```

### Service-Specific Logging

```python
# Linear API
logger.info("Fetching issues", extra={
    "service": "Linear",
    "viewer_id": "abc123",
    "category": "assigned"
})

# Anthropic API
logger.info("Generating briefing", extra={
    "service": "Anthropic",
    "model": "claude-sonnet-4",
    "issue_count": 10,
    "max_tokens": 2000
})

# Telegram
logger.info("Sending briefing", extra={
    "service": "Telegram",
    "chat_id": "123456789",
    "message_length": 1234
})
```

### Workflow Step Logging

```python
logger.info("Step 1/8: Fetching issues from Linear", extra={
    "step": 1,
    "total_steps": 8,
    "operation": "fetch_issues"
})

# ... do work ...

logger.info("Step 1 completed", extra={
    "step": 1,
    "issue_count": 15,
    "duration_seconds": 1.23
})
```

## Context Injection

The logging system supports automatic context injection using context variables. This allows you to set identifiers that will be included in all log messages within a context.

### Using LogContext Manager

```python
from linear_chief.utils.logging import LogContext, get_logger

logger = get_logger(__name__)

async def generate_briefing():
    request_id = f"briefing-{uuid.uuid4().hex[:8]}"

    with LogContext(request_id=request_id):
        # All logs within this context will include request_id
        logger.info("Starting workflow")  # Includes request_id
        await fetch_issues()              # Logs include request_id
        await generate_content()          # Logs include request_id
        logger.info("Workflow completed") # Includes request_id
```

### Manual Context Setting

```python
from linear_chief.utils.logging import set_request_id, set_session_id, clear_context

# Set context variables
set_request_id("req-abc123")
set_session_id("session-xyz789")

# All logs will include these IDs
logger.info("Processing request")

# Clear context when done
clear_context()
```

### Available Context Variables

- **request_id**: Unique identifier for a request/workflow
- **session_id**: Session identifier for user sessions
- **user_id**: User identifier

## Performance Logging

### Execution Time Decorator

Use the `log_execution_time` decorator to automatically log function execution time:

```python
from linear_chief.utils.logging import get_logger, log_execution_time

logger = get_logger(__name__)

@log_execution_time(logger, "fetch_issues")
async def fetch_issues():
    # ... implementation ...
    return issues
```

This will automatically log:
- Start of operation
- Duration on completion
- Errors with duration if failed

Output (JSON format):
```json
{
  "timestamp": "2025-11-01T09:00:15Z",
  "level": "INFO",
  "message": "fetch_issues completed",
  "operation": "fetch_issues",
  "duration_seconds": 1.234,
  "success": true
}
```

### Manual Performance Logging

```python
from datetime import datetime

start_time = datetime.utcnow()

# ... do work ...

duration = (datetime.utcnow() - start_time).total_seconds()

logger.info("Operation completed", extra={
    "operation": "complex_workflow",
    "duration_seconds": duration,
    "items_processed": 100
})
```

## Best Practices

### 1. Use Structured Data

**Good:**
```python
logger.info("Briefing generated", extra={
    "briefing_id": 123,
    "issue_count": 15,
    "cost_usd": 0.05
})
```

**Bad:**
```python
logger.info(f"Briefing 123 generated with 15 issues, cost: $0.05")
```

### 2. Include Context in Errors

**Good:**
```python
logger.error("API call failed", extra={
    "service": "Linear",
    "error_type": type(e).__name__,
    "retry_attempt": attempt,
    "endpoint": "/graphql"
}, exc_info=True)
```

**Bad:**
```python
logger.error(f"Error: {e}")
```

### 3. Use Appropriate Log Levels

```python
# DEBUG: Detailed diagnostic info
logger.debug("GraphQL query", extra={"query": query})

# INFO: Normal workflow events
logger.info("Issues fetched", extra={"count": 10})

# WARNING: Non-critical issues
logger.warning("Using fallback configuration", extra={"reason": "API unavailable"})

# ERROR: Failures
logger.error("Failed to send telegram message", exc_info=True)

# CRITICAL: System-level failures
logger.critical("Database connection lost")
```

### 4. Don't Log Sensitive Data

**Never log:**
- API keys
- Passwords
- Tokens
- Personal information (emails, names) - unless necessary and GDPR-compliant
- Full request/response bodies (may contain sensitive data)

**Safe to log:**
- IDs (issue IDs, briefing IDs)
- Counts and metrics
- Timestamps
- Status codes
- Error types (not full error messages if they contain sensitive data)

### 5. Use Request IDs for Tracing

```python
with LogContext(request_id=request_id):
    # All operations within this context can be traced
    await step_1()
    await step_2()
    await step_3()
```

This makes it easy to filter logs for a specific workflow execution.

### 6. Log Business Metrics

```python
logger.info("Briefing workflow completed", extra={
    "briefing_id": 123,
    "issue_count": 15,
    "high_priority_count": 3,
    "cost_usd": 0.05,
    "duration_seconds": 5.67,
    "workflow_status": "success"
})
```

## Integration with Monitoring Tools

### Elasticsearch/ELK Stack

JSON logs can be directly ingested into Elasticsearch:

```bash
# Stream logs to Elasticsearch
python -m linear_chief briefing | filebeat -e -c filebeat.yml
```

Example `filebeat.yml`:
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - ~/.linear_chief/logs/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
```

### Datadog

Configure Datadog to parse JSON logs:

```bash
# In .env
LOG_FORMAT=json
LOG_FILE=~/.linear_chief/logs/app.log
```

Datadog agent configuration:
```yaml
logs:
  - type: file
    path: /Users/padak/.linear_chief/logs/app.log
    service: linear-chief
    source: python
```

### CloudWatch Logs

Use AWS CloudWatch agent to ship logs:

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/user/.linear_chief/logs/app.log",
            "log_group_name": "/linear-chief/application",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

### Prometheus Metrics from Logs

Extract metrics from structured logs:

```python
# mtail configuration to extract Prometheus metrics
counter briefings_generated by briefing_id
histogram briefing_duration_seconds buckets 0.5, 1, 2, 5, 10, 30

/Briefing workflow completed/ {
  briefings_generated++
  briefing_duration_seconds = $duration_seconds
}
```

## Troubleshooting

### No Logs Appearing

**Check log level:**
```bash
# Set to DEBUG temporarily
echo "LOG_LEVEL=DEBUG" >> .env
python -m linear_chief briefing
```

**Check log format:**
```bash
# Try console format for visibility
echo "LOG_FORMAT=console" >> .env
```

### Logs Too Verbose

**Increase log level:**
```bash
echo "LOG_LEVEL=WARNING" >> .env
```

**Filter by logger name:**
```python
# In code, suppress noisy third-party loggers
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
```

### JSON Logs Not Parsing

**Validate JSON:**
```bash
# Check if logs are valid JSON
tail -1 ~/.linear_chief/logs/app.log | jq .
```

**Common issues:**
- Newlines in message field
- Unescaped quotes
- Binary data in log fields

### File Logging Not Working

**Check permissions:**
```bash
ls -la ~/.linear_chief/logs/
# Should be writable by your user
```

**Check disk space:**
```bash
df -h ~/.linear_chief/logs/
```

**Check log file path:**
```bash
# In .env
LOG_FILE=/absolute/path/to/log/file.log
```

### Context Variables Not Appearing

**Ensure LogContext is used:**
```python
# WRONG - context not set
logger.info("Message")

# RIGHT - context set
with LogContext(request_id="req-123"):
    logger.info("Message")  # Will include request_id
```

## Example: Complete Workflow Logging

```python
from linear_chief.utils.logging import get_logger, LogContext
import uuid
from datetime import datetime

logger = get_logger(__name__)

async def generate_and_send_briefing():
    start_time = datetime.utcnow()
    request_id = f"briefing-{uuid.uuid4().hex[:8]}"

    with LogContext(request_id=request_id):
        try:
            # Step 1
            logger.info("Step 1/8: Fetching issues", extra={
                "step": 1,
                "total_steps": 8,
                "operation": "fetch_issues"
            })
            issues = await fetch_issues()
            logger.info("Fetched issues", extra={
                "issue_count": len(issues),
                "step": 1
            })

            # Step 2
            logger.info("Step 2/8: Analyzing issues", extra={
                "step": 2,
                "operation": "analyze_issues"
            })
            analyzed = await analyze_issues(issues)

            # Step 3
            logger.info("Step 3/8: Generating briefing", extra={
                "step": 3,
                "operation": "generate_briefing",
                "service": "Anthropic"
            })
            briefing = await generate_briefing(analyzed)

            # Success
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info("Workflow completed successfully", extra={
                "issue_count": len(issues),
                "duration_seconds": duration,
                "workflow_status": "success"
            })

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error("Workflow failed", extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_seconds": duration,
                "workflow_status": "failed"
            }, exc_info=True)
            raise
```

## Summary

The structured logging system provides:

1. **Flexible Formatting**: JSON for production, console for development
2. **Context Injection**: Automatic request/session tracking
3. **Rich Metadata**: Structured fields for analysis
4. **Performance Tracking**: Built-in execution time logging
5. **Integration Ready**: Works with ELK, Datadog, CloudWatch, etc.
6. **Best Practices Built-in**: Suppresses noisy third-party loggers

Use this system to gain visibility into your application's behavior, debug issues, and monitor performance in production.
