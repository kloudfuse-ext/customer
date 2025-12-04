#!/bin/bash

# Script to dump users, groups, and group_members tables with ON CONFLICT handling
# Usage: ./dump_rbac_tables_with_conflicts.sh [namespace] [output_dir]

POD_NAME="kfuse-configdb-0"
DB_NAME="rbacdb"
DB_USER="postgres"
NAMESPACE="${1:-default}"
OUTPUT_DIR="${2:-.}"

# Create timestamp for filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="$OUTPUT_DIR/rbac_dump_conflict_safe_${NAMESPACE}_${TIMESTAMP}.sql"

echo "Dumping RBAC tables from namespace: $NAMESPACE"
echo "Output file: $DUMP_FILE"
echo "Note: This dump uses ON CONFLICT DO NOTHING to handle existing records"
echo ""

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Create the dump with ON CONFLICT handling
cat > "$DUMP_FILE" << EOF
-- RBAC Database Dump (Conflict-Safe Version)
-- Namespace: $NAMESPACE
-- Date: $(date)
-- Tables: users, groups, group_members
-- This dump uses ON CONFLICT DO NOTHING to skip existing records
--
-- To restore: kubectl exec -i $POD_NAME -n $NAMESPACE -- sh -c 'PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME' < $DUMP_FILE

BEGIN;

-- Groups data
EOF

echo "Dumping groups table..."
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
SELECT 'INSERT INTO groups (id, name, email, team_id) VALUES (' || 
       COALESCE('''' || REPLACE(id, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(name, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(email, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE(team_id::text, 'NULL') || 
       ') ON CONFLICT (id) DO NOTHING;'
FROM groups
ORDER BY name;\"" >> "$DUMP_FILE"

echo "" >> "$DUMP_FILE"
echo "-- Users data" >> "$DUMP_FILE"

echo "Dumping users table..."
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
SELECT 'INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id) VALUES (' || 
       COALESCE('''' || REPLACE(id, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(email, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(name, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(role, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(login, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE(grafana_id::text, 'NULL') || ', ' ||
       COALESCE(grafana_org_id::text, 'NULL') ||
       ') ON CONFLICT (id) DO NOTHING;'
FROM users
ORDER BY email;\"" >> "$DUMP_FILE"

echo "" >> "$DUMP_FILE"
echo "-- Group members data" >> "$DUMP_FILE"

echo "Dumping group_members table..."
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
SELECT 'INSERT INTO group_members (group_id, user_id, permission) VALUES (' || 
       COALESCE('''' || REPLACE(group_id, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(user_id, '''', '''''') || '''', 'NULL') || ', ' ||
       COALESCE('''' || REPLACE(permission, '''', '''''') || '''', 'NULL') || 
       ') ON CONFLICT (group_id, user_id) DO NOTHING;'
FROM group_members
ORDER BY group_id, user_id;\"" >> "$DUMP_FILE"

echo "" >> "$DUMP_FILE"
echo "COMMIT;" >> "$DUMP_FILE"

echo ""
echo "Generating summary..."
echo ""

# Show summary
USER_COUNT=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM users;\"" | xargs)
GROUP_COUNT=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM groups;\"" | xargs)
MEMBER_COUNT=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM group_members;\"" | xargs)

echo "Database Summary:"
echo "-----------------"
echo "Users: $USER_COUNT"
echo "Groups: $GROUP_COUNT"
echo "Group memberships: $MEMBER_COUNT"
echo ""
echo "Dump completed successfully!"
echo "Output file: $DUMP_FILE"
echo "File size: $(ls -lh "$DUMP_FILE" | awk '{print $5}')"
echo ""
echo "This dump uses ON CONFLICT DO NOTHING, so it will:"
echo "- Skip any records that already exist"
echo "- Only insert new records"
echo "- Not fail on duplicate key errors"
echo ""
echo "To restore this dump:"
echo "kubectl exec -i $POD_NAME -n $NAMESPACE -- sh -c 'PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME' < $DUMP_FILE"