# last

Returns the value of a field from the chronologically latest log line within the query window. When grouped with `by`, `last` returns the most recent value observed per group. `last` works on both string and numeric fields — use it to capture the final URL, status, or any other field value at the end of the selected time range.

## Syntax

```fuseql
| last(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The field (string or numeric) whose latest value to return. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_last`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and retrieve the most recent URL requested for each HTTP method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| last(url) by method
```

**Expected output:**

| method | _last |
|---|---|
| GET | /ingester/health/ HTTP/2.0 |
| POST | /ingester/otlp/v1/logs HTTP/2.0 |
| OPTIONS | / HTTP/1.1 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | last(url) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `last` is the counterpart of `first` — together they let you compare the earliest and most recent observations within a window to detect changes or trends.
- `last` works on both string and numeric fields.
- If you need to capture the steady-state value after a warm-up period, use `last`; if you need to capture the initial state, use `first`.
