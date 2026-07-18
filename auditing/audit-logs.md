# Audit Log Examples

All queries use `source="kf-audit-log"` as the base filter.

---

## Total audit event volume

The simplest compliance question: how many audit events occurred in the window?

```fuseql
source="kf-audit-log" | count
```

**Validated** — `<your-kloudfuse-hostname>`, 30-day window (2026-06-17 → 2026-07-17):

| _count |
|---|
| 264 |

**Validated** — `<your-kloudfuse-hostname>`, 24-hour window (2026-07-16 → 2026-07-17):

| _count |
|---|
| 1 |

---

## Events by action type

The primary breakdown for compliance review — shows the full distribution of what operations
occurred. `action` is the key facet for understanding what the platform was asked to do.

```fuseql
source="kf-audit-log" | count by action
```

**Illustrative output** (expected for a cluster with active users):

| action | _count |
|---|---|
| `logged in` | 147 |
| `create` | 38 |
| `update` | 22 |
| `delete` | 11 |
| `add_user_to_group` | 9 |
| `create_token` | 6 |
| `authorization_failure` | 4 |
| `logged out` | 3 |
| `delete_token` | 2 |

---

## Events by user

Answers "who did what?" — the primary view for user activity auditing.

```fuseql
source="kf-audit-log" | count by user_email, action
```

**Illustrative output**:

| user_email | action | _count |
|---|---|---|
| `alice@example.com` | `logged in` | 42 |
| `alice@example.com` | `create` | 14 |
| `alice@example.com` | `update` | 8 |
| `bob@example.com` | `logged in` | 31 |
| `bob@example.com` | `add_user_to_group` | 5 |
| `svc-automation@example.com` | `create_token` | 6 |
| `svc-automation@example.com` | `delete_token` | 2 |

### Events for a specific user

```fuseql
source="kf-audit-log" user_email="alice@example.com" | count by action, resource_type
```

**Illustrative output**:

| action | resource_type | _count |
|---|---|---|
| `logged in` | `auth` | 42 |
| `create` | `policy` | 9 |
| `create` | `group` | 5 |
| `update` | `user` | 8 |
| `delete` | `policy` | 3 |

---

## Events by resource type and action

Shows the full picture of what kinds of resources were touched and how. Useful for understanding
scope of administrative activity.

```fuseql
source="kf-audit-log" | count by resource_type, action
```

**Illustrative output**:

| resource_type | action | _count |
|---|---|---|
| `auth` | `logged in` | 147 |
| `auth` | `logged out` | 3 |
| `auth` | `user locked` | 2 |
| `user` | `update` | 18 |
| `group` | `create` | 7 |
| `group` | `add_user_to_group` | 9 |
| `group` | `remove_user_from_group` | 4 |
| `policy` | `create` | 12 |
| `policy` | `delete` | 4 |
| `service_account` | `create_token` | 6 |
| `service_account` | `delete_token` | 2 |
| `folder_mapping` | `create` | 3 |

---

## Successful vs failed operations

Comparing success and failure counts surfaces failed mutations that may indicate permission
gaps or misconfigured API calls.

```fuseql
source="kf-audit-log" | count by status, action
```

**Illustrative output**:

| status | action | _count |
|---|---|---|
| `success` | `logged in` | 143 |
| `success` | `create` | 35 |
| `success` | `update` | 20 |
| `failure` | `logged in` | 4 |
| `failure` | `authorization_failure` | 4 |
| `failure` | `create` | 3 |

---

## Authorization failures

### By user

Identifies users repeatedly hitting permission boundaries — often indicates a misconfigured
policy or automation credential with insufficient permissions.

```fuseql
source="kf-audit-log" action="authorization_failure" | count by user_email
```

**Illustrative output**:

| user_email | _count |
|---|---|
| `svc-pipeline@example.com` | 12 |
| `carol@example.com` | 3 |
| `bob@example.com` | 1 |

### By resource type

Shows which resource categories are generating the most denials.

```fuseql
source="kf-audit-log" action="authorization_failure" | count by resource_type
```

**Illustrative output**:

| resource_type | _count |
|---|---|
| `policy` | 8 |
| `group` | 4 |
| `user` | 2 |

---

## Authentication events

### Login activity

```fuseql
source="kf-audit-log" resource_type="auth" | count by action, status
```

**Illustrative output**:

| action | status | _count |
|---|---|---|
| `logged in` | `success` | 143 |
| `logged in` | `failure` | 4 |
| `logged out` | `success` | 31 |
| `user locked` | `failure` | 2 |

### Logins by user

```fuseql
source="kf-audit-log" action="logged in" status="success" | count by user_email
```

**Illustrative output**:

| user_email | _count |
|---|---|
| `alice@example.com` | 42 |
| `bob@example.com` | 31 |
| `carol@example.com` | 28 |
| `svc-automation@example.com` | 12 |

---

## Group membership changes

`resource_name` is the group being changed; `resource_id` is the user being added or removed.

```fuseql
source="kf-audit-log" (action="add_user_to_group" OR action="remove_user_from_group") | count by user_email, resource_name, action
```

**Illustrative output**:

| user_email | resource_name | action | _count |
|---|---|---|---|
| `alice@example.com` | `platform-admins` | `add_user_to_group` | 3 |
| `alice@example.com` | `read-only` | `remove_user_from_group` | 2 |
| `bob@example.com` | `platform-admins` | `add_user_to_group` | 1 |

---

## Service account token activity

Tracks when service account tokens are created or revoked, and by whom.

```fuseql
source="kf-audit-log" resource_type="service_account" (action="create_token" OR action="delete_token") | count by user_email, resource_name, action
```

**Illustrative output**:

| user_email | resource_name | action | _count |
|---|---|---|---|
| `alice@example.com` | `svc-automation` | `create_token` | 4 |
| `alice@example.com` | `svc-pipeline` | `create_token` | 2 |
| `bob@example.com` | `svc-automation` | `delete_token` | 1 |

---

## Log field reference

### Facets

These fields are indexed and appear in the Logs UI Facets panel. They can be used as filters
and, on clusters with full Pinot indexing, for aggregation queries.

| Field | Type | Values / notes |
|---|---|---|
| `action` | string | `logged in`, `logged out`, `user locked`, `create`, `update`, `delete`, `add_user_to_group`, `remove_user_from_group`, `create_token`, `delete_token`, `create_mapping`, `delete_mapping`, `authorization_failure`, `DeleteFolder`, `federation.join` |
| `user_email` | string | Email of the user who performed the action |
| `role` | string | `admin` or `editor` |
| `resource_type` | string | `auth`, `user`, `group`, `service_account`, `policy`, `policy_mapping`, `folder_mapping`, `class_default` |
| `resource_name` | string | Human-readable name of the affected resource (user email, group name, policy name, etc.) |
| `status` | string | `success` or `failure` |
| `error_code` | string | HTTP status code on failure (e.g. `403`); `none` on success |
| `duration_ms` | integer | How long the operation took in milliseconds |

### Additional fields in the log body

These fields are present in every log entry's JSON body but are not indexed as Facets.

| Field | Type | Description |
|---|---|---|
| `resource_id` | string | Unique ID of the affected resource; falls back to `resource_name` when no distinct ID exists |
| `user_id` | string | Internal ID of the acting user |
| `user_agent` | string | HTTP User-Agent of the calling client |
| `request_id` | string | Unique request identifier for cross-service correlation |
| `error_message` | string | Error detail on failure; `none` on success |
| `args` | string | Additional context for the operation (varies by action type) |

---

## API call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <sa-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"kf-audit-log\\\" | count by action\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```
