# count

Counts the total number of log lines matched by the query. Unlike most aggregation operators, `count` takes no field argument — it counts rows, not field values. Use it to measure request volume, error frequency, or event occurrence across any grouping.

## Syntax

```fuseql
| count [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `as <alias>` | Optional | Renames the output column. Defaults to `_count`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and count requests per HTTP method to understand traffic distribution.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| count by method
```

**Expected output:**

| method | _count |
|---|---|
| GET | 92,253 |
| POST | 67,267,496 |
| OPTIONS | 2 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | count by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `count` counts every matched log line, including lines where a particular field is null.
- To count only lines where a specific field has a value, add a `where` filter to exclude nulls before counting.
- `count` is the fastest way to measure request volume — pair it with a time grouping to build a request-rate trend.
