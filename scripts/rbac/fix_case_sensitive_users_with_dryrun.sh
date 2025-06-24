#!/bin/bash

# Script to fix case-sensitive email duplicates
# Keeps the lowercase email version and transfers group memberships from mixed-case version
# Usage: ./fix_case_sensitive_users_with_dryrun.sh [--dry-run] [namespace]

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
echo "Finding and fixing case-sensitive email duplicates..."
echo ""

# Function to execute or simulate database commands
execute_db_command() {
    local command="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo "        [DRY RUN] Would execute: $description"
        echo "        Command: $command"
    else
        kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"$command\""
    fi
}

# Function to execute or simulate Grafana deletion
execute_grafana_delete() {
    local grafana_user_id="$1"
    local email="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo "        [DRY RUN] Would delete Grafana user: $email (ID: $grafana_user_id)"
    else
        GRAFANA_PASSWORD=$(kubectl get secret kfuse-grafana-credentials -n "$NAMESPACE" -o jsonpath="{.data.admin-password}" | base64 -d)
        if [ -n "$GRAFANA_PASSWORD" ]; then
            GRAFANA_URL="http://kfuse-grafana.$NAMESPACE.svc.cluster.local"
            DELETE_RESULT=$(kubectl run grafana-delete-temp --image=curlimages/curl:latest --rm -i --restart=Never -n "$NAMESPACE" -- curl -s -X DELETE -u "admin:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/admin/users/$grafana_user_id" 2>/dev/null)
            
            if [ $? -eq 0 ] && [[ "$DELETE_RESULT" == *"User deleted"* ]]; then
                echo "        Successfully deleted user from Grafana"
            else
                echo "        Warning: Failed to delete user from Grafana - $DELETE_RESULT"
            fi
        fi
    fi
}

# Find case-sensitive email duplicates
duplicate_emails=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
SELECT LOWER(email) as lower_email
FROM users 
GROUP BY LOWER(email) 
HAVING COUNT(*) > 1 
AND COUNT(DISTINCT email) > 1
ORDER BY lower_email;\"")

if [ -z "$duplicate_emails" ]; then
    echo "No case-sensitive email duplicates found"
    exit 0
fi

echo "Found case-sensitive duplicates for the following emails:"
echo "$duplicate_emails"
echo ""

# Statistics
total_duplicates=0
total_transfers=0
total_deletions=0

