# cat

Reads all rows from a lookup table into the query pipeline. Unlike `lookup` (which joins a table against live log results), `cat` is a source operator — use it to query or filter lookup table contents directly.

## Syntax

```fuseql
cat <lookup_table_name>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<lookup_table_name>` | Required | Name of an existing lookup table. All rows and columns are returned. |

## Example

Read the `userinfo` lookup table and filter to rows where `username` equals "alice".

```fuseql
cat userinfo
| where username = "alice"
```

**Expected output (illustrative):**

| user_id | username | last_seen |
|---|---|---|
| u-10482 | alice | 2026-06-27T18:54:00Z |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"cat userinfo | where username = \\\"alice\\\"\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `cat` is a source operator — it must appear at the start of a query, not after a `|`.
- Pipe additional operators after `cat` to filter, transform, or aggregate the table contents.
- The lookup table must exist and be populated before the query runs. Use `save` to populate it.
