-- Test data for fix_users_auto.sh script
-- This creates users where email = login (Okta UID format) and their proper counterparts

-- First, ensure we have test groups
INSERT INTO groups (id, name, email, team_id) VALUES 
    ('auto-test-group-1', 'Auto Test Group 1', 'auto-test-group-1@test.com', 1),
    ('auto-test-group-2', 'Auto Test Group 2', 'auto-test-group-2@test.com', 2)
ON CONFLICT (id) DO NOTHING;

-- Test Case 1: User with email=login and proper user exists
-- Broken user (email = login)
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    (gen_random_uuid(), '550015251@hc.ge.com', 'Yeswanth Reddy (Broken)', 'Viewer', '550015251@hc.ge.com', NULL, NULL, false);

-- Proper user (correct email)
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    (gen_random_uuid(), 'yeswanthreddy.velapalem@gehealthcare.com', 'Yeswanth Reddy', 'Viewer', '550015251@hc.ge.com', NULL, NULL, false);

-- Add the broken user to groups (these memberships should be transferred)
INSERT INTO group_members (group_id, user_id, permission) 
SELECT 'auto-test-group-1', id, 'Member' FROM users WHERE email = '550015251@hc.ge.com' AND login = '550015251@hc.ge.com'
ON CONFLICT DO NOTHING;

INSERT INTO group_members (group_id, user_id, permission) 
SELECT 'auto-test-group-2', id, 'Admin' FROM users WHERE email = '550015251@hc.ge.com' AND login = '550015251@hc.ge.com'
ON CONFLICT DO NOTHING;

-- Test Case 2: Another user with email=login
-- Broken user
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    (gen_random_uuid(), '450012345@hc.ge.com', 'John Smith (Broken)', 'Editor', '450012345@hc.ge.com', NULL, NULL, false);

-- Proper user
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    (gen_random_uuid(), 'john.smith@gehealthcare.com', 'John Smith', 'Editor', '450012345@hc.ge.com', NULL, NULL, false);

-- Add broken user to a group
INSERT INTO group_members (group_id, user_id, permission) 
SELECT 'auto-test-group-1', id, 'Member' FROM users WHERE email = '450012345@hc.ge.com' AND login = '450012345@hc.ge.com'
ON CONFLICT DO NOTHING;

-- Test Case 3: User with email=login but NO proper user exists (edge case)
-- This should be reported as needing manual intervention
INSERT INTO users (id, email, name, role, login, grafana_id, grafana_org_id, service_account) VALUES 
    (gen_random_uuid(), '350099999@hc.ge.com', 'Orphan User', 'Viewer', '350099999@hc.ge.com', NULL, NULL, false);

-- Add to group
INSERT INTO group_members (group_id, user_id, permission) 
SELECT 'auto-test-group-2', id, 'Member' FROM users WHERE email = '350099999@hc.ge.com' AND login = '350099999@hc.ge.com'
ON CONFLICT DO NOTHING;

-- Verify the test data
SELECT 'Users with email=login:' as info;
SELECT email, name, role, login FROM users 
WHERE email = login 
AND email IN ('550015251@hc.ge.com', '450012345@hc.ge.com', '350099999@hc.ge.com')
ORDER BY email;

SELECT '' as blank;
SELECT 'All users with these logins:' as info;
SELECT email, name, role, login FROM users 
WHERE login IN ('550015251@hc.ge.com', '450012345@hc.ge.com', '350099999@hc.ge.com')
ORDER BY login, email;

SELECT '' as blank;
SELECT 'Group memberships for broken users:' as info;
SELECT u.email, u.login, g.name as group_name, gm.permission 
FROM group_members gm
JOIN users u ON u.id = gm.user_id
JOIN groups g ON g.id = gm.group_id
WHERE u.email = u.login
AND u.email IN ('550015251@hc.ge.com', '450012345@hc.ge.com', '350099999@hc.ge.com')
ORDER BY u.email, g.name;