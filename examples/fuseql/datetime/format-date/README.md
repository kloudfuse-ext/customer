# formatdate

Converts an epoch millisecond timestamp to a human-readable date string using a specified format pattern and optional timezone (default UTC). Use `formatdate` to produce readable timestamps for display, grouping by time period, or labeling output rows.

## Syntax

```
| formatdate(<dateMilliseconds>) as <alias>

| formatdate(<dateMilliseconds>, <formatString>) as <alias>

| formatdate(<dateMilliseconds>, <formatString>, <timezoneString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<dateMilliseconds>` | Required | An epoch millisecond timestamp field or expression to format. |
| `<formatString>` | Optional | A date format pattern using Java `DateTimeFormatter` tokens. Defaults to `yyyy-MM-dd HH:mm:ss`. |
| `<timezoneString>` | Optional | A timezone identifier such as `UTC` or `America/Los_Angeles`. Defaults to UTC. |
| `<alias>` | Required | Name for the resulting string field. |

## Example

Format the current time as a human-readable date string and return the first value per HTTP method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| formatdate(now(), "yyyy-MM-dd HH:mm") as ts_str
| first(ts_str) by method
```

**Expected output:**

| method | first(ts_str) |
|---|---|
| GET | 2026-06-27 18:52 |
| POST | 2026-06-27 18:52 |

> The exact output depends on the time the query runs.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | formatdate(now(), \\\"yyyy-MM-dd HH:mm\\\") as ts_str | first(ts_str) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Common format tokens: `yyyy` (4-digit year), `MM` (month), `dd` (day), `HH` (24-hour), `mm` (minutes), `ss` (seconds), `SSS` (milliseconds), `a` (AM/PM).
- Use `parsedate` to convert a date string back to epoch milliseconds.
- Timezone defaults to UTC; specify `America/Los_Angeles` or similar for local time.
