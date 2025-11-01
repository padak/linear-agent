#!/bin/bash
# Restore script for Linear Chief of Staff
# Restores from full backup archive

set -e  # Exit on error

# Check if backup file provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lht ~/backups/linear-chief/linear-chief-*.tar.gz 2>/dev/null | head -5 || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting restore from: $BACKUP_FILE"
echo ""
read -p "This will overwrite current data. Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Stop service
echo "Stopping service..."
systemctl --user stop linear-chief.service || true

# Backup current state
if [ -d ~/.linear_chief ]; then
    BACKUP_OLD=~/.linear_chief.backup-$(date +%Y%m%d_%H%M%S)
    echo "Backing up current state to: $BACKUP_OLD"
    mv ~/.linear_chief "$BACKUP_OLD"
fi

if [ -f ~/linear-agent/.env ]; then
    echo "Backing up current .env to: ~/linear-agent/.env.backup"
    cp ~/linear-agent/.env ~/linear-agent/.env.backup
fi

# Extract backup
echo "Extracting backup..."
tar -xzf "$BACKUP_FILE" -C ~/

# Verify extraction
if [ ! -d ~/.linear_chief ]; then
    echo "✗ Extraction failed: ~/.linear_chief not found"
    echo "Restoring from backup..."
    [ -d "$BACKUP_OLD" ] && mv "$BACKUP_OLD" ~/.linear_chief
    exit 1
fi

# Fix permissions
echo "Setting permissions..."
chmod 600 ~/linear-agent/.env 2>/dev/null || true
chmod -R 700 ~/.linear_chief

# Verify database integrity
echo "Verifying database integrity..."
if sqlite3 ~/.linear_chief/state.db "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "✓ Database integrity check passed"
else
    echo "✗ Database integrity check failed!"
    exit 1
fi

# Restart service
echo "Restarting service..."
systemctl --user start linear-chief.service

# Wait for service to start
sleep 2

# Verify service status
if systemctl --user is-active --quiet linear-chief.service; then
    echo "✓ Service started successfully"
else
    echo "✗ Service failed to start"
    systemctl --user status linear-chief.service
    exit 1
fi

echo ""
echo "✓ Restore completed successfully!"
echo ""
echo "You can verify the restore with:"
echo "  python -m linear_chief test"
echo "  python -m linear_chief metrics --days=7"
echo ""
echo "Old data backed up to: $BACKUP_OLD"
