# Infrastructure and Deployment

## Infrastructure as Code

- **Tool:** Not applicable for MVP (manual setup)
- **Location:** `scripts/` directory for setup scripts
- **Approach:** Manual configuration, systemd service file for future deployment

## Deployment Strategy

- **Strategy:** Manual deployment for MVP. Future: systemd service on Ubuntu 22.04 LTS
- **CI/CD Platform:** GitHub Actions (future) - run tests on push, no auto-deploy for now
- **Pipeline Configuration:** `.github/workflows/ci.yaml` (not implemented in MVP)

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

- **Missed Briefing Detection:** Watchdog process checks last briefing timestamp every hour. If >25 hours since last briefing, trigger alert.
- **Alert Channels:**
  - Primary: Telegram message to user's chat (fallback channel)
  - Secondary: Log to stderr with ERROR level (monitored by systemd journal)
- **Catch-up Plan:** Missed briefings are requeued automatically. Orchestrator checks `last_briefing_timestamp` on startup and generates catch-up briefing if >24h gap.
- **Uptime Target:** 99% (max 1 missed briefing per 100 days = 7.2 hours downtime/year)
- **Health Check Endpoint:** HTTP endpoint `:8000/health` returns last briefing timestamp (future: for external monitoring)

## Backup and Restore

- **Backup Frequency:** Daily SQLite file backup to `~/.linear_chief/backups/state-{date}.db`
- **Retention Policy:** Keep 7 daily backups, 4 weekly backups (28 days total)
- **Backup Script:** `scripts/backup_db.py` run via cron
- **Restore Procedure:** Stop service, copy backup to `state.db`, restart service
- **Data Retention:** Issue metadata retained for 30 days, briefings retained indefinitely (for cost analysis)

---
