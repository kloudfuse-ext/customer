# save

Inserts or updates rows in a lookup table using the current query's result set. Existing rows with matching primary keys are updated; new keys are inserted. Use `save` to keep a lookup table current with live log data.

## Syntax

```fuseql
| save <lookup_table_name>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<lookup_table_name>` | Required | Name of an existing lookup table. The query result's column names must match the table schema. |

## Example

Extract user details from login logs and save to the `userinfo` lookup table.

```fuseql
source="login_application"
| json "user_id", "username", "email", "last_seen"
| save userinfo
```

**Expected output (illustrative — rows written to userinfo table):**

| user_id | username | last_seen |
|---|---|---|
| u-10482 | alice | 2026-06-27T18:54:00Z |
| u-20917 | bob | 2026-06-27T18:55:00Z |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"login_application\\\" | json \\\"user_id\\\", \\\"username\\\", \\\"email\\\", \\\"last_seen\\\" | save userinfo\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- The lookup table must exist in the Kloudfuse UI with a schema matching the query output columns.
- `save` is a terminal stage — it writes results and does not pass rows downstream.
- After saving, use `cat` to read the table back into a query, or `lookup` to join it against another source.
