#!/bin/bash

# Script to automatically fix users where email = login (Okta UID)
# This version doesn't require a CSV file and includes dry-run mode
# Usage: ./fix_users_auto_with_dryrun.sh [--dry-run] [namespace]

POD_NAME="kfuse-configdb-0"
DB_NAME="rbacdb"
DB_USER="postgres"
DRY_RUN=false
NAMESPACE="default"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            NAMESPACE="$1"
            shift
            ;;
    esac
done

if [ "$DRY_RUN" = true ]; then
    echo "======================================"
    echo "DRY RUN MODE - No changes will be made"
    echo "======================================"
    echo ""
fi

echo "Processing users in namespace: $NAMESPACE"
echo "Finding and fixing users where email = login (Okta UID format)..."
echo ""

# Function to execute or simulate database commands
execute_db_command() {
    local command="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo "      [DRY RUN] Would execute: $description"
        echo "      Command: $command"
    else
        kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"$command\""
    fi
}

# Function to execute or simulate Grafana deletion
execute_grafana_delete() {
    local grafana_user_id="$1"
    local uid="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo "      [DRY RUN] Would delete Grafana user: $uid (ID: $grafana_user_id)"
    else
        GRAFANA_PASSWORD=$(kubectl get secret kfuse-grafana-credentials -n "$NAMESPACE" -o jsonpath="{.data.admin-password}" | base64 -d)
        if [ -n "$GRAFANA_PASSWORD" ]; then
            GRAFANA_URL="http://kfuse-grafana.$NAMESPACE.svc.cluster.local"
            DELETE_RESULT=$(kubectl run grafana-delete-temp --image=curlimages/curl:latest --rm -i --restart=Never -n "$NAMESPACE" -- curl -s -X DELETE -u "admin:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/admin/users/$grafana_user_id" 2>/dev/null)
            
            if [ $? -eq 0 ] && [[ "$DELETE_RESULT" == *"User deleted"* ]]; then
                echo "    Successfully deleted user from Grafana"
            else
                echo "    Warning: Failed to delete user from Grafana - $DELETE_RESULT"
            fi
        fi
    fi
}

# Find all users where email = login and email looks like an Okta UID
users_to_fix=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT DISTINCT login FROM users WHERE email = login;\"")

if [ -z "$users_to_fix" ]; then
    echo "No users found with email = login in Okta UID format"
    exit 0
fi

# Statistics
total_to_fix=0
total_fixed=0
total_orphaned=0
total_transfers=0

