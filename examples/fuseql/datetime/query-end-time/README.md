# queryendtime

Returns the end time of the current query window as epoch milliseconds. Use `queryendtime()` to reference the end boundary of the selected time range — for example, to compute the elapsed time between an event timestamp and the window end.

## Syntax

```
| queryendtime() as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| (none) | — | `queryendtime` takes no arguments. |
| `<alias>` | Required | Name for the resulting millisecond epoch timestamp field. |

## Example

Return the query window end time as a formatted date string.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| queryendtime() as end_ts
| formatdate(end_ts, "yyyy-MM-dd HH:mm:ss") as end_str
| first(end_str) by method
```

**Expected output:**

| method | first(end_str) |
|---|---|
| GET | 2026-06-27 18:53:00 |
| POST | 2026-06-27 18:53:00 |

> The raw millisecond value from this query window was `1782586380000`.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | queryendtime() as end_ts | formatdate(end_ts, \\\"yyyy-MM-dd HH:mm:ss\\\") as end_str | first(end_str) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The value is fixed for the duration of the query and reflects the end of the user-selected time range.
- Use `querytimerange()` to get the total window width in milliseconds.
