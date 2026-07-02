# percentiles

Computes percentile values of a numeric field across matched log lines. Percentile operators are expressed as `p<N>()` — for example `p50()`, `p90()`, `p99()`. Available operators are: `p16`, `p50`, `p75`, `p84`, `p90`, `p95`, and `p99`. Multiple percentile operators can be combined in a single query pipe stage to produce several percentile columns at once. Null or missing field values are ignored.

> **Note:** The syntax is `p50(field)`, `p90(field)`, `p99(field)`, etc. — not `percentile(field, 50)` or `percentile(field, N)`.

## Syntax

```fuseql
| p50(<field>) [as <alias>] [, p90(<field>) [as <alias>] ...] [by <field1>, <field2>, ...]
```

Available operators: `p16`, `p50`, `p75`, `p84`, `p90`, `p95`, `p99`

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to compute the percentile of. Null or missing values are ignored. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_p<N>` (e.g. `_p50`). |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and compute p50, p90, and p99 of response body size per HTTP method. The large gap between GET p50 (138 bytes) and p99 (3,678,129 bytes) reveals that while most GET responses are small, the top 1% are multi-megabyte payloads.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| p50(bytes) as p50_bytes, p90(bytes) as p90_bytes, p99(bytes) as p99_bytes by method
```

**Expected output:**

| method | p50_bytes | p90_bytes | p99_bytes |
|---|---|---|---|
| GET | 138 | 3,026 | 3,678,129 |
| POST | 2 | 2 | 2 |
| OPTIONS | 69 | 124 | 137 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | p50(bytes) as p50_bytes, p90(bytes) as p90_bytes, p99(bytes) as p99_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Use `p95` or `p99` for SLO threshold checks and `p50` (the median) for typical behaviour not skewed by outliers.
- A large gap between `p50` and `p99` indicates a long-tail distribution that averaged metrics would obscure.
- Use `p50` as a robust median — it is not skewed by outliers the way `avg` can be.
- The operators are `p50()`, `p90()`, `p99()`, etc. — the `percentile(field, N)` syntax is not supported.
