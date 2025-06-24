#!/bin/bash

# Script to delete users where email = login and user has no group memberships
# Usage: ./cleanup_orphaned_users.sh [namespace]

POD_NAME="kfuse-configdb-0"
DB_NAME="rbacdb"
DB_USER="postgres"
NAMESPACE="${1:-default}"  # Allow namespace to be passed as first argument

echo "Processing users in namespace: $NAMESPACE"
echo "Finding users where email = login and have no group memberships..."
echo ""

# Find all users where email = login (Okta UID format) and have no group memberships
orphaned_users=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
SELECT u.id, u.login, u.email 
FROM users u 
LEFT JOIN group_members gm ON u.id = gm.user_id 
WHERE u.email = u.login 
AND u.email LIKE '00u%' 
AND gm.user_id IS NULL
ORDER BY u.login;\"")

if [ -z "$orphaned_users" ]; then
    echo "No orphaned users found (users with email=login and no group memberships)"
    exit 0
fi

# Count total users to process
total_users=$(echo "$orphaned_users" | grep -c '00u')
echo "Found $total_users orphaned user(s) to process"
echo ""

# Process each orphaned user
deleted_count=0
while IFS='|' read -r user_id login email; do
    user_id=$(echo "$user_id" | xargs)
    login=$(echo "$login" | xargs)
    email=$(echo "$email" | xargs)
    
    if [ -z "$user_id" ]; then
        continue
    fi
    
    echo "Processing orphaned user:"
    echo "  ID: $user_id"
    echo "  Login: $login"
    echo "  Email: $email"
    
    # Double-check that user has no group memberships
    group_count=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM group_members WHERE user_id = '$user_id';\"" | xargs)
    
    if [ "$group_count" -eq 0 ]; then
        echo "  Confirmed: User has no group memberships"
        echo "  Deleting user..."
        
        # Delete the user
        kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"DELETE FROM users WHERE id = '$user_id';\""
        
        if [ $? -eq 0 ]; then
            echo "  ✓ User deleted successfully"
            ((deleted_count++))
        else
            echo "  ✗ Error deleting user"
        fi
    else
        echo "  WARNING: User has $group_count group membership(s) - skipping deletion"
    fi
    
    echo ""
done <<< "$orphaned_users"

echo "Summary:"
echo "========="
echo "Total orphaned users found: $total_users"
echo "Users deleted: $deleted_count"
echo ""

# Show remaining users where email = login
echo "Checking for any remaining users where email = login..."
remaining=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"SELECT id, email, name, login, (SELECT COUNT(*) FROM group_members WHERE user_id = users.id) as group_count FROM users WHERE email = login AND email LIKE '00u%' ORDER BY login;\"")

if [ -n "$remaining" ]; then
    echo "$remaining"
else
    echo "No users found where email = login"
fi

echo ""
echo "Cleanup complete!"