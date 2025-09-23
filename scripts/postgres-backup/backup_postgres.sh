#!/bin/bash

# PostgreSQL Backup Script
# Usage: ./backup_postgres.sh <namespace> <pod-name>

NAMESPACE=$1
POD_NAME=${2:-"kfuse-configdb-0"}

if [ -z "$NAMESPACE" ]; then
    echo "Usage: $0 <namespace> [pod-name]"
    echo "Example: $0 production"
    echo "Default pod-name: kfuse-configdb-0"
    exit 1
fi
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="postgres_backup_${TIMESTAMP}"

echo "Creating backup directory: ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"

echo "Backing up all databases from ${POD_NAME} in namespace ${NAMESPACE}..."

# Get list of databases (excluding templates and postgres)
DATABASES=$(kubectl exec -n ${NAMESPACE} ${POD_NAME} -- bash -c "PGPASSWORD=password psql -U postgres -t -c \"SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';\"" | tr -d ' ')

for db in $DATABASES; do
    if [ ! -z "$db" ]; then
        echo "Backing up database: $db"
        kubectl exec -n ${NAMESPACE} ${POD_NAME} -- bash -c "PGPASSWORD=password pg_dump -U postgres -d $db -Fc" > "${BACKUP_DIR}/${db}.backup"

        if [ $? -eq 0 ]; then
            echo "✓ Successfully backed up $db"
        else
            echo "✗ Failed to backup $db"
        fi
    fi
done

echo "Backup completed! Files saved in: ${BACKUP_DIR}/"
ls -la "${BACKUP_DIR}/"