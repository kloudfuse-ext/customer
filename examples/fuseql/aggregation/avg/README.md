# avg

Computes the arithmetic mean of a numeric field across matched log lines. The `avg` operator works on numeric facets and ignores null or missing values when calculating the result. Use it to track typical characteristics such as mean response body size per HTTP method.

## Syntax

```fuseql
| avg(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to average. Null or missing values are ignored. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_avg`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and compute the average response body size (in bytes) per HTTP method. A much higher average for GET than POST reflects that GET requests return full resource payloads while POST responses are typically small acknowledgements.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| avg(bytes) as avg_bytes by method
```

**Expected output:**

| method | avg_bytes |
|---|---|
| GET | 87,284.33 |
| POST | 37.77 |
| OPTIONS | 69.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | avg(bytes) as avg_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `avg` aggregates over every log line matching the query within the selected time window. A single returned row represents the mean across all matching events.
- After extracting fields with `parse`, FuseQL coerces string values to numbers automatically.
- `avg` ignores null values rather than treating them as zero, so groups with sparse data still return a meaningful average.
- For worst-case analysis, pair `avg` with `max` to see both the typical and peak values side by side.
