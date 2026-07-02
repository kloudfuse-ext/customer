# querytimerange

Returns the total duration of the current query window in milliseconds. Use `querytimerange()` to scale per-window aggregations to a rate — for example, dividing an event count by the window duration to compute events per second regardless of the selected time range.

## Syntax

```
| querytimerange() as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| (none) | — | `querytimerange` takes no arguments. |
| `<alias>` | Required | Name for the resulting millisecond duration field. |

## Example

Compute the request rate (requests per second) for each HTTP method by dividing the count by the query window duration.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| count by method
| querytimerange() as window_ms
| eval((_count / window_ms) * 1000) as rps
```

**Expected output:**

| method | _count | rps |
|---|---|---|
| POST | 2,159,649 | 599.9 |
| GET | 3,091 | 0.86 |
| HEAD | 183 | 0.05 |

> The raw millisecond value from this query window was `3,600,000` (1 hour). Values shown are illustrative; actual results depend on your log data and selected time range.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | count by method | querytimerange() as window_ms | eval((_count / window_ms) * 1000) as rps\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Equivalent to `queryendtime() - querystarttime()`.
- Use this value to normalize counts to per-second or per-minute rates that remain consistent across different time range selections.
