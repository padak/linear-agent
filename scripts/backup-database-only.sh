#!/bin/bash
# Database-only backup script for Linear Chief of Staff
# Fast daily backup using SQLite backup command (safe while running)

set -e  # Exit on error

BACKUP_DIR=~/backups/linear-chief/db
TIMESTAMP=$(date +%Y%m%d)
BACKUP_FILE="state-${TIMESTAMP}.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Starting database backup..."

# Check if database exists
if [ ! -f ~/.linear_chief/state.db ]; then
    echo "✗ Database not found: ~/.linear_chief/state.db"
    exit 1
fi

# Copy database using SQLite backup command (safe while running)
echo "Backing up database..."
sqlite3 ~/.linear_chief/state.db ".backup '${BACKUP_DIR}/${BACKUP_FILE}'"

# Verify backup
if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "✗ Database backup failed!"
    exit 1
fi

# Compress
echo "Compressing backup..."
gzip -f "${BACKUP_DIR}/${BACKUP_FILE}"

# Verify compressed backup
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}.gz" ]; then
    echo "✓ Database backup created: ${BACKUP_DIR}/${BACKUP_FILE}.gz"
    ls -lh "${BACKUP_DIR}/${BACKUP_FILE}.gz"

    # Calculate size
    SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
    echo "  Backup size: ${SIZE}"
else
    echo "✗ Compression failed!"
    exit 1
fi

# Optional: Keep only last 30 daily backups
echo "Cleaning up old backups (>30 days)..."
DELETED=$(find "$BACKUP_DIR" -name "state-*.db.gz" -mtime +30 -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "  Deleted $DELETED old backup(s)"
else
    echo "  No old backups to delete"
fi

echo "✓ Database backup completed successfully"
