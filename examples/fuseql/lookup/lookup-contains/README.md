# lookupContains

Returns `true` if a log field's value exists in a lookup table's key column, and `false` otherwise. Use inside a `where` clause to filter log events based on membership in a pre-defined set — for example, VIP users, known bad IPs, or monitored service names.

## Syntax

```fuseql
| where lookupContains(<table_name>, <log_field> = <table_field>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<table_name>` | Required | Name of an existing lookup table. |
| `<log_field>` | Required | The log field whose value is checked against the lookup table. |
| `<table_field>` | Required | The lookup table column to match against. |

## Example

Filter nginx logs to only include requests from VIP users identified in the `vip_users` table.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| where lookupContains(vip_users, user_id = id)
| count as vip_requests by method
```

**Expected output (illustrative):**

| method | vip_requests |
|---|---|
| GET | 12,430 |
| POST | 3,211 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | where lookupContains(vip_users, user_id = id) | count as vip_requests by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `lookupContains` evaluates each log row independently — more efficient than a full join when you only need membership testing.
- To retrieve fields from the table (not just test membership), use `lookup` instead.
- The lookup table must exist and be populated before the query runs.
