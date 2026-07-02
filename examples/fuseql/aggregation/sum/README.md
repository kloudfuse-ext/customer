# sum

Computes the total sum of a numeric field across matched log lines. The `sum` operator works on numeric facets and ignores null or missing values. Summing response body sizes gives the total data volume served by each method during the query time window — useful for bandwidth analysis.

## Syntax

```fuseql
| sum(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to sum. Null or missing values are ignored. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_sum`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and compute total bytes transferred per HTTP method. Summing response body sizes gives the total data volume served by each method during the query time window — useful for bandwidth analysis.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| sum(bytes) as total_bytes by method
```

**Expected output:**

| method | total_bytes |
|---|---|
| GET | 7,913,715,573 |
| POST | 2,524,318,781 |
| OPTIONS | 138 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | sum(bytes) as total_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `sum` is most meaningful for fields that accumulate, such as bytes transferred. The values above are totals across all log lines in the selected time window.
- Avoid summing fields like timestamps or IDs — use `count`, `min`, or `max` for those instead.
- Pair `sum` with `count` to derive an average without using the `avg` operator, which can be useful when you want to control null handling explicitly.
