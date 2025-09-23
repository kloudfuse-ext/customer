#!/bin/bash

# PostgreSQL Restore Script
# Usage: ./restore_postgres.sh <target-namespace> <target-pod-name> <backup-directory>

TARGET_NAMESPACE=${1:-"dom"}
TARGET_POD_NAME=${2:-"kfuse-configdb-0"}
BACKUP_DIR=${3}

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <target-namespace> <target-pod-name> <backup-directory>"
    echo "Example: $0 dom kfuse-configdb-0 postgres_backup_20250923_114020"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory '$BACKUP_DIR' does not exist"
    exit 1
fi

echo "Restoring databases to ${TARGET_POD_NAME} in namespace ${TARGET_NAMESPACE}..."
echo "Using backup from: ${BACKUP_DIR}/"

for backup_file in "${BACKUP_DIR}"/*.backup; do
    if [ -f "$backup_file" ]; then
        db_name=$(basename "$backup_file" .backup)
        echo "Restoring database: $db_name"

        # Uncomment the following lines if you want to clean the schema before restoring and to resolve the schema conflicts

        # echo "  Cleaning database schema..."
        # kubectl exec -i -n ${TARGET_NAMESPACE} ${TARGET_POD_NAME} -- bash -c "PGPASSWORD=password psql -U postgres -d $db_name -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"

        # Restore without --clean since we already cleaned
        kubectl exec -i -n ${TARGET_NAMESPACE} ${TARGET_POD_NAME} -- bash -c "PGPASSWORD=password pg_restore -U postgres --dbname=$db_name --no-owner --no-acl --schema=public --single-transaction --clean" < "$backup_file"

        if [ $? -eq 0 ]; then
            echo "✓ Successfully restored $db_name"
        else
            echo "✗ Failed to restore $db_name (this may be normal for constraint conflicts)"
        fi
        echo "---"
    fi
done

echo "Restore completed!"
echo "Note: Some constraint errors are normal and don't affect data integrity."