# first

Returns the value of a field from the chronologically earliest log line within the query window. When grouped with `by`, `first` returns the earliest value observed per group. `first` works on both string and numeric fields — use it to capture the initial URL, status, or any other field value at the start of the selected time range.

## Syntax

```fuseql
| first(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The field (string or numeric) whose earliest value to return. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_first`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and retrieve the first URL requested for each HTTP method. This shows the first request path seen for each method within the selected time window.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| first(url) by method
```

**Expected output:**

| method | _first |
|---|---|
| GET | /ingester/_health HTTP/2.0 |
| POST | /api/v2/logs HTTP/1.1 |
| OPTIONS | / HTTP/1.1 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | first(url) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `first` is determined by log ingestion order within the query window, which reflects the timestamp on each log line.
- `first` works on both string and numeric fields.
- Compare `first` against `last` to see whether field values changed over the window.
