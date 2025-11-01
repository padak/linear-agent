# Backup and Maintenance Scripts

This directory contains utility scripts for backing up and maintaining Linear Chief of Staff.

## Scripts Overview

### Backup Scripts

#### `backup-linear-chief.sh`
**Full backup of all data and configuration**

- Stops service temporarily for consistency
- Creates compressed tar archive of:
  - `~/.linear_chief/` (all data)
  - `~/linear-agent/.env` (configuration)
  - `~/.config/systemd/user/linear-chief.service` (service config)
- Automatically removes backups older than 30 days
- Recommended frequency: Weekly

**Usage:**
```bash
./backup-linear-chief.sh
```

**Output:**
```
Backups saved to: ~/backups/linear-chief/linear-chief-YYYYMMDD_HHMMSS.tar.gz
```

---

#### `backup-database-only.sh`
**Fast database-only backup (safe while service is running)**

- Uses SQLite backup command (safe with concurrent access)
- No service interruption required
- Compresses backup with gzip
- Keeps last 30 daily backups
- Recommended frequency: Daily

**Usage:**
```bash
./backup-database-only.sh
```

**Output:**
```
Backups saved to: ~/backups/linear-chief/db/state-YYYYMMDD.db.gz
```

---

### Restore Scripts

#### `restore-from-backup.sh`
**Restore from full backup archive**

- Interactive script with confirmation prompt
- Backs up current state before restoring
- Verifies database integrity after restore
- Restarts service automatically
- Sets correct file permissions

**Usage:**
```bash
# List available backups
./restore-from-backup.sh

# Restore from specific backup
./restore-from-backup.sh ~/backups/linear-chief/linear-chief-20250115_120000.tar.gz
```

**Safety features:**
- Requires explicit "yes" confirmation
- Creates backup of current state before restoring
- Verifies database integrity
- Rolls back on failure

---

### Monitoring Scripts

#### `check-backups.sh`
**Monitor backup health and freshness**

- Checks for recent full backups (< 8 days old)
- Checks for recent database backups (< 25 hours old)
- Reports disk space usage
- Exit code 0 = all OK, 1 = warnings found

**Usage:**
```bash
./check-backups.sh
```

**Example output:**
```
=== Full Backups ===
✓ Latest full backup is 3 days old
  File: ~/backups/linear-chief/linear-chief-20250112_030000.tar.gz

=== Database Backups ===
✓ Latest database backup is 8 hours old
  File: ~/backups/linear-chief/db/state-20250115.db.gz

=== Disk Space ===
Total backup size: 245M
Available space: 15G

✓ All backup checks passed
```

**Recommended:** Add to daily cron for automated monitoring

---

## Automation Setup

### Daily Database Backup (Recommended)

Add to crontab:
```bash
crontab -e

# Add line (runs at 2 AM daily):
0 2 * * * /home/yourusername/linear-agent/scripts/backup-database-only.sh >> ~/logs/backup.log 2>&1
```

### Weekly Full Backup (Recommended)

Add to crontab:
```bash
# Add line (runs at 3 AM every Sunday):
0 3 * * 0 /home/yourusername/linear-agent/scripts/backup-linear-chief.sh >> ~/logs/backup.log 2>&1
```

### Daily Backup Monitoring (Optional)

Add to crontab:
```bash
# Add line (runs at noon daily):
0 12 * * * /home/yourusername/linear-agent/scripts/check-backups.sh >> ~/logs/backup-check.log 2>&1
```

### Systemd Timer Alternative

For more control, use systemd timers instead of cron. See [docs/deployment.md](../docs/deployment.md) for examples.

---

## Manual Backup Examples

### Before System Update
```bash
# Create full backup before updating
./backup-linear-chief.sh

# Update system
sudo apt update && sudo apt upgrade

# Verify service still works
systemctl --user status linear-chief.service
```

### Before Configuration Changes
```bash
# Backup current state
./backup-database-only.sh

# Make changes to .env
nano ~/linear-agent/.env

# Test changes
python -m linear_chief test

# If something goes wrong, restore
./restore-from-backup.sh ~/backups/linear-chief/db/state-YYYYMMDD.db.gz
```

### Monthly Full Backup
```bash
# Create monthly archive
./backup-linear-chief.sh

# Copy to external storage
cp ~/backups/linear-chief/linear-chief-$(date +%Y%m%d)*.tar.gz /mnt/external/
```

---

## Backup Storage Locations

**Default backup directory:** `~/backups/linear-chief/`

```
~/backups/linear-chief/
├── linear-chief-20250115_120000.tar.gz  # Full backup
├── linear-chief-20250108_030000.tar.gz  # Full backup (last week)
└── db/
    ├── state-20250115.db.gz              # Daily database backup
    ├── state-20250114.db.gz              # Daily database backup
    └── ...
```

**Recommended storage:**
- Local: 5-10GB for 30 days of backups
- Remote: Copy monthly backups to external drive or cloud storage

---

## Troubleshooting

### Script Permission Denied
```bash
# Make scripts executable
chmod +x ~/linear-agent/scripts/*.sh
```

### Backup Directory Doesn't Exist
```bash
# Create backup directory
mkdir -p ~/backups/linear-chief/db
```

### Service Not Found (User Service)
```bash
# Verify service file location
ls -la ~/.config/systemd/user/linear-chief.service

# If using system service instead:
# Edit scripts to use: sudo systemctl start linear-chief@username.service
```

### Database Backup Fails
```bash
# Verify database exists
ls -la ~/.linear_chief/state.db

# Check SQLite installation
which sqlite3
```

### Restore Fails
```bash
# Check backup file integrity
tar -tzf ~/backups/linear-chief/linear-chief-20250115.tar.gz

# If corrupted, try previous backup
ls -lt ~/backups/linear-chief/ | head
```

---

## Security Notes

- Backup files contain **sensitive API keys** in `.env`
- Store backups in secure location with restricted permissions
- Consider encrypting backups before uploading to cloud storage
- Never commit backup files to git repositories

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

---

## Additional Resources

- [Deployment Guide](../docs/deployment.md)
- [Backup Strategy](../docs/backup-strategy.md)
- [Project README](../README.md)

---

**Last Updated:** 2025-01-15