# Process each user
while read -r uid; do
    uid=$(echo "$uid" | xargs)
    
    if [ -z "$uid" ]; then
        continue
    fi
    
    ((total_to_fix++))
    echo "Processing user with UID: $uid"
    
    # Check if there are multiple entries for this login (case-insensitive)
    user_count=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM users WHERE LOWER(login) = LOWER('$uid');\"" | xargs)
    
    if [ "$user_count" -gt 1 ]; then
        echo "  Found $user_count users with login: $uid"
        
        # Get the user where email = login (case-sensitive for email, case-insensitive for login)
        user_with_uid_email=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT id FROM users WHERE LOWER(login) = LOWER('$uid') AND email = '$uid' LIMIT 1;\"" | xargs)
        
        if [ -n "$user_with_uid_email" ]; then
            echo "  Found user with email=login: $user_with_uid_email"
            
            # Check if this is the dashuser - protect from deletion
            if [ "$uid" = "dashuser" ]; then
                echo "  SKIPPING dashuser - this is a protected system user"
                continue
            fi
            
            # Get the user with proper email (not equal to login, case-insensitive login check)
            user_with_proper_email=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT id, email FROM users WHERE LOWER(login) = LOWER('$uid') AND email != '$uid' LIMIT 1;\"")
            
            if [ -n "$user_with_proper_email" ]; then
                proper_user_id=$(echo "$user_with_proper_email" | cut -d'|' -f1 | xargs)
                proper_email=$(echo "$user_with_proper_email" | cut -d'|' -f2 | xargs)
                
                echo "  User with proper email exists: $proper_user_id (email: $proper_email)"
                
                # Check which groups the user with email=login belongs to
                echo "  Checking group memberships for user $user_with_uid_email..."
                groups=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT group_id, permission FROM group_members WHERE user_id = '$user_with_uid_email';\"")
                
                if [ -n "$groups" ]; then
                    echo "  Found group memberships, transferring to user with proper email..."
                    
                    # Transfer group memberships
                    while IFS='|' read -r group_id permission; do
                        group_id=$(echo "$group_id" | xargs)
                        permission=$(echo "$permission" | xargs)
                        
                        if [ -n "$group_id" ]; then
                            echo "    Adding user $proper_user_id to group $group_id with permission $permission"
                            execute_db_command "INSERT INTO group_members (group_id, user_id, permission) VALUES ('$group_id', '$proper_user_id', '$permission') ON CONFLICT (group_id, user_id) DO NOTHING;" "Transfer group membership"
                            ((total_transfers++))
                        fi
                    done <<< "$groups"
                    
                    # Remove the user from all groups after transfer
                    echo "  Removing user $user_with_uid_email from all groups..."
                    execute_db_command "DELETE FROM group_members WHERE user_id = '$user_with_uid_email';" "Remove from all groups"
                else
                    echo "  No group memberships found for user $user_with_uid_email"
                fi
                
                # Always delete the user with email=login
                echo "  Deleting user with email=login: $user_with_uid_email"
                
                # Delete user from Grafana
                echo "  Attempting to delete user from Grafana..."
                
                if [ "$DRY_RUN" = true ]; then
                    echo "    [DRY RUN] Would check and delete user from Grafana: $uid"
                else
                    # Get Grafana admin password
                    GRAFANA_PASSWORD=$(kubectl get secret kfuse-grafana-credentials -n "$NAMESPACE" -o jsonpath="{.data.admin-password}" | base64 -d)
                    
                    if [ -n "$GRAFANA_PASSWORD" ]; then
                        GRAFANA_URL="http://kfuse-grafana.$NAMESPACE.svc.cluster.local"
                        
                        echo "    Searching for user in Grafana with login: $uid"
                        USER_SEARCH=$(kubectl run grafana-curl-temp --image=curlimages/curl:latest --rm -i --restart=Never -n "$NAMESPACE" -- curl -s -u "admin:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/users/lookup?loginOrEmail=$uid" 2>/dev/null)
                        
                        if [ $? -eq 0 ] && [ -n "$USER_SEARCH" ] && [[ "$USER_SEARCH" != *"error"* ]]; then
                            GRAFANA_USER_ID=$(echo "$USER_SEARCH" | grep -o '"id":[0-9]*' | cut -d':' -f2)
                            
                            if [ -n "$GRAFANA_USER_ID" ] && [ "$GRAFANA_USER_ID" != "null" ]; then
                                echo "    Found Grafana user with ID: $GRAFANA_USER_ID"
                                execute_grafana_delete "$GRAFANA_USER_ID" "$uid"
                            else
                                echo "    User not found in Grafana"
                            fi
                        else
                            echo "    Could not search for user in Grafana or user not found"
                        fi
                    else
                        echo "    Warning: Could not retrieve Grafana admin password"
                    fi
                fi
                
                # Delete from rbacdb
                execute_db_command "DELETE FROM users WHERE id = '$user_with_uid_email';" "Delete user with email=login"
                ((total_fixed++))
            else
                echo "  No user found with proper email for login: $uid"
                echo "  Cannot fix this user automatically - needs manual intervention"
                ((total_orphaned++))
            fi
        fi
    else
        echo "  Only one user found with login: $uid"
        echo "  Cannot fix automatically - no duplicate with proper email exists"
        ((total_orphaned++))
    fi
    
    echo ""
done <<< "$users_to_fix"

echo "Summary:"
echo "--------"
echo "Total users to fix: $total_to_fix"
echo "Successfully fixed: $total_fixed"
echo "Orphaned (need manual intervention): $total_orphaned"
echo "Group memberships transferred: $total_transfers"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN COMPLETE - No changes were made"
    echo "To apply these changes, run without --dry-run flag"
else
    echo "Verifying final state..."
    echo ""
    
    # Show remaining users where email = login
    remaining=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"SELECT id, email, name, login FROM users WHERE email = login ORDER BY login;\"")
    
    if [ -n "$remaining" ]; then
        echo "Remaining users that need manual intervention:"
        echo "$remaining"
    else
        echo "All users have been processed successfully!"
    fi
fi

echo ""
echo "Processing complete!"