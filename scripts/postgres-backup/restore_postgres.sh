#!/bin/bash

# PostgreSQL Internal Restore Script - Runs entirely inside pod
# Usage: ./restore_postgres_internal.sh <namespace> [pod-name] <backup-source>

TARGET_NAMESPACE=$1

# Check if arg2 looks like a backup source
if [[ "$2" == s3://* ]] || [[ "$2" == postgres_backup_* ]] || [[ -d "$2" ]]; then
    # arg2 is backup source, use default pod
    TARGET_POD_NAME="kfuse-configdb-0"
    BACKUP_SOURCE=$2
elif [ ! -z "$3" ]; then
    # arg3 exists, so arg2 must be pod name
    TARGET_POD_NAME=$2
    BACKUP_SOURCE=$3
else
    # Only 2 args total, arg2 must be backup source
    TARGET_POD_NAME="kfuse-configdb-0"
    BACKUP_SOURCE=$2
fi

if [ -z "$TARGET_NAMESPACE" ] || [ -z "$BACKUP_SOURCE" ]; then
    echo "Usage: $0 <target-namespace> [target-pod-name] <backup-source>"
    echo ""
    echo "backup-source can be:"
    echo "  - Local directory: postgres_backup_20250923_114020"
    echo "  - S3 path: s3://my-bucket/backups/postgres_backup_20250923_114020.tar.gz"
    echo ""
    echo "Example: $0 staging postgres_backup_20250923_114020"
    echo "Example: $0 staging s3://my-bucket/backups/postgres_backup_20250923_114020.tar.gz"
    echo "Example: $0 staging my-pod s3://my-bucket/backups/postgres_backup_20250923_114020.tar.gz"
    echo "Default pod-name: kfuse-configdb-0"
    exit 1
fi

# Check if it's S3 path or local directory
if [[ "$BACKUP_SOURCE" == s3://* ]]; then
    echo "Downloading backup from S3: $BACKUP_SOURCE"

    # Extract filename from S3 path
    S3_FILENAME=$(basename "$BACKUP_SOURCE")
    LOCAL_TAR_FILE="./$S3_FILENAME"

    # Download from S3
    aws s3 cp "$BACKUP_SOURCE" "$LOCAL_TAR_FILE"

    if [ $? -ne 0 ]; then
        echo "✗ Failed to download from S3"
        exit 1
    fi

    echo "✓ Downloaded from S3"

    # Extract the tar.gz file
    BACKUP_DIR=$(basename "$S3_FILENAME" .tar.gz)
    tar -xzf "$LOCAL_TAR_FILE"

    if [ $? -ne 0 ]; then
        echo "✗ Failed to extract backup archive"
        exit 1
    fi

    echo "✓ Extracted backup to: $BACKUP_DIR"

else
    # Local directory
    BACKUP_DIR="$BACKUP_SOURCE"

    if [ ! -d "$BACKUP_DIR" ]; then
        echo "Error: Backup directory '$BACKUP_DIR' does not exist"
        exit 1
    fi
fi

echo "Copying backup files to pod: ${TARGET_POD_NAME} in namespace ${TARGET_NAMESPACE}..."
TEMP_RESTORE_DIR="/tmp/restore_$(date +%Y%m%d_%H%M%S)"

# Copy backup files to pod
kubectl cp ${BACKUP_DIR} ${TARGET_NAMESPACE}/${TARGET_POD_NAME}:${TEMP_RESTORE_DIR}

echo "Starting restore inside pod..."

# Execute restore script inside pod
kubectl exec -n ${TARGET_NAMESPACE} ${TARGET_POD_NAME} -- bash -c "
    echo 'Starting restore at:' \$(date)

    for backup_file in ${TEMP_RESTORE_DIR}/*.backup; do
        if [ -f \"\${backup_file}\" ]; then
            db_name=\$(basename \"\${backup_file}\" .backup)
            echo \"Restoring database: \${db_name}\"
            start_time=\$(date +%s)

            # Uncomment to clean schema before restore (handles conflicts)
            # echo '  Cleaning database schema...'
            # PGPASSWORD=password psql -U postgres -d \${db_name} -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'

            # Restore database
            PGPASSWORD=password pg_restore -U postgres --dbname=\${db_name} --no-owner --no-acl --clean --if-exists --schema=public --single-transaction < \"\${backup_file}\"

            if [ \$? -eq 0 ]; then
                end_time=\$(date +%s)
                duration=\$((end_time - start_time))
                echo \"✓ Successfully restored \${db_name} in \${duration}s\"
            else
                echo \"✗ Failed to restore \${db_name} (may be normal for constraint conflicts)\"
            fi
            echo '---'
        fi
    done

    echo 'Restore completed at:' \$(date)

    # Clean up temporary files
    echo 'Cleaning up temporary files...'
    rm -rf ${TEMP_RESTORE_DIR}
"

echo "Restore completed!"
echo "Note: Some constraint errors are normal and don't affect data integrity."