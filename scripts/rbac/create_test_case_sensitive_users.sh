#!/bin/bash

# Script to create test users with case-sensitive email duplicates
# This will help test the fix_case_sensitive_users.sh script

POD_NAME="kfuse-configdb-0"
DB_NAME="rbacdb"
DB_USER="postgres"
NAMESPACE="${1:-suryadev}"  # Default to suryadev namespace

echo "Creating test users with case-sensitive emails in namespace: $NAMESPACE"
echo ""

# Function to generate UUID
generate_uuid() {
    cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen
}

# Create test groups first
echo "Creating test groups..."
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
INSERT INTO groups (id, name, email, team_id) VALUES 
    ('test-group-1', 'Test Group 1', 'test-group-1@test.com', '1'),
    ('test-group-2', 'Test Group 2', 'test-group-2@test.com', '2')
ON CONFLICT (id) DO NOTHING;\""

echo ""
echo "Creating test users with case-sensitive email duplicates..."

# Test Case 1: Benjamin Nguyen
echo "Test Case 1: Benjamin Nguyen (mixed case vs lowercase)"
USER1_ID=$(generate_uuid)
USER2_ID=$(generate_uuid)

kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
-- Mixed case version
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    ('$USER1_ID', 'Benjamin.Nguyen@gehealthcare.com', 'Benjamin Nguyen', 'Editor', '250003451@hc.ge.com', NULL, NULL, false);

-- Lowercase version (this is the one we want to keep)
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    ('$USER2_ID', 'benjamin.nguyen@gehealthcare.com', 'Benjamin Nguyen', 'Editor', '250003451@hc.ge.com', NULL, NULL, false);\""

# Add mixed-case user to groups
echo "  Adding mixed-case user to test groups..."
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
INSERT INTO group_members (group_id, user_id, permission) VALUES 
    ('test-group-1', '$USER1_ID', 'Member'),
    ('test-group-2', '$USER1_ID', 'Admin')
ON CONFLICT DO NOTHING;\""

# Test Case 2: John Doe
echo ""
echo "Test Case 2: John Doe (multiple mixed cases)"
USER3_ID=$(generate_uuid)
USER4_ID=$(generate_uuid)
USER5_ID=$(generate_uuid)

kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
-- All caps version
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    ('$USER3_ID', 'JOHN.DOE@KLOUDFUSE.COM', 'John Doe', 'Viewer', 'john.doe', NULL, NULL, false);

-- Mixed case version
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    ('$USER4_ID', 'John.Doe@kloudfuse.com', 'John Doe', 'Viewer', 'john.doe', NULL, NULL, false);

-- Lowercase version (this is the one we want to keep)
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    ('$USER5_ID', 'john.doe@kloudfuse.com', 'John Doe', 'Viewer', 'john.doe', NULL, NULL, false);\""

# Add mixed-case users to groups
echo "  Adding mixed-case users to test groups..."
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
INSERT INTO group_members (group_id, user_id, permission) VALUES 
    ('test-group-1', '$USER3_ID', 'Member'),
    ('test-group-2', '$USER4_ID', 'Admin')
ON CONFLICT DO NOTHING;\""

# Test Case 3: Alice Smith (only mixed case, no lowercase version)
echo ""
echo "Test Case 3: Alice Smith (only mixed case versions, no lowercase)"
USER6_ID=$(generate_uuid)
USER7_ID=$(generate_uuid)

kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
-- Mixed case version 1
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    ('$USER6_ID', 'Alice.Smith@Test.Com', 'Alice Smith', 'Admin', 'alice.smith', NULL, NULL, false);

-- Mixed case version 2
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    ('$USER7_ID', 'ALICE.SMITH@TEST.COM', 'Alice Smith', 'Admin', 'alice.smith', NULL, NULL, false);\""

# Add to groups
echo "  Adding Alice Smith users to test groups..."
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
INSERT INTO group_members (group_id, user_id, permission) VALUES 
    ('test-group-1', '$USER6_ID', 'Admin'),
    ('test-group-2', '$USER7_ID', 'Member')
ON CONFLICT DO NOTHING;\""

echo ""
echo "Verifying test data creation..."
echo ""

# Show all test users
echo "Test users created:"
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
SELECT email, name, role, login 
FROM users 
WHERE LOWER(email) IN ('benjamin.nguyen@gehealthcare.com', 'john.doe@kloudfuse.com', 'alice.smith@test.com')
ORDER BY LOWER(email), email;\""

echo ""
echo "Group memberships:"
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
SELECT u.email, g.name as group_name, gm.permission 
FROM group_members gm
JOIN users u ON u.id = gm.user_id
JOIN groups g ON g.id = gm.group_id
WHERE g.id IN ('test-group-1', 'test-group-2')
ORDER BY u.email, g.name;\""

echo ""
echo "Case-sensitive duplicates found:"
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- sh -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U $DB_USER -d $DB_NAME -c \"
SELECT LOWER(email) as lower_email, COUNT(*) as count, STRING_AGG(email, ', ' ORDER BY email) as all_versions
FROM users 
WHERE LOWER(email) IN ('benjamin.nguyen@gehealthcare.com', 'john.doe@kloudfuse.com', 'alice.smith@test.com')
GROUP BY LOWER(email) 
HAVING COUNT(*) > 1
ORDER BY lower_email;\""

echo ""
echo "Test data created successfully!"
echo "You can now run: ./fix_case_sensitive_users.sh $NAMESPACE"