# toduration

Converts a string representation of a time duration to its value in milliseconds. Use `toduration` to normalize latency or elapsed-time fields before aggregating them.

## Syntax

```
| toduration(<timeString>) as <alias>
```

Supported unit suffixes: `ns` (nanoseconds), `µs`/`us` (microseconds), `ms` (milliseconds), `s` (seconds), `m` (minutes), `h` (hours).

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<timeString>` | Required | A string field or literal representing a duration with a unit suffix. |
| `<alias>` | Required | Name for the resulting numeric field (milliseconds). |

## Example

Extract duration values from query-service logs and compute the average latency in milliseconds.

```fuseql
source="query-service"
| parse "* duration=*ms*" as pre,duration_ms,post
| toduration(duration_ms) as dur_num
| avg(dur_num) as avg_ms
```

**Expected output:**

| avg_ms |
|---|
| 145.3 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"query-service\\\" | parse \\\"* duration=*ms*\\\" as pre,duration_ms,post | toduration(duration_ms) as dur_num | avg(dur_num) as avg_ms\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The unit suffix must be part of the string argument — pass `"188ms"` not `"188"`.
- A value in nanoseconds such as `"500000ns"` is converted to `0.5` ms.
- Output is always in milliseconds regardless of the input unit.
