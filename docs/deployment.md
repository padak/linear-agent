# Deployment Guide

This guide covers production deployment of Linear Chief of Staff on a Linux server using systemd.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Service Configuration](#service-configuration)
- [Service Management](#service-management)
- [Monitoring](#monitoring)
- [Backup and Restore](#backup-and-restore)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements

- **Operating System:** Linux with systemd (Ubuntu 20.04+, Debian 11+, CentOS 8+, or similar)
- **Python:** 3.11 or higher
- **Memory:** Minimum 512MB RAM available
- **Storage:** Minimum 1GB free disk space
- **Network:** Outbound HTTPS access for API calls

### Required API Keys

You'll need accounts and API keys for the following services:

1. **Linear** - Project management API
   - Sign up at https://linear.app
   - Generate API key from Settings → API
   - Note your Workspace ID

2. **Anthropic** - Claude AI API
   - Sign up at https://console.anthropic.com
   - Generate API key from Account Settings
   - Ensure billing is set up (costs ~$1.80/month)

3. **Telegram** - Bot delivery
   - Create bot via [@BotFather](https://t.me/botfather)
   - Get bot token and your chat ID
   - [Tutorial](https://core.telegram.org/bots/tutorial)

4. **OpenAI** - mem0 embeddings (optional but recommended)
   - Sign up at https://platform.openai.com
   - Generate API key
   - Costs ~$0.10/month

### User Setup

It's recommended to run Linear Chief as a dedicated system user:

```bash
# Create dedicated user (no login shell)
sudo useradd -r -s /bin/false linear-chief

# Or use your existing user account
# In this guide, we'll use a regular user account for simplicity
```

## Installation

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git

# CentOS/RHEL
sudo dnf install -y python3.11 python3-pip git
```

### 2. Clone Repository

```bash
# Clone to your home directory or /opt
cd ~
git clone https://github.com/yourusername/linear-agent.git
cd linear-agent
```

### 3. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 4. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Verify installation
python -m linear_chief --help
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API keys
nano .env
```

Required configuration in `.env`:

```bash
# Linear API Configuration
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxx
LINEAR_WORKSPACE_ID=your-workspace-id

# Anthropic API Configuration
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# OpenAI API Configuration (for mem0 embeddings)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# Scheduling Configuration
LOCAL_TIMEZONE=Europe/Prague
BRIEFING_TIME=09:00

# Storage Configuration
DATABASE_PATH=~/.linear_chief/state.db
CHROMADB_PATH=~/.linear_chief/chromadb
MEM0_PATH=~/.linear_chief/mem0
LOGS_PATH=~/.linear_chief/logs

# Cost Tracking
MONTHLY_BUDGET_USD=20.0

# Disable tokenizers parallelism warning
TOKENIZERS_PARALLELISM=false
```

**Security note:** The `.env` file contains sensitive API keys. Ensure proper permissions:

```bash
chmod 600 .env
```

### 6. Initialize Database

```bash
# Activate virtual environment if not already active
source .venv/bin/activate

# Initialize database
python -m linear_chief init

# Verify initialization
ls -la ~/.linear_chief/
```

### 7. Test Connections

```bash
# Test all service connections
python -m linear_chief test

# Expected output:
# ✓ Linear: OK
# ✓ Anthropic: OK
# ✓ Telegram: OK
```

### 8. Test Manual Briefing

```bash
# Generate a test briefing
python -m linear_chief briefing

# Expected output:
# ✓ Briefing generated and sent successfully!
#   Issues: 5
#   Cost: $0.0045
#   Duration: 3.24s
#   Briefing ID: 1
```

## Service Configuration

### 1. Install systemd Service

The repository includes a systemd service file at `linear-chief.service`.

**For regular user (recommended for personal server):**

```bash
# Copy service file to user systemd directory
mkdir -p ~/.config/systemd/user
cp linear-chief.service ~/.config/systemd/user/

# Edit service file to use absolute paths
nano ~/.config/systemd/user/linear-chief.service
```

Update paths in the service file:

```ini
[Service]
WorkingDirectory=/home/yourusername/linear-agent
Environment="PATH=/home/yourusername/linear-agent/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/yourusername/linear-agent/.env
ExecStart=/home/yourusername/linear-agent/.venv/bin/python -m linear_chief start
ReadWritePaths=/home/yourusername/.linear_chief
ReadWritePaths=/home/yourusername/linear-agent
```

```bash
# Reload systemd user daemon
systemctl --user daemon-reload

# Enable service to start on boot
systemctl --user enable linear-chief.service

# Enable lingering (allows user services to run without login)
sudo loginctl enable-linger $USER
```

**For system-wide installation (dedicated user):**

```bash
# Copy service file to system directory
sudo cp linear-chief.service /etc/systemd/system/linear-chief@.service

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start for specific user
sudo systemctl enable linear-chief@yourusername.service
```

## Service Management

### Starting and Stopping

**User service:**

```bash
# Start service
systemctl --user start linear-chief.service

# Stop service
systemctl --user stop linear-chief.service

# Restart service
systemctl --user restart linear-chief.service

# Check status
systemctl --user status linear-chief.service
```

**System service:**

```bash
# Start service
sudo systemctl start linear-chief@yourusername.service

# Stop service
sudo systemctl stop linear-chief@yourusername.service

# Restart service
sudo systemctl restart linear-chief@yourusername.service

# Check status
sudo systemctl status linear-chief@yourusername.service
```

### Viewing Logs

```bash
# User service logs
journalctl --user -u linear-chief.service -f

# System service logs
sudo journalctl -u linear-chief@yourusername.service -f

# View last 50 lines
journalctl --user -u linear-chief.service -n 50

# View logs since today
journalctl --user -u linear-chief.service --since today

# View logs for specific date
journalctl --user -u linear-chief.service --since "2025-01-15" --until "2025-01-16"
```

### Updating the Application

```bash
# Stop service
systemctl --user stop linear-chief.service

# Pull latest changes
cd ~/linear-agent
git pull origin main

# Activate virtual environment
source .venv/bin/activate

# Update dependencies
pip install --upgrade -r requirements.txt

# Run database migrations if needed
python -m linear_chief init

# Restart service
systemctl --user start linear-chief.service

# Verify service is running
systemctl --user status linear-chief.service
```

## Monitoring

### Health Checks

**Check service status:**

```bash
systemctl --user is-active linear-chief.service
```

**Check scheduled job status:**

```bash
# View recent logs for scheduler activity
journalctl --user -u linear-chief.service --since "1 hour ago" | grep -i "briefing"
```

**Manual metrics check:**

```bash
# Activate virtual environment
source .venv/bin/activate

# View metrics for last 7 days
python -m linear_chief metrics --days=7

# View metrics for last 30 days
python -m linear_chief metrics --days=30

# View briefing history
python -m linear_chief history --days=7 --limit=10
```

### Cost Monitoring

```bash
# Check API costs
python -m linear_chief metrics --days=30

# Expected monthly cost breakdown:
# - Anthropic API: ~$1.80/month (30 briefings × 4K tokens × $0.003/1K)
# - OpenAI API (mem0): ~$0.10/month
# - Total: ~$2.00/month (well under $20 budget)
```

### Setting Up Alerts (Optional)

**Email alerts on service failure:**

Edit service file to include:

```ini
[Service]
# ... existing configuration ...

# Send email on failure (requires configured mail system)
OnFailure=status-email@%i.service
```

**Monitoring script (cron):**

Create monitoring script at `~/scripts/check-linear-chief.sh`:

```bash
#!/bin/bash
if ! systemctl --user is-active --quiet linear-chief.service; then
    echo "Linear Chief service is down!" | mail -s "Service Alert" your@email.com
fi
```

```bash
# Make executable
chmod +x ~/scripts/check-linear-chief.sh

# Add to crontab (check every hour)
crontab -e

# Add line:
0 * * * * /home/yourusername/scripts/check-linear-chief.sh
```

## Backup and Restore

See [Backup Strategy](./backup-strategy.md) for detailed backup procedures.

### Quick Backup

```bash
# Stop service
systemctl --user stop linear-chief.service

# Create backup
tar -czf linear-chief-backup-$(date +%Y%m%d).tar.gz \
    ~/.linear_chief/ \
    ~/linear-agent/.env \
    ~/linear-agent/pyproject.toml

# Restart service
systemctl --user start linear-chief.service

# Move backup to safe location
mv linear-chief-backup-*.tar.gz ~/backups/
```

### Quick Restore

```bash
# Stop service
systemctl --user stop linear-chief.service

# Extract backup
tar -xzf linear-chief-backup-20250115.tar.gz -C ~/

# Restart service
systemctl --user start linear-chief.service

# Verify
python -m linear_chief metrics --days=7
```

## Troubleshooting

### Service Won't Start

**Check service status:**

```bash
systemctl --user status linear-chief.service
journalctl --user -u linear-chief.service -n 50
```

**Common issues:**

1. **Missing API keys:**
   ```bash
   # Verify .env file exists and has correct permissions
   ls -la ~/linear-agent/.env
   cat ~/linear-agent/.env  # Check all keys are set
   ```

2. **Python environment issues:**
   ```bash
   # Verify virtual environment
   source ~/linear-agent/.venv/bin/activate
   python --version  # Should be 3.11+
   pip list | grep anthropic  # Should show installed packages
   ```

3. **Database corruption:**
   ```bash
   # Backup existing database
   cp ~/.linear_chief/state.db ~/.linear_chief/state.db.backup

   # Reinitialize
   source ~/linear-agent/.venv/bin/activate
   python -m linear_chief init
   ```

4. **Permission errors:**
   ```bash
   # Fix directory permissions
   chmod -R 755 ~/linear-agent
   chmod 600 ~/linear-agent/.env
   chmod -R 755 ~/.linear_chief
   ```

### Briefings Not Generating

**Check scheduler configuration:**

```bash
journalctl --user -u linear-chief.service | grep -i "scheduler\|next briefing"
```

**Verify timezone and time:**

```bash
# Check current time in configured timezone
TZ=Europe/Prague date

# Verify .env configuration
grep -E "(TIMEZONE|BRIEFING_TIME)" ~/linear-agent/.env
```

**Test manual briefing:**

```bash
source ~/linear-agent/.venv/bin/activate
python -m linear_chief briefing
```

### High API Costs

**Check metrics:**

```bash
python -m linear_chief metrics --days=30
```

**Review briefing frequency:**

- Default: 1 briefing/day (30/month)
- Expected cost: ~$1.80/month for Anthropic + ~$0.10/month for OpenAI
- If costs are higher, check for duplicate jobs or failed retries

**Reduce costs:**

```bash
# Stop service temporarily
systemctl --user stop linear-chief.service

# Review recent briefings
python -m linear_chief history --days=7

# Restart when ready
systemctl --user start linear-chief.service
```

### Memory Issues

**Check resource usage:**

```bash
# View service resource usage
systemctl --user status linear-chief.service

# Check memory limit
grep MemoryLimit ~/.config/systemd/user/linear-chief.service
```

**Adjust memory limit if needed:**

```bash
# Edit service file
nano ~/.config/systemd/user/linear-chief.service

# Change MemoryLimit (default: 512M)
MemoryLimit=1G

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart linear-chief.service
```

### Database Locked Errors

SQLite database locked errors indicate concurrent access issues.

**Solution:**

```bash
# Stop service
systemctl --user stop linear-chief.service

# Check for stale lock files
ls -la ~/.linear_chief/state.db*

# Remove journal files (safe when service is stopped)
rm -f ~/.linear_chief/state.db-journal
rm -f ~/.linear_chief/state.db-wal
rm -f ~/.linear_chief/state.db-shm

# Restart service
systemctl --user start linear-chief.service
```

## Security Considerations

### API Key Management

1. **Never commit `.env` file to git:**
   ```bash
   # Verify .gitignore includes .env
   cat .gitignore | grep .env
   ```

2. **Restrict file permissions:**
   ```bash
   chmod 600 ~/linear-agent/.env
   ```

3. **Rotate API keys periodically:**
   - Anthropic: Every 90 days
   - Linear: Every 90 days
   - Telegram: When compromised
   - OpenAI: Every 90 days

4. **Monitor for unauthorized access:**
   ```bash
   # Check for unusual API costs
   python -m linear_chief metrics --days=30
   ```

### File Permissions

```bash
# Application directory
chmod -R 755 ~/linear-agent
chmod 600 ~/linear-agent/.env

# Data directory
chmod -R 700 ~/.linear_chief
```

### Network Security

1. **Firewall configuration:**
   - Outbound HTTPS (443) required for API calls
   - No inbound ports needed

2. **API endpoints:**
   - Linear API: `api.linear.app`
   - Anthropic API: `api.anthropic.com`
   - Telegram API: `api.telegram.org`
   - OpenAI API: `api.openai.com`

### Service Hardening

The systemd service includes security hardening:

- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=read-only` - Read-only home directory (except write paths)
- `ReadWritePaths` - Explicit write permissions for data directories

### Logging

Logs are written to systemd journal and may contain sensitive information:

```bash
# Set journal retention policy
sudo nano /etc/systemd/journald.conf

# Add/modify:
MaxRetentionSec=7days
SystemMaxUse=100M

# Restart journald
sudo systemctl restart systemd-journald
```

## Production Checklist

Before deploying to production:

- [ ] All API keys configured in `.env`
- [ ] Database initialized (`python -m linear_chief init`)
- [ ] Connection test passed (`python -m linear_chief test`)
- [ ] Manual briefing test passed (`python -m linear_chief briefing`)
- [ ] Systemd service installed and enabled
- [ ] Service starts successfully
- [ ] Logs are being written to journal
- [ ] Scheduled job appears in logs
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured (optional)
- [ ] Documentation reviewed and customized

## Support

For issues and questions:

- **GitHub Issues:** https://github.com/yourusername/linear-agent/issues
- **Documentation:** https://github.com/yourusername/linear-agent/docs
- **CLAUDE.md:** Project-specific AI assistant instructions

---

**Last Updated:** 2025-01-15
