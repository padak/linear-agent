#!/bin/bash
# Backup monitoring script for Linear Chief of Staff
# Verifies that recent backups exist and are not too old

set -e  # Exit on error

BACKUP_DIR=~/backups/linear-chief
EXIT_CODE=0

echo "Checking backup status..."
echo ""

# Check full backups
echo "=== Full Backups ==="
LATEST_FULL=$(ls -t "$BACKUP_DIR"/linear-chief-*.tar.gz 2>/dev/null | head -1)

if [ -z "$LATEST_FULL" ]; then
    echo "✗ ERROR: No full backups found!"
    EXIT_CODE=1
else
    # Check if backup is less than 8 days old (weekly + 1 day grace)
    BACKUP_AGE=$(( $(date +%s) - $(stat -f %m "$LATEST_FULL" 2>/dev/null || stat -c %Y "$LATEST_FULL") ))
    BACKUP_HOURS=$(( BACKUP_AGE / 3600 ))
    BACKUP_DAYS=$(( BACKUP_HOURS / 24 ))

    if [ $BACKUP_AGE -gt 691200 ]; then  # 8 days in seconds
        echo "✗ WARNING: Latest full backup is $BACKUP_DAYS days old!"
        echo "  File: $LATEST_FULL"
        EXIT_CODE=1
    else
        echo "✓ Latest full backup is $BACKUP_DAYS days old"
        echo "  File: $LATEST_FULL"
        ls -lh "$LATEST_FULL"
    fi
fi

echo ""

# Check database backups
echo "=== Database Backups ==="
LATEST_DB=$(ls -t "$BACKUP_DIR"/db/state-*.db.gz 2>/dev/null | head -1)

if [ -z "$LATEST_DB" ]; then
    echo "✗ ERROR: No database backups found!"
    EXIT_CODE=1
else
    # Check if backup is less than 25 hours old (daily + 1 hour grace)
    BACKUP_AGE=$(( $(date +%s) - $(stat -f %m "$LATEST_DB" 2>/dev/null || stat -c %Y "$LATEST_DB") ))
    BACKUP_HOURS=$(( BACKUP_AGE / 3600 ))

    if [ $BACKUP_AGE -gt 90000 ]; then  # 25 hours in seconds
        echo "✗ WARNING: Latest database backup is $BACKUP_HOURS hours old!"
        echo "  File: $LATEST_DB"
        EXIT_CODE=1
    else
        echo "✓ Latest database backup is $BACKUP_HOURS hours old"
        echo "  File: $LATEST_DB"
        ls -lh "$LATEST_DB"
    fi
fi

echo ""

# Check disk space
echo "=== Disk Space ==="
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
echo "Total backup size: $BACKUP_SIZE"

AVAILABLE_SPACE=$(df -h "$BACKUP_DIR" | tail -1 | awk '{print $4}')
echo "Available space: $AVAILABLE_SPACE"

echo ""

# Summary
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All backup checks passed"
else
    echo "✗ Backup checks failed - please review warnings above"
fi

exit $EXIT_CODE
