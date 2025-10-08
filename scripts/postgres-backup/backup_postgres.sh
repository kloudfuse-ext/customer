#!/bin/bash

# PostgreSQL Internal Backup Script - Runs entirely inside pod
# Usage: ./backup_postgres_internal.sh <namespace> [pod-name] [s3-path]

NAMESPACE=$1

# Check if arg2 is S3 path
if [[ "$2" == s3://* ]]; then
    POD_NAME="kfuse-configdb-0"
    S3_PATH=$2
# Check if arg3 is S3 path
elif [[ "$3" == s3://* ]]; then
    POD_NAME=$2
    S3_PATH=$3
# No S3 path provided
else
    POD_NAME=${2:-"kfuse-configdb-0"}
    S3_PATH=""
fi

if [ -z "$NAMESPACE" ]; then
    echo "Usage: $0 <namespace> [pod-name] [s3-path]"
    echo "Example: $0 production"
    echo "Example: $0 production s3://my-bucket/backups/"
    echo "Example: $0 production kfuse-configdb-0 s3://my-bucket/backups/"
    echo "Default pod-name: kfuse-configdb-0"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="postgres_backup_${TIMESTAMP}"

echo "Creating backup inside pod: ${POD_NAME} in namespace ${NAMESPACE}..."

# Create and execute backup script inside pod
kubectl exec -n ${NAMESPACE} ${POD_NAME} -- bash -c "
    BACKUP_DIR='/tmp/${BACKUP_DIR}'
    mkdir -p \"\${BACKUP_DIR}\"
    echo 'Starting backup at:' \$(date)

    # Get list of databases
    DATABASES=\$(PGPASSWORD=password psql -U postgres -t -c \"SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';\" | tr -d ' ')

    for db in \${DATABASES}; do
        if [ ! -z \"\${db}\" ]; then
            echo \"Backing up database: \${db}\"
            start_time=\$(date +%s)
            # Add exclusions for alertsdb
            if [ \"\${db}\" = \"alertsdb\" ]; then
                echo \"  Excluding tables: public.annotation, public.alert_instance\"
                PGPASSWORD=password pg_dump -U postgres -d \${db} -Fc --exclude-table=public.annotation --exclude-table=public.alert_instance > \"\${BACKUP_DIR}/\${db}.backup\"
            else
                PGPASSWORD=password pg_dump -U postgres -d \${db} -Fc > \"\${BACKUP_DIR}/\${db}.backup\"
            fi
            end_time=\$(date +%s)
            duration=\$((end_time - start_time))
            size=\$(ls -lh \"\${BACKUP_DIR}/\${db}.backup\" | awk '{print \$5}')
            echo \"✓ Backed up \${db} in \${duration}s (Size: \${size})\"
        fi
    done

    echo 'Backup completed at:' \$(date)
    echo 'Files created:'
    ls -lh \"\${BACKUP_DIR}/\"
"

echo ""
echo "Copying backup files from pod to local machine..."
kubectl cp ${NAMESPACE}/${POD_NAME}:/tmp/${BACKUP_DIR} ./${BACKUP_DIR}

echo "Backup completed! Files saved in: ${BACKUP_DIR}/"
ls -la "${BACKUP_DIR}/"

# Upload to S3 if path provided
if [ ! -z "$S3_PATH" ]; then
    echo ""
    echo "Uploading backup to S3: ${S3_PATH}${BACKUP_DIR}/"

    # Create tar.gz for efficient upload
    tar -czf "${BACKUP_DIR}.tar.gz" "${BACKUP_DIR}"/

    # Upload to S3
    aws s3 cp "${BACKUP_DIR}.tar.gz" "${S3_PATH}${BACKUP_DIR}.tar.gz"

    if [ $? -eq 0 ]; then
        echo "✓ Successfully uploaded to S3: ${S3_PATH}${BACKUP_DIR}.tar.gz"

        # Optionally remove local files after successful upload
        read -p "Remove local backup files? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "${BACKUP_DIR}" "${BACKUP_DIR}.tar.gz"
            echo "Local backup files removed"
        fi
    else
        echo "✗ Failed to upload to S3"
    fi
else
    echo "No S3 path provided, backup saved locally only"
fi

# Clean up pod temporary files
echo "Cleaning up temporary files in pod..."
kubectl exec -n ${NAMESPACE} ${POD_NAME} -- rm -rf /tmp/${BACKUP_DIR}