# Audit & Performance Log Examples

Runnable copies of the FuseQL queries documented on the Kloudfuse
**Auditing → Query Examples** page
(`platform/modules/ROOT/pages/administration/auditing/query-examples.adoc`).

Audit queries start from `@audit_log="true"`. Performance queries start from
`@perf_log="true" and @msg="Finished API"`, which selects one line per completed
API call.

Every query below carries a `<!-- validation: ... -->` marker so
`validate_examples.py` can run it against a live cluster. `kind=metric` runs the
query through `getLogMetricsResultWithKfuseQl`; `kind=raw` runs it through
`getLogsWithFuseQlStream` (filter-only queries with no aggregation).

## Running the validator

```bash
export KLOUDFUSE_HOST=observe.kloudfuse.io
export KLOUDFUSE_TOKEN=glsa_...
python3 validate_examples.py
python3 validate_examples.py --show-output      # print a sample of each result
python3 validate_examples.py --minutes 1440     # widen the default look-back
```

`PASS` = query executed and returned data, `EMPTY` = executed but no rows in the
window (fine for illustrative filters such as the `alice@example.com` example),
`FAIL` = the query was rejected.

## Audit Log Examples

### Count events by action

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" | count by (@action)
```

### Count events by user and action

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" | count by (@user_email, @action)
```

### Everything one user did, by action and resource type

<!-- validation: kind=metric expect=empty -->
```fuseql
@audit_log="true" and @user_email="alice@example.com" | count by (@action, @resource_type)
```

### Changes by resource type

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" | count by (@resource_type, @action)
```

### Successful versus failed operations

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" | count by (@status_1, @action)
```

### Authorization failures by user and denying service

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" and @action="authorization_failure" | count by (@user_email, source)
```

### Logins by user and source IP

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" and @action="logged in" | count by (@user_email, @session_ip)
```

### Group membership changes

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" and (@action="add_user_to_group" or @action="remove_user_from_group") | count by (@user_email, @resource_name, @action)
```

### Service account tokens issued and revoked

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" and @resource_type="service_account" and (@action="create_token" or @action="delete_token") | count by (@user_email, @resource_name, @action)
```

### MCP client registrations, logins, and token refreshes

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" and (@action="mcp.register" or @action="mcp.login" or @action="mcp.token.code_grant" or @action="mcp.token.refresh") | count by (@action, @resource_name)
```

### Top users changing alert rules

<!-- validation: kind=metric -->
```fuseql
@audit_log="true" and @resource_type="AlertRule" | count by (@action, @user_email) | sort by _count desc | limit 5
```

## Performance Log Examples

### Top callers by query volume

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" | count by (@User) | sort by _count desc | limit 5
```

### Query volume by service

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" | count by (source)
```

### Top APIs by query volume

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" | count by (source, @api_name) | sort by _count desc | limit 5
```

### Average latency by caller

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" | avg(@duration_ms) by (@User)
```

### Calls slower than 5 seconds, by service and API

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" and @duration_ms > 5000 | count by (source, @api_name)
```

### p95 latency by service

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" | p95(@duration_ms) by (source)
```

### Failed calls by error type and component

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" and @is_error="true" | count by (source, @error_type, @error_component)
```

### Query volume by origin

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" | count by (source, @ViewName) | sort by _count desc | limit 8
```

### Alert rules with the most evaluation time

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" and @ViewName="alert" | sum(@duration_ms) as total_ms, avg(@duration_ms) as avg_ms by (@AlertName) | sort by total_ms desc | limit 5
```

### Slowest dashboard panels

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" and @ViewName="dashboard" | avg(@duration_ms) as avg_ms, count by (@DashboardName, @PanelName) | sort by avg_ms desc | limit 5
```

### Query volume per hour, by service

<!-- validation: kind=metric -->
```fuseql
@perf_log="true" and @msg="Finished API" | timeslice 1h | count by (_timeslice, source)
```

### Every log line for one request

The request ID is a placeholder — substitute a real `kf_request_id` from your
own data. Validated with `expect=empty` because the placeholder matches nothing.

<!-- validation: kind=raw expect=empty -->
```fuseql
@kf_request_id="3e165960-624c-4ad5-9a35-ab21439da6ec"
```