# Process each duplicate email group
while read -r lower_email; do
    lower_email=$(echo "$lower_email" | xargs)
    
    if [ -z "$lower_email" ]; then
        continue
    fi
    
    echo "Processing duplicate emails for: $lower_email"
    
    # Get all users with this email (case-insensitive)
    users_info=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
    SELECT id, email, name, login, role 
    FROM users 
    WHERE LOWER(email) = '$lower_email' 
    ORDER BY email;\"")
    
    if [ -z "$users_info" ]; then
        echo "  No users found for $lower_email"
        continue
    fi
    
    # Find the lowercase version and mixed-case versions
    lowercase_user=""
    mixed_case_users=()
    
    while IFS='|' read -r user_id email name login role; do
        user_id=$(echo "$user_id" | xargs)
        email=$(echo "$email" | xargs)
        name=$(echo "$name" | xargs)
        login=$(echo "$login" | xargs)
        role=$(echo "$role" | xargs)
        
        if [ -z "$user_id" ]; then
            continue
        fi
        
        echo "    Found user: $email (ID: $user_id)"
        
        if [ "$email" = "$lower_email" ]; then
            lowercase_user="$user_id|$email|$name|$login|$role"
            echo "      → This is the lowercase version (KEEP)"
        else
            mixed_case_users+=("$user_id|$email|$name|$login|$role")
            echo "      → This is a mixed-case version (DELETE after transfer)"
            ((total_duplicates++))
        fi
    done <<< "$users_info"
    
    if [ -z "$lowercase_user" ]; then
        echo "  WARNING: No lowercase version found for $lower_email - skipping"
        echo ""
        continue
    fi
    
    if [ ${#mixed_case_users[@]} -eq 0 ]; then
        echo "  No mixed-case versions found - nothing to clean up"
        echo ""
        continue
    fi
    
    # Extract lowercase user details
    IFS='|' read -r lowercase_id lowercase_email lowercase_name lowercase_login lowercase_role <<< "$lowercase_user"
    
    echo "  Lowercase user to keep: $lowercase_email (ID: $lowercase_id)"
    echo "  Mixed-case users to process: ${#mixed_case_users[@]}"
    echo ""
    
    # Process each mixed-case user
    for mixed_user in "${mixed_case_users[@]}"; do
        IFS='|' read -r mixed_id mixed_email mixed_name mixed_login mixed_role <<< "$mixed_user"
        
        echo "    Processing mixed-case user: $mixed_email (ID: $mixed_id)"
        
        # Check group memberships for mixed-case user
        echo "      Checking group memberships..."
        groups=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"SELECT group_id, permission FROM group_members WHERE user_id = '$mixed_id';\"")
        
        if [ -n "$groups" ]; then
            echo "      Found group memberships, transferring to lowercase user..."
            
            # Transfer group memberships
            while IFS='|' read -r group_id permission; do
                group_id=$(echo "$group_id" | xargs)
                permission=$(echo "$permission" | xargs)
                
                if [ -n "$group_id" ]; then
                    echo "        Adding user $lowercase_id to group $group_id with permission $permission"
                    execute_db_command "INSERT INTO group_members (group_id, user_id, permission) VALUES ('$group_id', '$lowercase_id', '$permission') ON CONFLICT (group_id, user_id) DO NOTHING;" "Transfer group membership"
                    ((total_transfers++))
                fi
            done <<< "$groups"
            
            # Remove mixed-case user from all groups
            echo "      Removing mixed-case user from all groups..."
            execute_db_command "DELETE FROM group_members WHERE user_id = '$mixed_id';" "Remove mixed-case user from groups"
        else
            echo "      No group memberships found"
        fi
        
        # Delete user from Grafana
        echo "      Attempting to delete user from Grafana..."
        
        if [ "$DRY_RUN" = true ]; then
            echo "        [DRY RUN] Would check and delete user from Grafana: $mixed_email"
        else
            # Get Grafana admin password
            GRAFANA_PASSWORD=$(kubectl get secret kfuse-grafana-credentials -n "$NAMESPACE" -o jsonpath="{.data.admin-password}" | base64 -d)
            
            if [ -n "$GRAFANA_PASSWORD" ]; then
                GRAFANA_URL="http://kfuse-grafana.$NAMESPACE.svc.cluster.local"
                
                # Search for user in Grafana by email
                echo "        Searching for user in Grafana with email: $mixed_email"
                USER_SEARCH=$(kubectl run grafana-curl-temp --image=curlimages/curl:latest --rm -i --restart=Never -n "$NAMESPACE" -- curl -s -u "admin:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/users/lookup?loginOrEmail=$mixed_email" 2>/dev/null)
                
                if [ $? -eq 0 ] && [ -n "$USER_SEARCH" ] && [[ "$USER_SEARCH" != *"error"* ]]; then
                    GRAFANA_USER_ID=$(echo "$USER_SEARCH" | grep -o '"id":[0-9]*' | cut -d':' -f2)
                    
                    if [ -n "$GRAFANA_USER_ID" ] && [ "$GRAFANA_USER_ID" != "null" ]; then
                        echo "        Found Grafana user with ID: $GRAFANA_USER_ID"
                        execute_grafana_delete "$GRAFANA_USER_ID" "$mixed_email"
                    else
                        echo "        User not found in Grafana"
                    fi
                else
                    echo "        Could not search for user in Grafana or user not found"
                fi
            else
                echo "        Warning: Could not retrieve Grafana admin password"
            fi
        fi
        
        # Delete mixed-case user from rbacdb
        echo "      Deleting mixed-case user from rbacdb..."
        execute_db_command "DELETE FROM users WHERE id = '$mixed_id';" "Delete mixed-case user"
        ((total_deletions++))
        
        echo "      ✓ Mixed-case user processed"
        echo ""
    done
    
    echo "  ✓ Completed processing for: $lower_email"
    echo ""
done <<< "$duplicate_emails"

echo "Summary:"
echo "--------"
echo "Total duplicate users found: $total_duplicates"
echo "Total group memberships to transfer: $total_transfers"
echo "Total users to delete: $total_deletions"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN COMPLETE - No changes were made"
    echo "To apply these changes, run without --dry-run flag"
else
    echo "Verifying final state..."
    echo ""
    
    # Show remaining case-sensitive duplicates
    remaining=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
    SELECT LOWER(email) as lower_email, COUNT(*) as count, STRING_AGG(email, ', ') as all_emails
    FROM users 
    GROUP BY LOWER(email) 
    HAVING COUNT(*) > 1 AND COUNT(DISTINCT email) > 1
    ORDER BY lower_email;\"")
    
    if [ -n "$remaining" ]; then
        echo "Remaining case-sensitive duplicates that need manual intervention:"
        echo "$remaining"
    else
        echo "All case-sensitive email duplicates have been resolved!"
    fi
fi

echo ""
echo "Processing complete!"