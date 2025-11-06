# Troubleshooting Guide

Complete troubleshooting guide for Linear Chief of Staff, covering common errors, API issues, database problems, and performance optimization.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [API Connection Issues](#api-connection-issues)
  - [Linear API](#linear-api)
  - [Anthropic API](#anthropic-api)
  - [Telegram Bot](#telegram-bot)
  - [OpenAI API (mem0)](#openai-api-mem0)
- [Database Issues](#database-issues)
- [Memory Layer Issues](#memory-layer-issues)
  - [mem0 Issues](#mem0-issues)
  - [ChromaDB Issues](#chromadb-issues)
- [Scheduler Issues](#scheduler-issues)
- [Performance Problems](#performance-problems)
- [Cost Tracking Issues](#cost-tracking-issues)
- [Environment Configuration](#environment-configuration)
- [Common Error Messages](#common-error-messages)
- [Debug Mode](#debug-mode)
- [Getting Help](#getting-help)

---

## Quick Diagnostics

### Run the Test Command

The fastest way to diagnose issues is to run the built-in test command:

```bash
python -m linear_chief test
```

**Expected Output:**
```
Testing service connections...

✓ Linear: OK
✓ Telegram: OK
```

**If any service fails:**
1. Check your `.env` file for correct API keys
2. Verify API keys are active and not expired
3. Check network connectivity
4. Review error logs

### Check Environment Variables

```bash
# Verify .env file exists
ls -la .env

# Check if required variables are set (don't display values)
python -c "
from linear_chief.config import *
import sys

required = [
    ('LINEAR_API_KEY', LINEAR_API_KEY),
    ('ANTHROPIC_API_KEY', ANTHROPIC_API_KEY),
    ('TELEGRAM_BOT_TOKEN', TELEGRAM_BOT_TOKEN),
    ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID),
]

missing = [name for name, val in required if not val]
if missing:
    print(f'Missing: {missing}')
    sys.exit(1)
else:
    print('All required variables set')
"
```

### Check Database

```bash
# Check if database exists
ls -la ~/.linear_chief/state.db

# Initialize database if missing
python -m linear_chief init
```

### Check Logs

```bash
# If using systemd
journalctl -u linear-chief -f

# If running manually, check stdout/stderr
# Add this to your .env for verbose logging:
# LOG_LEVEL=DEBUG

# When running interactive bot or test scripts
# Logs appear in console (stderr) by default
# Cache hit/miss messages show as:
# INFO: Using cached data for AI-1819
# INFO: Fetching CSM-93 from Linear API
```

---

## API Connection Issues

### Linear API

#### Error: "Linear connection failed"

**Symptoms:**
```
✗ Linear: FAILED
```

**Causes & Solutions:**

1. **Invalid API Key**
   ```bash
   # Check API key format (should start with "lin_api_")
   echo $LINEAR_API_KEY | cut -c1-8
   # Should output: lin_api_
   ```

   **Solution:** Generate a new API key at https://linear.app/settings/api

2. **Network Issues**
   ```bash
   # Test connectivity
   curl -H "Authorization: $LINEAR_API_KEY" \
        -H "Content-Type: application/json" \
        https://api.linear.app/graphql \
        -d '{"query": "{ viewer { id } }"}'
   ```

   **Expected:** JSON response with viewer data
   **If fails:** Check firewall, proxy settings, or network connectivity

3. **Rate Limiting**

   Linear API has rate limits (typically 1000 requests/hour).

   **Symptoms:**
   - HTTP 429 errors
   - "Too Many Requests" messages

   **Solution:**
   ```python
   # The LinearClient automatically retries with exponential backoff
   # If persistent, reduce request frequency or contact Linear support
   ```

4. **GraphQL Query Errors**

   **Symptoms:**
   ```
   GraphQL query failed: [{'message': 'Field not found', ...}]
   ```

   **Solution:**
   - Check Linear API docs for field changes
   - Verify GraphQL query syntax in `linear/client.py`
   - Update queries if Linear API changed

#### Error: "No issues to report"

**Symptoms:**
```
Fetched 0 issues
No issues to report today. All clear!
```

**Causes:**
1. **No relevant issues exist**
   - Check Linear workspace for assigned/created/subscribed issues
   - Verify you're using the correct Linear account

2. **Filter too restrictive**
   ```python
   # Check what issues are being fetched
   from linear_chief.linear import LinearClient
   import asyncio

   async def debug():
       client = LinearClient(api_key="...")
       viewer = await client.get_viewer()
       print(f"Logged in as: {viewer['name']} ({viewer['email']})")

       assigned = await client.get_issues(assignee_id=viewer['id'])
       print(f"Assigned: {len(assigned)}")

       all_relevant = await client.get_my_relevant_issues()
       print(f"Relevant: {len(all_relevant)}")

   asyncio.run(debug())
   ```

---

### Anthropic API

#### Error: "Failed to generate briefing"

**Symptoms:**
```python
anthropic.APIError: 401 Unauthorized
```

**Causes & Solutions:**

1. **Invalid API Key**
   ```bash
   # Check API key format (should start with "sk-ant-")
   echo $ANTHROPIC_API_KEY | cut -c1-7
   # Should output: sk-ant-
   ```

   **Solution:** Generate new key at https://console.anthropic.com/settings/keys

2. **Insufficient Credits**

   **Symptoms:**
   - HTTP 402 errors
   - "Payment required" messages

   **Solution:**
   - Check billing at https://console.anthropic.com/settings/billing
   - Add payment method or increase limits

3. **Rate Limiting**

   **Symptoms:**
   - HTTP 429 errors
   - "Too many requests" messages

   **Solution:**
   - Wait and retry (automatic with tenacity retry logic)
   - Reduce briefing frequency
   - Upgrade to higher tier plan

4. **Token Limit Exceeded**

   **Symptoms:**
   ```
   anthropic.APIError: 400 prompt is too long
   ```

   **Solution:**
   ```python
   # Reduce max_tokens or number of issues
   # In agent/briefing_agent.py, adjust:
   max_tokens = 1500  # Instead of 2000

   # Or limit issues in orchestrator.py:
   issues = issues[:20]  # Limit to 20 issues
   ```

5. **Model Not Available**

   **Symptoms:**
   ```
   anthropic.APIError: 404 model not found
   ```

   **Solution:**
   ```python
   # Check available models and update in .env or code
   # Current default: claude-sonnet-4-20250514
   # Alternative: claude-3-5-sonnet-20241022
   ```

---

### Telegram Bot

#### Error: "Failed to send Telegram message"

**Symptoms:**
```
telegram.error.TelegramError: 401 Unauthorized
```

**Causes & Solutions:**

1. **Invalid Bot Token**
   ```bash
   # Test token directly
   curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
   ```

   **Expected:** JSON with bot information
   **If error:** Generate new token via @BotFather

2. **Invalid Chat ID**

   **Symptoms:**
   ```
   telegram.error.TelegramError: 400 Bad Request: chat not found
   ```

   **Solution:**
   ```bash
   # Find your chat ID
   # 1. Send a message to your bot
   # 2. Run this command:
   curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates" | jq '.result[0].message.chat.id'

   # Update TELEGRAM_CHAT_ID in .env
   ```

3. **Bot Not Started**

   **Symptoms:**
   - Message not received
   - No error in logs

   **Solution:**
   - Open Telegram
   - Search for your bot
   - Click "Start" button
   - Try sending briefing again

4. **Message Too Long**

   Telegram has a 4096 character limit per message.

   **Note:** The bot automatically handles this by chunking messages.

   **If still failing:**
   ```python
   # In telegram/bot.py, check chunking logic
   # Or reduce briefing length in agent config
   ```

5. **Network/Firewall Issues**

   ```bash
   # Test Telegram API connectivity
   curl -I https://api.telegram.org
   ```

   **Solution:** Check firewall rules, proxy settings

---

### OpenAI API (mem0)

#### Error: "Failed to initialize mem0 client"

**Symptoms:**
```
mem0 library not installed, using in-memory fallback
```

**Causes & Solutions:**

1. **Missing OPENAI_API_KEY**

   mem0 uses OpenAI for embeddings.

   ```bash
   # Check if set
   echo ${OPENAI_API_KEY:+SET}
   # Should output: SET
   ```

   **Solution:**
   ```bash
   # Add to .env
   OPENAI_API_KEY=sk-...
   ```

   **Note:** System falls back to in-memory storage if missing (graceful degradation).

2. **Invalid OpenAI API Key**

   ```bash
   # Test key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

   **Expected:** List of models
   **If error:** Generate new key at https://platform.openai.com/api-keys

3. **mem0 Library Issues**

   **Symptoms:**
   ```
   ImportError: No module named 'mem0'
   ```

   **Solution:**
   ```bash
   pip install mem0==0.1.19
   ```

4. **Qdrant Storage Path Issues**

   **Symptoms:**
   ```
   PermissionError: [Errno 13] Permission denied: '/tmp/qdrant'
   ```

   **Solution:**
   ```bash
   # Ensure MEM0_PATH is writable
   mkdir -p ~/.linear_chief/mem0
   chmod 755 ~/.linear_chief/mem0

   # Verify in .env
   MEM0_PATH=~/.linear_chief/mem0
   ```

---

## Database Issues

### Error: "Database initialization failed"

**Symptoms:**
```bash
$ python -m linear_chief init
✗ Database initialization failed: ...
```

**Causes & Solutions:**

1. **Permission Denied**

   ```bash
   # Check permissions
   ls -ld ~/.linear_chief/
   # Should be writable

   # Fix permissions
   mkdir -p ~/.linear_chief
   chmod 755 ~/.linear_chief
   ```

2. **Disk Space Full**

   ```bash
   # Check disk space
   df -h ~/.linear_chief/

   # Clean up if needed
   rm -rf ~/.linear_chief/chromadb
   rm ~/.linear_chief/state.db
   python -m linear_chief init
   ```

3. **Corrupted Database**

   **Symptoms:**
   ```
   sqlite3.DatabaseError: database disk image is malformed
   ```

   **Solution:**
   ```bash
   # Backup and recreate
   mv ~/.linear_chief/state.db ~/.linear_chief/state.db.backup
   python -m linear_chief init

   # If backup needed, try to recover:
   sqlite3 ~/.linear_chief/state.db.backup ".recover" | sqlite3 ~/.linear_chief/state.db
   ```

### Error: "Database locked"

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Causes & Solutions:**

1. **Multiple Processes**

   **Solution:**
   ```bash
   # Find processes using database
   lsof ~/.linear_chief/state.db

   # Stop conflicting processes
   pkill -f "linear_chief"

   # Restart
   python -m linear_chief start
   ```

2. **WAL Mode Issue**

   SQLite WAL (Write-Ahead Logging) mode is enabled by default.

   **Solution:**
   ```bash
   # Check WAL mode
   sqlite3 ~/.linear_chief/state.db "PRAGMA journal_mode;"

   # Should output: wal

   # If issues persist, disable WAL:
   sqlite3 ~/.linear_chief/state.db "PRAGMA journal_mode=DELETE;"
   ```

### Error: "Table does not exist"

**Symptoms:**
```
sqlite3.OperationalError: no such table: issue_history
```

**Solution:**
```bash
# Reinitialize database
python -m linear_chief init
```

---

## Memory Layer Issues

### mem0 Issues

#### Error: "mem0 API call failed after retries"

**Symptoms:**
```
tenacity.RetryError: RetryError[<Future at ...>]
```

**Causes & Solutions:**

1. **Network Issues**

   ```bash
   # Check OpenAI API connectivity
   curl -I https://api.openai.com
   ```

2. **Rate Limiting**

   **Solution:** System will retry automatically. If persistent:
   ```python
   # Reduce retry attempts in memory/mem0_wrapper.py
   @retry(stop=stop_after_attempt(2))  # Instead of 3
   ```

3. **Invalid Configuration**

   **Symptoms:**
   ```
   TypeError: 'QdrantConfig' object is not subscriptable
   ```

   **Solution:** This is fixed in current code. Ensure you're using:
   ```python
   memory_config = MemoryConfig(
       vector_store={
           "provider": "qdrant",
           "config": {  # Must be dict, not QdrantConfig object
               "collection_name": "mem0",
               "path": str(MEM0_PATH)
           }
       }
   )
   ```

#### Error: "In-memory fallback active"

**Symptoms:**
```
MEM0_API_KEY not set, using in-memory storage
```

**Impact:** Memory not persisted across restarts.

**Solution:**
```bash
# Add OpenAI API key to .env (mem0 uses OpenAI for embeddings)
OPENAI_API_KEY=sk-...

# Restart application
python -m linear_chief start
```

---

### ChromaDB Issues

#### Error: "Failed to initialize IssueVectorStore"

**Symptoms:**
```
RuntimeError: ChromaDB not found
```

**Causes & Solutions:**

1. **ChromaDB Not Installed**

   ```bash
   pip install chromadb==0.4.24
   ```

2. **Storage Path Issues**

   ```bash
   # Check path exists and is writable
   mkdir -p ~/.linear_chief/chromadb
   chmod 755 ~/.linear_chief/chromadb
   ```

#### Warning: "ChromaDB duplicate ID warnings"

**Symptoms:**
```
Warning: ID already exists in collection
```

**Cause:** Using `add()` instead of `upsert()`.

**Impact:** Harmless but inefficient.

**Solution:** Current code uses `upsert()`. If you see this:
```python
# In memory/vector_store.py, ensure:
self._collection.upsert(  # Not add()
    ids=[issue_id],
    embeddings=[embedding],
    ...
)
```

#### Error: "Embedding model download failed"

**Symptoms:**
```
OSError: Can't load tokenizer for 'all-MiniLM-L6-v2'
```

**Solution:**
```bash
# Download model manually
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Check disk space (model is ~90MB)
df -h

# If persistent, use different model in .env:
EMBEDDING_MODEL=paraphrase-MiniLM-L6-v2
```

#### Issue: "Clear ChromaDB storage"

To reset vector store (e.g., after testing):

```bash
# Stop application
pkill -f "linear_chief"

# Remove ChromaDB data
rm -rf ~/.linear_chief/chromadb

# Restart (will recreate empty store)
python -m linear_chief start
```

---

## Scheduler Issues

### Error: "Scheduler failed to start"

**Symptoms:**
```bash
$ python -m linear_chief start
✗ Scheduler failed: ...
```

**Causes & Solutions:**

1. **Invalid BRIEFING_TIME Format**

   **Symptoms:**
   ```
   ValueError: BRIEFING_TIME must be in HH:MM format
   ```

   **Solution:**
   ```bash
   # Check .env
   BRIEFING_TIME=09:00  # Correct
   # Not: 9:00, 9am, etc.
   ```

2. **Invalid Timezone**

   **Symptoms:**
   ```
   pytz.exceptions.UnknownTimeZoneError: 'Invalid/Timezone'
   ```

   **Solution:**
   ```bash
   # Use valid timezone name
   LOCAL_TIMEZONE=Europe/Prague  # Correct
   LOCAL_TIMEZONE=America/New_York
   LOCAL_TIMEZONE=UTC

   # List all timezones:
   python -c "import pytz; print('\n'.join(pytz.all_timezones))"
   ```

3. **Scheduler Already Running**

   **Symptoms:**
   ```
   RuntimeError: Scheduler is already running
   ```

   **Solution:**
   ```bash
   # Kill existing process
   pkill -f "linear_chief"

   # Restart
   python -m linear_chief start
   ```

### Issue: "Briefing not running at scheduled time"

**Diagnostics:**

1. **Check next run time**
   ```bash
   # Start scheduler and note the "Next briefing" time
   python -m linear_chief start
   # Should show: Next briefing: 2025-11-02 09:00:00+01:00
   ```

2. **Verify timezone**
   ```bash
   # Check system time matches expected timezone
   date
   TZ=$LOCAL_TIMEZONE date
   ```

3. **Check scheduler is running**
   ```bash
   ps aux | grep linear_chief
   ```

4. **Check logs for errors**
   ```bash
   # If using systemd
   journalctl -u linear-chief -f
   ```

### Issue: "Manual trigger not working"

```python
from linear_chief.scheduling import BriefingScheduler

scheduler = BriefingScheduler()
# scheduler.start(job)  # Must start first!
scheduler.trigger_now()  # Error: Scheduler not running
```

**Solution:** Call `start()` before `trigger_now()`.

---

## Performance Problems

### Issue: "Briefing generation too slow"

**Symptoms:**
- Duration >10 seconds
- Timeout errors

**Diagnostics:**

```python
# Add timing to orchestrator.py workflow
import time

start = time.time()
# ... step 1 ...
print(f"Step 1: {time.time() - start:.2f}s")
```

**Optimizations:**

1. **Reduce Issue Count**
   ```python
   # In orchestrator.py
   issues = issues[:30]  # Limit to 30 most relevant
   ```

2. **Reduce Token Usage**
   ```python
   # In agent/briefing_agent.py
   max_tokens = 1500  # Instead of 2000
   ```

3. **Optimize Embeddings**
   ```bash
   # Use smaller model in .env
   EMBEDDING_MODEL=all-MiniLM-L3-v2  # Faster but less accurate
   ```

4. **Disable Semantic Search**
   ```python
   # Comment out step 4 in orchestrator.py
   # await store.add_issue(...)  # Skip vector store
   ```

### Issue: "High memory usage"

**Symptoms:**
- OOM errors
- Slow performance

**Solutions:**

1. **Check ChromaDB size**
   ```bash
   du -sh ~/.linear_chief/chromadb
   # If >1GB, consider cleanup
   ```

2. **Limit issue history**
   ```python
   # In storage/repositories.py
   days = 7  # Instead of 30 for get_all_latest_snapshots()
   ```

3. **Clear old embeddings**
   ```bash
   # Remove old ChromaDB data
   rm -rf ~/.linear_chief/chromadb/*
   ```

### Issue: "Database growing too large"

**Check size:**
```bash
du -sh ~/.linear_chief/state.db
```

**Solutions:**

1. **Archive old data**
   ```sql
   -- Connect to database
   sqlite3 ~/.linear_chief/state.db

   -- Delete old snapshots (>90 days)
   DELETE FROM issue_history WHERE snapshot_at < datetime('now', '-90 days');

   -- Delete old briefings (>90 days)
   DELETE FROM briefings WHERE generated_at < datetime('now', '-90 days');

   -- Delete old metrics (>90 days)
   DELETE FROM metrics WHERE recorded_at < datetime('now', '-90 days');

   -- Vacuum to reclaim space
   VACUUM;
   ```

2. **Implement rotation**
   Add to cron (Linux/Mac):
   ```cron
   # Rotate every month
   0 0 1 * * sqlite3 ~/.linear_chief/state.db "DELETE FROM issue_history WHERE snapshot_at < datetime('now', '-90 days'); VACUUM;"
   ```

---

## Cost Tracking Issues

### Issue: "Cost estimates incorrect"

**Causes:**

1. **Outdated pricing**

   Check current Anthropic pricing at https://www.anthropic.com/pricing

   **Update in `agent/briefing_agent.py`:**
   ```python
   def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
       input_cost = (input_tokens / 1_000_000) * 3.00  # Update rate
       output_cost = (output_tokens / 1_000_000) * 15.00  # Update rate
       return input_cost + output_cost
   ```

2. **Token counts not captured**

   **Solution:** Modify orchestrator to capture actual usage:
   ```python
   # In orchestrator.py, after generate_briefing():
   # (Requires modifying BriefingAgent to return usage)
   input_tokens = response.usage.input_tokens
   output_tokens = response.usage.output_tokens
   ```

### Issue: "Exceeding budget"

**Check current spend:**
```bash
python -m linear_chief metrics --days=30
```

**Solutions:**

1. **Reduce frequency**
   ```bash
   # In .env, change to every other day or weekly
   # Or manually trigger only when needed
   ```

2. **Optimize prompts**
   - Reduce issue descriptions (already truncated to 300 chars)
   - Limit number of issues
   - Use shorter system prompt

3. **Use cheaper model**
   ```python
   # Not recommended - quality will decrease
   model = "claude-3-haiku-20240307"  # Cheaper but lower quality
   ```

---

## Environment Configuration

### Issue: ".env file not loaded"

**Symptoms:**
```
linear_chief.config: WARNING: LINEAR_API_KEY not set
```

**Solutions:**

1. **Check .env location**
   ```bash
   # Must be in project root
   ls -la .env
   ```

2. **Check .env format**
   ```bash
   # No quotes needed, no spaces around =
   # Correct:
   LINEAR_API_KEY=lin_api_abc123

   # Wrong:
   LINEAR_API_KEY = "lin_api_abc123"
   ```

3. **Reload environment**
   ```bash
   # After editing .env, restart application
   pkill -f linear_chief
   python -m linear_chief start
   ```

### Issue: "Path expansion not working"

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: '~/.linear_chief/state.db'
```

**Solution:** Paths are automatically expanded via `Path.expanduser()` in `config.py`.

**Workaround:**
```bash
# Use absolute path in .env
DATABASE_PATH=/Users/yourname/.linear_chief/state.db
```

---

## Common Error Messages

### "TOKENIZERS_PARALLELISM warning"

**Full Error:**
```
huggingface/tokenizers: The current process just got forked, after parallelism has already been used. Disabling parallelism to avoid deadlocks...
```

**Impact:** Harmless warning from sentence-transformers.

**Solution:**
```bash
# Add to .env
TOKENIZERS_PARALLELISM=false
```

### "SQLAlchemy reserved word: metadata"

**Error:**
```
AttributeError: 'Metadata' object has no attribute '...'
```

**Cause:** Using `metadata` as column name (reserved by SQLAlchemy).

**Solution:** Already fixed in models - uses `extra_metadata` instead.

### "Connection pool timeout"

**Error:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Cause:** Too many concurrent database connections.

**Solution:**
```python
# Close sessions properly
for session in get_db_session(session_maker):
    # Use session
    pass  # Automatically closed
```

---

## Debug Mode

### Enable Verbose Logging

**Method 1: Environment Variable**
```bash
# Add to .env
LOG_LEVEL=DEBUG
```

**Method 2: Code**
```python
# In __main__.py or your script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Enable SQL Debugging

```python
# In storage/database.py
engine = create_engine(
    db_url,
    echo=True,  # Shows all SQL queries
    ...
)
```

### Enable httpx Debugging (Linear API)

```python
import httpx
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)
```

### Inspect API Responses

```python
# Add after API calls
import json
print(json.dumps(response_data, indent=2))
```

---

## Getting Help

### 1. Check Existing Documentation

- **README.md:** Setup and basic usage
- **CLAUDE.md:** Architecture and development patterns
- **docs/architecture.md:** Design decisions
- **docs/api.md:** Complete API reference

### 2. Review Test Files

Test files show working examples:
- `tests/integration/test_workflow.py`
- `test_integration.py`
- `test_memory_integration.py`

### 3. Enable Debug Logging

```bash
# Run with verbose output
LOG_LEVEL=DEBUG python -m linear_chief briefing
```

### 4. Check Issue Tracker

Search GitHub issues for similar problems (if applicable).

### 5. Collect Debug Information

When asking for help, provide:

```bash
# System info
python --version
pip list | grep -E "(linear|anthropic|telegram|mem0|chroma|sqlalchemy)"

# Config (sanitized)
python -c "
from linear_chief.config import *
print(f'Database: {DATABASE_PATH}')
print(f'ChromaDB: {CHROMADB_PATH}')
print(f'Timezone: {LOCAL_TIMEZONE}')
print(f'Briefing time: {BRIEFING_TIME}')
"

# Test results
python -m linear_chief test

# Recent logs (if using systemd)
journalctl -u linear-chief --since "1 hour ago"
```

---

## Prevention & Best Practices

### 1. Regular Health Checks

```bash
# Daily
python -m linear_chief test

# Weekly
python -m linear_chief metrics --days=7

# Monthly
python -m linear_chief metrics --days=30
```

### 2. Monitor Database Size

```bash
# Add to cron (monthly)
0 0 1 * * du -sh ~/.linear_chief/state.db | mail -s "DB Size" you@example.com
```

### 3. Backup Database

```bash
# Weekly backup
cp ~/.linear_chief/state.db ~/.linear_chief/state.db.backup-$(date +%Y%m%d)

# Keep only last 4 weeks
find ~/.linear_chief -name "state.db.backup-*" -mtime +28 -delete
```

### 4. Test Before Production

```bash
# Always test after changes
python -m linear_chief test
python -m linear_chief briefing  # Manual test
```

### 5. Use Version Control for Config

```bash
# Track .env.example (not .env with secrets!)
git add .env.example
git commit -m "Update config template"
```

### 6. Monitor API Costs

```bash
# Check weekly
python -m linear_chief metrics --days=7

# Set up alerts if costs exceed threshold
# (Implementation depends on your monitoring setup)
```

---

## Recovery Procedures

### Complete Reset

If all else fails:

```bash
# 1. Stop all processes
pkill -f linear_chief

# 2. Backup data
cp -r ~/.linear_chief ~/.linear_chief.backup

# 3. Clean slate
rm -rf ~/.linear_chief

# 4. Reinitialize
python -m linear_chief init

# 5. Test
python -m linear_chief test

# 6. Manual briefing
python -m linear_chief briefing
```

### Restore from Backup

```bash
# Stop application
pkill -f linear_chief

# Restore database
cp ~/.linear_chief/state.db.backup ~/.linear_chief/state.db

# Restart
python -m linear_chief start
```

---

## Platform-Specific Issues

### macOS

**Issue: "Operation not permitted"**

Solution: Grant terminal Full Disk Access in System Preferences > Security & Privacy.

### Linux (systemd)

**Issue: Service not starting**

```bash
# Check service status
systemctl status linear-chief

# Check logs
journalctl -u linear-chief -n 50

# Restart service
systemctl restart linear-chief
```

### Windows

**Issue: Path issues**

Windows paths should use forward slashes in .env:
```bash
DATABASE_PATH=C:/Users/YourName/.linear_chief/state.db
```

Or double backslashes:
```bash
DATABASE_PATH=C:\\Users\\YourName\\.linear_chief\\state.db
```

---

## Still Having Issues?

If this guide doesn't solve your problem:

1. Enable debug logging
2. Collect error messages and logs
3. Document steps to reproduce
4. Check if it's a known issue in documentation
5. Consider filing a bug report (if applicable)

Remember: Most issues are configuration-related. Double-check your `.env` file and API keys first!
