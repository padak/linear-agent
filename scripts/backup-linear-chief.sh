#!/bin/bash
# Full backup script for Linear Chief of Staff
# Creates compressed tar archive of all data and configuration

set -e  # Exit on error

BACKUP_DIR=~/backups/linear-chief
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="linear-chief-${TIMESTAMP}.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Starting full backup..."

# Stop service for consistent backup
echo "Stopping service..."
systemctl --user stop linear-chief.service

# Create compressed archive
echo "Creating backup archive..."
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    -C ~ \
    .linear_chief/ \
    linear-agent/.env \
    .config/systemd/user/linear-chief.service \
    2>/dev/null || true

# Restart service
echo "Restarting service..."
systemctl --user start linear-chief.service

# Verify backup
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "✓ Backup created successfully: ${BACKUP_DIR}/${BACKUP_FILE}"
    ls -lh "${BACKUP_DIR}/${BACKUP_FILE}"

    # Calculate size
    SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo "  Backup size: ${SIZE}"
else
    echo "✗ Backup failed!"
    exit 1
fi

# Optional: Remove backups older than 30 days
echo "Cleaning up old backups (>30 days)..."
DELETED=$(find "$BACKUP_DIR" -name "linear-chief-*.tar.gz" -mtime +30 -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "  Deleted $DELETED old backup(s)"
else
    echo "  No old backups to delete"
fi

echo "✓ Backup completed successfully"
