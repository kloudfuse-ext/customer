# now

Returns the current epoch time in milliseconds at the moment the query executes. Use `now()` to compute time-relative expressions — for example, calculating how long ago an event occurred by subtracting a parsed timestamp from the current time.

## Syntax

```
| now() as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| (none) | — | `now` takes no arguments. |
| `<alias>` | Required | Name for the resulting millisecond epoch timestamp field. |

## Example

Capture the current time and convert it to a human-readable date string.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| now() as ts
| formatdate(ts, "yyyy-MM-dd HH:mm") as ts_str
| first(ts_str) by method
```

**Expected output:**

| method | first(ts_str) |
|---|---|
| GET | 2026-06-27 18:52 |
| POST | 2026-06-27 18:52 |

> The raw millisecond value from this query window was `1782586354919`.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | now() as ts | formatdate(ts, \\\"yyyy-MM-dd HH:mm\\\") as ts_str | first(ts_str) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `now()` returns the wall-clock time when the query executes, not the time range boundary.
- Pair with `querystarttime()` or `queryendtime()` to compute offsets within the query window.
- Output is UTC by default; use `formatdate` with a timezone argument to convert.
