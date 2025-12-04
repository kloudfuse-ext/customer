# RBAC User Management Scripts

Collection of scripts to manage and fix user issues in the RBAC system.

## Backup Scripts

### dump_rbac_tables.sh / dump_rbac_tables_with_conflicts.sh
**Purpose**: Backup RBAC database tables (users, groups, group_members)

**What it does**:
- Creates timestamped SQL dump of RBAC tables
- Shows summary statistics
- Two versions available:
  - `dump_rbac_tables.sh`: Standard dump with optional `--with-truncate` flag
  - `dump_rbac_tables_with_conflicts.sh`: Uses ON CONFLICT DO NOTHING for safe restoration

**Usage**:
```bash
# Standard dump
./dump_rbac_tables.sh [namespace] [output_dir]
./dump_rbac_tables.sh suryadev /tmp/backups

# Dump with truncate statements (for full replacement)
./dump_rbac_tables.sh suryadev /tmp/backups --with-truncate

# Conflict-safe dump (skips existing records on restore)
./dump_rbac_tables_with_conflicts.sh suryadev /tmp/backups

# Restore from dump
kubectl exec -i kfuse-configdb-0 -n suryadev -- sh -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -U postgres -d rbacdb' < /tmp/backups/rbac_dump_suryadev_[timestamp].sql
```

## Fix Scripts

### 1. fix_users_auto_with_dryrun.sh
**Purpose**: Fixes duplicate users where email equals login (Okta UID format)

**What it does**:
- Finds users with email = login (like `550015251@hc.ge.com`)
- Transfers group memberships to the user with proper email
- Deletes the problematic user from both Grafana and RBAC database
- Keeps the user with the correct email address

**Usage**:
```bash
# Run with changes
./fix_users_auto_with_dryrun.sh [namespace]

# Dry run mode (preview changes)
./fix_users_auto_with_dryrun.sh --dry-run [namespace]
./fix_users_auto_with_dryrun.sh --dry-run suryadev
```

### 2. fix_case_sensitive_users_with_dryrun.sh
**Purpose**: Fixes case-sensitive email duplicates by keeping lowercase version

**What it does**:
- Finds users with duplicate emails that differ only in case (e.g., `john.doe@company.com` vs `John.Doe@company.com`)
- Keeps the lowercase email version
- Transfers all group memberships from mixed-case users to the lowercase user
- Deletes mixed-case users from both Grafana and RBAC database

**Usage**:
```bash
# Run with changes
./fix_case_sensitive_users_with_dryrun.sh [namespace]

# Dry run mode (preview changes)
./fix_case_sensitive_users_with_dryrun.sh --dry-run [namespace]
./fix_case_sensitive_users_with_dryrun.sh --dry-run suryadev
```

### 3. clean_orphaned_users.sh
**Purpose**: Removes orphaned users with no group memberships

**What it does**:
- Finds users where email = login AND user has no group memberships
- Safely deletes these unused users from RBAC database
- Only removes users that have zero group associations

**Usage**:
```bash
./clean_orphaned_users.sh [namespace]
./clean_orphaned_users.sh suryadev
```

## Test Scripts

### create_test_users_for_fix_auto.sql
Creates test users to validate fix_users_auto.sh functionality

### create_test_case_sensitive_users.sh
Creates test users with case-sensitive email duplicates to test fix_case_sensitive_users.sh

### cleanup_and_recreate_test_users.sql
Cleans up and recreates test users for fix_users_auto.sh testing

## Requirements

- `kubectl` access to the cluster
- Access to the namespace containing `kfuse-configdb-0` pod
- Grafana admin credentials (for scripts that interact with Grafana)

## Safety Features

All scripts include:
- **Dry run mode** (where available) to preview changes before execution
- Detailed output of all operations
- Safety checks to prevent accidental deletions
- Idempotent operations (can be run multiple times safely)
- Transaction support (changes are atomic)

## Recommended Workflow

1. **Backup current data**:
   ```bash
   ./dump_rbac_tables_with_conflicts.sh suryadev /tmp/backups
   ```

2. **Run fixes with dry-run first**:
   ```bash
   ./fix_users_auto_with_dryrun.sh --dry-run suryadev
   ./fix_case_sensitive_users_with_dryrun.sh --dry-run suryadev
   ```

3. **Apply fixes**:
   ```bash
   ./fix_users_auto_with_dryrun.sh suryadev
   ./fix_case_sensitive_users_with_dryrun.sh suryadev
   ./clean_orphaned_users.sh suryadev
   ```

4. **Restart services**:
   ```bash
   kubectl rollout restart deployment user-mgmt-service -n suryadev
   ```

## Post-Processing

After running any of the scripts, restart the user management service to ensure changes are reflected:

```bash
kubectl rollout restart deployment user-mgmt-service -n [namespace]
```

## Troubleshooting

- If a script doesn't process all users in one run, run it again (some edge cases may require multiple passes)
- Check the Grafana logs if user deletion from Grafana fails
- Use the dump scripts to create backups before making any changes
- Review dry-run output carefully before applying changes