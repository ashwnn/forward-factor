#!/bin/sh

# Ensure backup directory exists
mkdir -p /backup

echo "Starting backup service..."
echo "Target Database: $DB_HOST:$DB_PORT/$DB_NAME"

while true; do
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="/backup/backup_${TIMESTAMP}.sql.gz"

    echo "[$(date)] Creating backup: $BACKUP_FILE"
    
    # Export password for pg_dump
    export PGPASSWORD="$DB_PASSWORD"
    
    # Run pg_dump
    # -h: host, -p: port, -U: user, -d: database
    # Pipe to gzip for compression
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"; then
        echo "[$(date)] Backup successful: $BACKUP_FILE"
    else
        echo "[$(date)] Backup failed!"
        # Remove empty/partial file if it exists
        rm -f "$BACKUP_FILE"
    fi
    
    # Clear password
    unset PGPASSWORD

    # Cleanup old backups (older than 7 days)
    echo "[$(date)] Cleaning up backups older than 7 days..."
    # -mtime +7 means modified more than 7*24 hours ago
    find /backup -name "backup_*.sql.gz" -mtime +7 -delete

    # Calculate time until next run (24 hours)
    echo "[$(date)] Sleeping for 24 hours..."
    sleep 86400
done
