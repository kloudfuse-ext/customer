# parsedate

Parses a date string using a specified format pattern and optional timezone (default UTC), and returns the corresponding epoch milliseconds as a long integer. Use `parsedate` to convert human-readable timestamps extracted from log fields into numeric epoch values for arithmetic, filtering, or comparison.

## Syntax

```
| parsedate(<dateString>, <formatString>) as <alias>

| parsedate(<dateString>, <formatString>, <timezoneString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<dateString>` | Required | A string field or literal containing the date to parse. |
| `<formatString>` | Required | A date format pattern matching the input string, using Java `DateTimeFormatter` tokens. |
| `<timezoneString>` | Optional | A timezone identifier such as `UTC` or `America/Los_Angeles`. Defaults to UTC. |
| `<alias>` | Required | Name for the resulting epoch millisecond field. |

## Example

Parse the nginx access log date field into epoch milliseconds and return the earliest timestamp in the window.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| parsedate("dd/MMM/yyyy:HH:mm:ss Z", date) as ts_ms
| min(ts_ms) as earliest
```

**Expected output:**

| earliest |
|---|
| 1782582780123 |

> Values shown are illustrative; actual results depend on your log data and the selected time window.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | parsedate(\\\"dd/MMM/yyyy:HH:mm:ss Z\\\", date) as ts_ms | min(ts_ms) as earliest\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `parsedate` is the inverse of `formatdate` and uses the same format pattern tokens.
- A format mismatch between the pattern and the input string returns an error or null.
- Nginx access log dates use the format `dd/MMM/yyyy:HH:mm:ss Z` (e.g., `27/Jun/2026:18:52:00 +0000`).
