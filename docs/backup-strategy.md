# Backup and Restore Strategy

This document outlines the backup strategy for Linear Chief of Staff, including what to back up, frequency recommendations, and restore procedures.

## Table of Contents

- [Overview](#overview)
- [What to Back Up](#what-to-back-up)
- [Backup Methods](#backup-methods)
- [Backup Frequency](#backup-frequency)
- [Automated Backups](#automated-backups)
- [Restore Procedures](#restore-procedures)
- [Disaster Recovery](#disaster-recovery)
- [Storage Recommendations](#storage-recommendations)

## Overview

Linear Chief of Staff stores persistent data in `~/.linear_chief/` by default. This includes:
- SQLite database with briefing history and metrics
- ChromaDB vector embeddings for semantic search
- mem0 conversation memory and context

**Critical data:** Configuration (`.env`) and database (`state.db`)
**Important data:** Vector embeddings and memory storage
**Size:** Typically 100-500MB total after several months of operation

## What to Back Up

### Critical Files (Required for Recovery)

1. **Environment Configuration**
   - **Path:** `~/linear-agent/.env`
   - **Contains:** API keys, scheduling configuration, storage paths
   - **Size:** ~2KB
   - **Backup frequency:** After any changes
   - **Security:** Highly sensitive - encrypt backups

2. **SQLite Database**
   - **Path:** `~/.linear_chief/state.db`
   - **Contains:**
     - Issue history snapshots
     - Briefing archive (content, metadata, delivery status)
     - Metrics (API costs, token usage, performance)
   - **Size:** 10-50MB (grows ~1-2MB/month)
   - **Backup frequency:** Daily
   - **Critical:** Yes - contains all historical data

3. **Database Journal Files**
   - **Path:** `~/.linear_chief/state.db-wal`, `state.db-shm`
   - **Contains:** Uncommitted transactions (SQLite Write-Ahead Log)
   - **Backup frequency:** Include in database backups
   - **Note:** Only exist when database is in use

### Important Files (Recommended for Full Recovery)

4. **ChromaDB Vector Store**
   - **Path:** `~/.linear_chief/chromadb/`
   - **Contains:** Issue embeddings for semantic search
   - **Size:** 50-200MB (depends on issue count)
   - **Backup frequency:** Weekly
   - **Recoverable:** Yes - can be rebuilt from Linear API, but time-consuming

5. **mem0 Memory Storage**
   - **Path:** `~/.linear_chief/mem0/`
   - **Contains:**
     - Conversation context history
     - User preferences
     - Qdrant vector database
   - **Size:** 20-100MB
   - **Backup frequency:** Weekly
   - **Recoverable:** Partially - recent briefings can rebuild context

### Optional Files

6. **Application Code**
   - **Path:** `~/linear-agent/`
   - **Contains:** Python application code
   - **Backup frequency:** Only if you have local modifications
   - **Note:** Can be restored from Git repository

7. **Service Configuration**
   - **Path:** `~/.config/systemd/user/linear-chief.service`
   - **Contains:** systemd service definition
   - **Size:** ~2KB
   - **Backup frequency:** After any changes

## Backup Methods

### Method 1: Simple Tar Archive (Recommended for Personal Use)

**Full backup script:**

```bash
#!/bin/bash
# backup-linear-chief.sh

BACKUP_DIR=~/backups/linear-chief
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="linear-chief-${TIMESTAMP}.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop service for consistent backup
systemctl --user stop linear-chief.service

# Create compressed archive
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    ~/.linear_chief/ \
    ~/linear-agent/.env \
    ~/.config/systemd/user/linear-chief.service \
    2>/dev/null

# Restart service
systemctl --user start linear-chief.service

# Verify backup
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "Backup created: ${BACKUP_DIR}/${BACKUP_FILE}"
    ls -lh "${BACKUP_DIR}/${BACKUP_FILE}"
else
    echo "Backup failed!"
    exit 1
fi

# Optional: Remove backups older than 30 days
find "$BACKUP_DIR" -name "linear-chief-*.tar.gz" -mtime +30 -delete
```

**Make executable and run:**

```bash
chmod +x backup-linear-chief.sh
./backup-linear-chief.sh
```

### Method 2: Database-Only Backup (Fastest, Daily Use)

For quick daily backups without stopping the service:

```bash
#!/bin/bash
# backup-database-only.sh

BACKUP_DIR=~/backups/linear-chief/db
TIMESTAMP=$(date +%Y%m%d)
BACKUP_FILE="state-${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

# Copy database using SQLite backup command (safe while running)
sqlite3 ~/.linear_chief/state.db ".backup '${BACKUP_DIR}/${BACKUP_FILE}'"

# Compress
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

echo "Database backup created: ${BACKUP_DIR}/${BACKUP_FILE}.gz"
```

### Method 3: Incremental Rsync Backup

For efficient incremental backups to remote server:

```bash
#!/bin/bash
# backup-rsync.sh

REMOTE_HOST="backup-server.example.com"
REMOTE_PATH="/backups/linear-chief"
LOCAL_PATH=~/.linear_chief

# Stop service
systemctl --user stop linear-chief.service

# Rsync with compression and deletion tracking
rsync -avz --delete \
    "$LOCAL_PATH" \
    "${REMOTE_HOST}:${REMOTE_PATH}/"

# Also backup .env separately (encrypted)
openssl enc -aes-256-cbc -salt -pbkdf2 \
    -in ~/linear-agent/.env \
    -out /tmp/env.enc
rsync -avz /tmp/env.enc "${REMOTE_HOST}:${REMOTE_PATH}/"
rm /tmp/env.enc

# Restart service
systemctl --user start linear-chief.service
```

### Method 4: Cloud Backup (AWS S3, Google Cloud Storage)

Example using AWS S3:

```bash
#!/bin/bash
# backup-to-s3.sh

BUCKET="s3://my-backups/linear-chief"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create local backup first
tar -czf /tmp/linear-chief-${TIMESTAMP}.tar.gz \
    ~/.linear_chief/ \
    ~/linear-agent/.env

# Upload to S3 with encryption
aws s3 cp /tmp/linear-chief-${TIMESTAMP}.tar.gz \
    "${BUCKET}/linear-chief-${TIMESTAMP}.tar.gz" \
    --storage-class STANDARD_IA \
    --server-side-encryption AES256

# Cleanup
rm /tmp/linear-chief-${TIMESTAMP}.tar.gz

# Set lifecycle policy to delete after 90 days
# (configure once in S3 console or CLI)
```

## Backup Frequency

### Recommended Schedule

| Data Type | Frequency | Method | Retention |
|-----------|-----------|--------|-----------|
| Database | Daily | SQLite backup | 30 days |
| Full backup | Weekly | Tar archive | 90 days |
| ChromaDB | Weekly | Tar archive | 30 days |
| mem0 | Weekly | Tar archive | 30 days |
| .env file | On change | Encrypted copy | Indefinite |
| Service config | On change | Copy | Indefinite |

### Minimal Strategy (Low Effort)

- **Daily:** Database backup only
- **Weekly:** Full backup to external drive
- **On change:** Manual .env backup

### Comprehensive Strategy (Recommended)

- **Daily:** Automated database backup with compression
- **Weekly:** Full system backup to remote server
- **Monthly:** Cloud backup for disaster recovery
- **On change:** Immediate .env and config backups

## Automated Backups

### Cron Job Setup

**Daily database backup (2 AM):**

```bash
# Edit crontab
crontab -e

# Add line:
0 2 * * * /home/yourusername/scripts/backup-database-only.sh >> /home/yourusername/logs/backup.log 2>&1
```

**Weekly full backup (Sunday 3 AM):**

```bash
# Add to crontab:
0 3 * * 0 /home/yourusername/scripts/backup-linear-chief.sh >> /home/yourusername/logs/backup.log 2>&1
```

**Monthly cloud backup (1st of month, 4 AM):**

```bash
# Add to crontab:
0 4 1 * * /home/yourusername/scripts/backup-to-s3.sh >> /home/yourusername/logs/backup.log 2>&1
```

### Systemd Timer (Alternative to Cron)

Create timer unit at `~/.config/systemd/user/linear-chief-backup.timer`:

```ini
[Unit]
Description=Daily backup of Linear Chief database

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Create service unit at `~/.config/systemd/user/linear-chief-backup.service`:

```ini
[Unit]
Description=Linear Chief Database Backup

[Service]
Type=oneshot
ExecStart=/home/yourusername/scripts/backup-database-only.sh
StandardOutput=journal
StandardError=journal
```

Enable timer:

```bash
systemctl --user daemon-reload
systemctl --user enable linear-chief-backup.timer
systemctl --user start linear-chief-backup.timer

# Check status
systemctl --user list-timers
```

### Backup Monitoring

**Verify backups exist:**

```bash
#!/bin/bash
# check-backups.sh

BACKUP_DIR=~/backups/linear-chief
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/linear-chief-*.tar.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backups found!"
    exit 1
fi

# Check if backup is less than 25 hours old
BACKUP_AGE=$(( $(date +%s) - $(stat -f %m "$LATEST_BACKUP") ))
if [ $BACKUP_AGE -gt 90000 ]; then  # 25 hours in seconds
    echo "WARNING: Latest backup is more than 24 hours old!"
    exit 1
fi

echo "OK: Latest backup is $(($BACKUP_AGE / 3600)) hours old"
echo "File: $LATEST_BACKUP"
ls -lh "$LATEST_BACKUP"
```

**Add to daily cron:**

```bash
0 12 * * * /home/yourusername/scripts/check-backups.sh >> /home/yourusername/logs/backup-check.log 2>&1
```

## Restore Procedures

### Full System Restore

**From tar archive:**

```bash
# 1. Stop service if running
systemctl --user stop linear-chief.service

# 2. Backup current state (just in case)
mv ~/.linear_chief ~/.linear_chief.old

# 3. Extract backup
tar -xzf ~/backups/linear-chief/linear-chief-20250115_120000.tar.gz -C ~/

# 4. Verify permissions
chmod 600 ~/linear-agent/.env
chmod -R 700 ~/.linear_chief

# 5. Restart service
systemctl --user start linear-chief.service

# 6. Verify restoration
python -m linear_chief metrics --days=7
python -m linear_chief test

# 7. Remove old backup if successful
rm -rf ~/.linear_chief.old
```

### Database-Only Restore

**From SQLite backup:**

```bash
# 1. Stop service
systemctl --user stop linear-chief.service

# 2. Backup current database
cp ~/.linear_chief/state.db ~/.linear_chief/state.db.backup

# 3. Decompress and restore
gunzip -c ~/backups/linear-chief/db/state-20250115.db.gz > ~/.linear_chief/state.db

# 4. Remove WAL files (force full recovery)
rm -f ~/.linear_chief/state.db-wal
rm -f ~/.linear_chief/state.db-shm

# 5. Verify database integrity
sqlite3 ~/.linear_chief/state.db "PRAGMA integrity_check;"

# 6. Restart service
systemctl --user start linear-chief.service

# 7. Verify
python -m linear_chief metrics --days=30
```

### Partial Restore (ChromaDB or mem0)

**Restore ChromaDB only:**

```bash
# Stop service
systemctl --user stop linear-chief.service

# Remove current ChromaDB
rm -rf ~/.linear_chief/chromadb

# Extract from backup (preserving structure)
tar -xzf ~/backups/linear-chief/linear-chief-20250115_120000.tar.gz \
    --strip-components=2 \
    -C ~/.linear_chief \
    .linear_chief/chromadb

# Restart service
systemctl --user start linear-chief.service
```

**Rebuild ChromaDB from scratch:**

If backups are corrupted or too old, you can rebuild embeddings:

```bash
# This requires a custom script (not yet implemented)
# For now, ChromaDB will rebuild automatically as new issues are processed

# Clear ChromaDB
rm -rf ~/.linear_chief/chromadb

# Restart service - it will rebuild embeddings incrementally
systemctl --user start linear-chief.service
```

### Configuration-Only Restore

**Restore .env file:**

```bash
# From encrypted backup
openssl enc -aes-256-cbc -d -pbkdf2 \
    -in ~/backups/env.enc \
    -out ~/linear-agent/.env

# Set permissions
chmod 600 ~/linear-agent/.env

# Verify
cat ~/linear-agent/.env

# Restart service
systemctl --user restart linear-chief.service
```

## Disaster Recovery

### Complete System Loss

**Recovery steps:**

1. **Set up new server:**
   ```bash
   # Install Python 3.11+
   sudo apt update && sudo apt install -y python3.11 python3.11-venv git
   ```

2. **Clone repository:**
   ```bash
   cd ~
   git clone https://github.com/yourusername/linear-agent.git
   cd linear-agent
   ```

3. **Create virtual environment:**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Restore configuration:**
   ```bash
   # From encrypted backup
   openssl enc -aes-256-cbc -d -pbkdf2 \
       -in /path/to/backup/env.enc \
       -out .env
   chmod 600 .env
   ```

5. **Restore data:**
   ```bash
   # Extract full backup
   tar -xzf /path/to/backup/linear-chief-20250115.tar.gz -C ~/
   ```

6. **Install and start service:**
   ```bash
   mkdir -p ~/.config/systemd/user
   cp linear-chief.service ~/.config/systemd/user/

   # Edit paths in service file
   nano ~/.config/systemd/user/linear-chief.service

   systemctl --user daemon-reload
   systemctl --user enable linear-chief.service
   systemctl --user start linear-chief.service
   sudo loginctl enable-linger $USER
   ```

7. **Verify recovery:**
   ```bash
   systemctl --user status linear-chief.service
   python -m linear_chief test
   python -m linear_chief metrics --days=30
   ```

### Data Corruption Recovery

**Database corruption:**

```bash
# 1. Stop service
systemctl --user stop linear-chief.service

# 2. Try to repair
sqlite3 ~/.linear_chief/state.db "PRAGMA integrity_check;"

# 3. If repair fails, restore from backup
mv ~/.linear_chief/state.db ~/.linear_chief/state.db.corrupt
gunzip -c ~/backups/linear-chief/db/state-20250115.db.gz > ~/.linear_chief/state.db

# 4. Restart
systemctl --user start linear-chief.service
```

**ChromaDB corruption:**

```bash
# ChromaDB can be safely deleted and rebuilt
rm -rf ~/.linear_chief/chromadb
systemctl --user restart linear-chief.service
```

## Storage Recommendations

### Local Storage

**Minimum:** 10GB free space
- Application: 500MB
- Data: 500MB
- Backups: 5GB (30 days daily + 90 days weekly)
- Overhead: 4GB

**Recommended:** 50GB free space
- Allows for 6+ months of backups
- Room for log files and temporary data

### Remote Storage

**Options:**

1. **Personal NAS/Server:**
   - Rsync backups every week
   - 10GB allocated
   - Cost: $0 (existing hardware)

2. **Cloud Storage (AWS S3 Glacier):**
   - Monthly full backups
   - 5GB total (6 monthly backups)
   - Cost: ~$0.02/month

3. **Cloud Storage (Google Drive / Dropbox):**
   - Manual uploads or rclone sync
   - 10GB allocated
   - Cost: $0 (free tier)

4. **Git repository (private):**
   - **WARNING:** Never commit `.env` file with API keys
   - Only suitable for database backups (encrypted)
   - Use Git LFS for large files

### Backup Encryption

**Encrypt sensitive backups:**

```bash
# Encrypt backup
openssl enc -aes-256-cbc -salt -pbkdf2 \
    -in linear-chief-20250115.tar.gz \
    -out linear-chief-20250115.tar.gz.enc

# Decrypt backup
openssl enc -aes-256-cbc -d -pbkdf2 \
    -in linear-chief-20250115.tar.gz.enc \
    -out linear-chief-20250115.tar.gz
```

**Use GPG for key-based encryption:**

```bash
# Encrypt with GPG (no password prompt)
gpg --encrypt --recipient your@email.com linear-chief-20250115.tar.gz

# Decrypt
gpg --decrypt linear-chief-20250115.tar.gz.gpg > linear-chief-20250115.tar.gz
```

## Testing Backups

**Monthly backup test procedure:**

```bash
# 1. Create test directory
mkdir -p ~/test-restore
cd ~/test-restore

# 2. Extract latest backup
tar -xzf ~/backups/linear-chief/linear-chief-20250115_120000.tar.gz

# 3. Verify database integrity
sqlite3 .linear_chief/state.db "PRAGMA integrity_check;"

# 4. Check file sizes
du -sh .linear_chief/*

# 5. Verify .env contents (check for required keys)
grep -E "LINEAR_API_KEY|ANTHROPIC_API_KEY|TELEGRAM" linear-agent/.env

# 6. Cleanup
cd ~
rm -rf ~/test-restore

echo "Backup test completed successfully!"
```

**Add to monthly cron:**

```bash
0 5 2 * * /home/yourusername/scripts/test-backup.sh >> /home/yourusername/logs/backup-test.log 2>&1
```

## Backup Checklist

**Before deployment:**

- [ ] Backup strategy selected (minimal or comprehensive)
- [ ] Backup scripts created and tested
- [ ] Backup directory created with sufficient space
- [ ] Automated backup cron jobs configured
- [ ] Backup monitoring set up
- [ ] Test restore performed successfully

**Monthly maintenance:**

- [ ] Verify latest backup exists and is recent
- [ ] Test restore from latest backup
- [ ] Check backup storage space
- [ ] Review and clean up old backups
- [ ] Verify backup automation is working

**After major changes:**

- [ ] Manual backup before update
- [ ] Backup .env if API keys changed
- [ ] Backup service config if modified
- [ ] Test new backup after changes

---

**Last Updated:** 2025-01-15
