# PostgreSQL Backup & Restore Scripts

Scripts to backup and restore PostgreSQL databases from Kubernetes pods.

## Usage

### Backup
```bash
./backup_postgres.sh <namespace> <pod-name>
```

### Restore
```bash
./restore_postgres.sh <namespace> <pod-name> <backup-directory>
```

## Example

```bash
# Backup
./backup_postgres.sh production kfuse-configdb-0

# Restore
./restore_postgres.sh staging kfuse-configdb-0 postgres_backup_20250923_143022
```

## Schema Conflicts

For schema conflicts, uncomment the cleaning lines in `restore_postgres.sh`:
```bash
# Uncomment these lines:
echo "  Cleaning database schema..."
kubectl exec -i -n ${TARGET_NAMESPACE} ${TARGET_POD_NAME} -- bash -c "PGPASSWORD=password psql -U postgres -d $db_name -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
```

## Check Results

```bash
# List databases
kubectl exec -n <namespace> <pod> -- bash -c "PGPASSWORD=password psql -U postgres -l"

# Check table data
kubectl exec -n <namespace> <pod> -- bash -c "PGPASSWORD=password psql -U postgres -d <dbname> -c 'SELECT * FROM <table>;'"
```