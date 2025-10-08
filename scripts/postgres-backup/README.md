# PostgreSQL Backup & Restore Scripts

Scripts to backup and restore PostgreSQL databases from Kubernetes pods with S3 integration.

## Scripts

- `backup_postgres.sh` - Runs inside pod, supports S3 upload
- `restore_postgres.sh` - Supports S3 download and restore

## Usage

### Backup (with optional S3 upload)
### Backup (with optional S3 upload)
```bash
# Local backup only
./backup_postgres.sh <namespace> [pod-name]

# Backup and upload to S3
./backup_postgres.sh <namespace> [pod-name] [s3-path]
./backup_postgres.sh <namespace> [s3-path]  # Uses default pod
```

### Restore (from local or S3)
### Restore (from local or S3)
```bash
# Restore from local directory
./restore_postgres.sh <namespace> [pod-name] <backup-directory>
./restore_postgres.sh <namespace> <backup-directory>  # Uses default pod

# Restore from S3
./restore_postgres.sh <namespace> [pod-name] <s3-path>
./restore_postgres.sh <namespace> <s3-path>  # Uses default pod
```

## Examples
## Examples

```bash
# Backup locally
./backup_postgres.sh production

# Backup and upload to S3
./backup_postgres.sh production s3://my-bucket/backups/

# Restore from local backup
./restore_postgres.sh staging postgres_backup_20250923_143022

# Restore from S3
./restore_postgres.sh staging s3://my-bucket/backups/postgres_backup_20250923_143022.tar.gz

# Custom pod name with S3
./backup_postgres.sh production my-configdb-0 s3://my-bucket/backups/
./restore_postgres.sh staging my-configdb-0 s3://my-bucket/backups/postgres_backup_20250923_143022.tar.gz
```

## AWS Authentication

For S3 operations, ensure AWS CLI is configured:
```bash
aws configure
# OR set environment variables:
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-west-2"
```

## Features

- **Automatic table exclusion**: `alertsdb` backup excludes `public.annotation` and `public.alert_instance` tables
- **S3 integration**: Seamless upload/download from S3
- **Fast operation**: Runs inside pod to avoid kubectl streaming bottleneck
- **Default pod name**: `kfuse-configdb-0` (can be overridden)

## AWS Authentication

For S3 operations, ensure AWS CLI is configured:
```bash
aws configure
# OR set environment variables:
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-west-2"
```

## Features

- **Automatic table exclusion**: `alertsdb` backup excludes `public.annotation` and `public.alert_instance` tables
- **S3 integration**: Seamless upload/download from S3
- **Fast operation**: Runs inside pod to avoid kubectl streaming bottleneck
- **Default pod name**: `kfuse-configdb-0` (can be overridden)

## Schema Conflicts

For schema conflicts during restore, uncomment the cleaning lines in `restore_postgres.sh`:
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