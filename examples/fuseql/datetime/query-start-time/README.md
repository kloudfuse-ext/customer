# querystarttime

Returns the start time of the current query window as epoch milliseconds. Use `querystarttime()` to reference the beginning of the selected time range — for example, to filter events relative to the window start or to label output with the range boundaries.

## Syntax

```
| querystarttime() as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| (none) | — | `querystarttime` takes no arguments. |
| `<alias>` | Required | Name for the resulting millisecond epoch timestamp field. |

## Example

Return the query window start time as a formatted date string.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| querystarttime() as start_ts
| formatdate(start_ts, "yyyy-MM-dd HH:mm:ss") as start_str
| first(start_str) by method
```

**Expected output:**

| method | first(start_str) |
|---|---|
| GET | 2026-06-27 17:53:00 |
| POST | 2026-06-27 17:53:00 |

> The raw millisecond value from this query window was `1782582780000`.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | querystarttime() as start_ts | formatdate(start_ts, \\\"yyyy-MM-dd HH:mm:ss\\\") as start_str | first(start_str) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The value is fixed for the duration of the query and reflects the start of the user-selected time range, not when the query started executing.
- Use `queryendtime()` for the end boundary and `querytimerange()` for the window width.
