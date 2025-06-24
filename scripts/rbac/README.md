# RBAC User Management Scripts

Two scripts to fix user management issues in the RBAC system.

## Scripts

### 1. fix_users_auto.sh
**Purpose**: Fixes duplicate users where email equals login (Okta UID format)

**What it does**:
- Finds users with email = login (like `00u1234567890`)
- Transfers group memberships to the user with proper email
- Deletes the problematic user from both Grafana and RBAC database
- Keeps the user with the correct email address

**Usage**:
```bash
./fix_users_auto.sh [namespace]
./fix_users_auto.sh suryadev
```

### 2. fix_case_sensitive_users.sh
**Purpose**: Fixes case-sensitive email duplicates by keeping lowercase version

**What it does**:
- Finds users with duplicate emails that differ only in case (e.g., `john.doe@company.com` vs `John.Doe@company.com`)
- Keeps the lowercase email version
- Transfers all group memberships from mixed-case users to the lowercase user
- Deletes mixed-case users from both Grafana and RBAC database

**Usage**:
```bash
./fix_case_sensitive_users.sh [namespace]
./fix_case_sensitive_users.sh suryadev
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

## Requirements

- `kubectl` access to the cluster
- Access to the namespace containing `kfuse-configdb-0` pod
- Grafana admin credentials (for fix_users_auto.sh)

## Safety

Both scripts:
- Show what they will do before making changes
- Provide detailed output of all operations
- Include safety checks to prevent accidental deletions
- Can be run multiple times safely (idempotent)

## Order of Operations

1. Run `fix_users_auto.sh` first to fix duplicate users with email=login pattern
2. Run `fix_case_sensitive_users.sh` to fix case-sensitive email duplicates  
3. Run `clean_orphaned_users.sh` to clean up any remaining orphaned users
4. Restart user-mgmt-service to refresh user cache

## Post-Processing

After running any of the scripts, restart the user management service to ensure changes are reflected:

```bash
kubectl rollout restart deployment user-mgmt-service -n [namespace]
kubectl rollout restart deployment user-mgmt-service -n suryadev
```