#!/bin/bash

# Script to fix case-sensitive email duplicates
# Keeps the lowercase email version and transfers group memberships from mixed-case version
# Usage: ./fix_case_sensitive_users_with_dryrun.sh [--dry-run] [--email <email>] [--limit <number>] [namespace]

POD_NAME="kfuse-configdb-0"
DB_NAME="rbacdb"
DB_USER="postgres"
DRY_RUN=false
NAMESPACE="default"
SPECIFIC_EMAIL=""
LIMIT=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --email)
            SPECIFIC_EMAIL="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            if ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || [ "$LIMIT" -eq 0 ]; then
                echo "Error: --limit must be a positive integer"
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--email <email>] [--limit <number>] [namespace]"
            echo ""
            echo "Options:"
            echo "  --dry-run     Preview changes without applying them"
            echo "  --email       Process only the specified email address"
            echo "  --limit       Process only the first N duplicate email groups"
            echo "  namespace     Kubernetes namespace (default: default)"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Process all duplicates in default namespace"
            echo "  $0 --dry-run                          # Dry run for all duplicates"
            echo "  $0 --email john.doe@example.com       # Process only john.doe@example.com"
            echo "  $0 --limit 5                          # Process only first 5 duplicate email groups"
            echo "  $0 --dry-run --limit 10               # Dry run for first 10 duplicate email groups"
            echo "  $0 --dry-run --email user@example.com # Dry run for specific email"
            echo "  $0 production                         # Process all duplicates in production namespace"
            exit 0
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
if [ -n "$SPECIFIC_EMAIL" ]; then
    echo "Processing only email: $SPECIFIC_EMAIL"
else
    if [ -n "$LIMIT" ]; then
        echo "Finding and fixing first $LIMIT case-sensitive email duplicate groups..."
    else
        echo "Finding and fixing all case-sensitive email duplicates..."
    fi
fi
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


# Find case-sensitive email duplicates
if [ -n "$SPECIFIC_EMAIL" ]; then
    # Check if the specific email has case-sensitive duplicates
    duplicate_emails=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
    SELECT LOWER(email) as lower_email
    FROM users 
    WHERE LOWER(email) = LOWER('$SPECIFIC_EMAIL')
    GROUP BY LOWER(email) 
    HAVING COUNT(*) > 1 
    AND COUNT(DISTINCT email) > 1;\"")
else
    # Find all case-sensitive email duplicates
    if [ -n "$LIMIT" ]; then
        duplicate_emails=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
        SELECT LOWER(email) as lower_email
        FROM users 
        GROUP BY LOWER(email) 
        HAVING COUNT(*) > 1 
        AND COUNT(DISTINCT email) > 1
        ORDER BY lower_email
        LIMIT $LIMIT;\"")
    else
        duplicate_emails=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c \"
        SELECT LOWER(email) as lower_email
        FROM users 
        GROUP BY LOWER(email) 
        HAVING COUNT(*) > 1 
        AND COUNT(DISTINCT email) > 1
        ORDER BY lower_email;\"")
    fi
fi

if [ -z "$duplicate_emails" ]; then
    if [ -n "$SPECIFIC_EMAIL" ]; then
        echo "No case-sensitive email duplicates found for: $SPECIFIC_EMAIL"
    else
        echo "No case-sensitive email duplicates found"
    fi
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