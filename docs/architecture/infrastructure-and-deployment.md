# Infrastructure and Deployment

## Infrastructure as Code

- **Tool:** Not applicable for MVP (manual setup)
- **Location:** `scripts/` directory for setup scripts
- **Approach:** Manual configuration, systemd service file for future deployment

## Deployment Strategy

- **Strategy:** Manual deployment for MVP. Future: systemd service on Ubuntu 22.04 LTS
- **CI/CD Platform:** GitHub Actions (future) - run tests on push, no auto-deploy for now
- **Pipeline Configuration:** `.github/workflows/ci.yaml` (not implemented in MVP)

## CI/CD Pipeline (Future)

**GitHub Actions Workflow:** `.github/workflows/ci.yaml`

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run linters
        run: |
          poetry run black --check .
          poetry run ruff check .
          poetry run mypy src/
      - name: Run tests
        run: |
          poetry run pytest --cov=linear_chief --cov-report=xml
      - name: Check coverage
        run: |
          poetry run coverage report --fail-under=80
      - name: Check docstring coverage
        run: |
          poetry run interrogate src/ --fail-under=100
```

**Coverage Requirements (from NFR10):**
- Unit test coverage: ≥ 80%
- Docstring coverage: 100% for public APIs
- Type hint coverage: 100% (enforced by mypy strict mode)

**Not Implemented in MVP:**
- Auto-deployment (manual deploy only)
- Security scanning (add in Phase 2)
- Performance regression tests (add after baseline established)

## Environments

- **Development:** Local machine (macOS/Linux) - `~/.linear_chief/state.db`
- **Production (future):** Digital Ocean Droplet or AWS EC2 t3.small - `/var/lib/linear_chief/state.db`

## Environment Promotion Flow

```
Development (local) → Manual testing (7 days) → Production deployment (systemd service)
```

## Rollback Strategy

- **Primary Method:** Git revert + redeploy (future cloud deployment)
- **Trigger Conditions:** Briefing failures, API errors, cost overruns
- **Recovery Time Objective:** 5 minutes (stop service, revert code, restart)

## Monitoring and Alerting

**Comprehensive Monitoring Strategy:**

### 1. Briefing Delivery Monitoring
- **Missed Briefing Detection:** Watchdog checks last briefing timestamp hourly. If >25h since last briefing, trigger alert.
- **Catch-up Plan:** Missed briefings requeued (max 3 attempts). Orchestrator checks `last_briefing_timestamp` on startup, generates catch-up if >24h gap.
- **Uptime Target:** 99% (max 1 missed/100 days)

### 2. Cost Monitoring & Alerting
- **Daily Cost Tracking:** CostTracker logs all Anthropic API calls with token counts
- **Budget Thresholds:**
  - Warning ($10/day): Log warning
  - Alert ($15/day): Telegram alert "⚠️ Cost $15 (75% of budget)"
  - Critical ($20/day): Telegram + email "🚨 Daily limit reached"
- **Monthly Projections:** Weekly cost trend report via Telegram

### 3. API Error Monitoring
- **Error Thresholds:**
  - 3 consecutive API failures: Telegram warning
  - 5 failures in 1 hour: Critical alert, consider fallback
- **Tracked Errors:** Linear API, Anthropic API, Telegram delivery
- **Alert Format:** "⚠️ 3 consecutive Linear API failures. Last: [error]"

### 4. Performance Monitoring
- **Timing:** Log per-stage timing (Linear, analysis, LLM, Telegram)
- **SLA Violation:** If >30s total, send warning (NFR1)
- **Weekly Report:** Average times, identify bottlenecks

### 5. Alert Channels
- **Primary:** Telegram to user's chat
- **Secondary:** stderr ERROR log (systemd journal)
- **Future:** Email via SMTP (optional)

### 6. Health Check Endpoint
- **HTTP:** `:8000/health` (optional, for external monitoring)
- **Response:**
  ```json
  {
    "status": "healthy",
    "last_briefing": "2025-01-30T09:00:00Z",
    "cost_today": 2.50,
    "errors_last_hour": 0
  }
  ```

**Configuration:**
- `COST_ALERT_DAILY_WARNING` = $10
- `COST_ALERT_DAILY_CRITICAL` = $20
- `ERROR_ALERT_THRESHOLD` = 3 consecutive
- `TELEGRAM_ALERT_CHAT_ID` (can be same as briefing chat)

## Database Schema Migrations

**Strategy:** Backup-before-migrate with manual rollback capability.

### Migration Process

1. **Pre-Migration Backup:**
   ```bash
   # Automatic backup before any schema change
   cp ~/.linear_chief/state.db ~/.linear_chief/backups/pre-migration-$(date +%Y%m%d-%H%M%S).db
   ```

2. **Schema Migration:**
   - **MVP Approach:** Drop and recreate on schema change (acceptable, no critical data)
   - **Phase 2 Approach:** Use Alembic for incremental migrations
   - **Implementation:**
     ```python
     # migrations/001_add_agent_context.py
     def upgrade():
         op.add_column('briefings', sa.Column('agent_context', sa.JSON, nullable=True))

     def downgrade():
         op.drop_column('briefings', 'agent_context')
     ```

3. **Rollback Procedure:**
   ```bash
   # If migration fails
   systemctl stop linear-chief  # Stop agent
   cp ~/.linear_chief/backups/pre-migration-*.db ~/.linear_chief/state.db  # Restore backup
   systemctl start linear-chief  # Restart agent
   ```

**Configuration:**
- `AUTO_BACKUP_BEFORE_MIGRATION` - Boolean, default True
- `BACKUP_RETENTION_MIGRATIONS` - Keep all pre-migration backups for 30 days

**Testing:**
- Integration test: Apply migration → Verify schema → Rollback → Verify original schema restored
- Manual test: Run migration on copy of production DB before applying to prod

**Phase 2 Migration Tools:**
When data becomes critical:
- Migrate to Alembic for incremental migrations
- Add migration verification tests
- Implement zero-downtime migration strategy (if needed)

## Backup and Restore

- **Backup Frequency:** Daily SQLite file backup to `~/.linear_chief/backups/state-{date}.db`
- **Retention Policy:** Keep 7 daily backups, 4 weekly backups (28 days total)
- **Backup Script:** `scripts/backup_db.py` run via cron
- **Restore Procedure:** Stop service, copy backup to `state.db`, restart service
- **Data Retention:** Issue metadata retained for 30 days, briefings retained indefinitely (for cost analysis)

---
