# max

Returns the highest value of a numeric field across matched log lines. The `max` operator works on numeric facets and ignores null or missing values. Use it to surface worst-case conditions such as the largest response body served, peak error counts, or maximum resource usage in a window.

## Syntax

```fuseql
| max(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to find the maximum of. Null or missing values are ignored. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_max`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and find the largest response body size (in bytes) per HTTP method. A very large max_bytes for GET reveals the biggest single payload served.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| max(bytes) as max_bytes by method
```

**Expected output:**

| method | max_bytes |
|---|---|
| GET | 35,590,999 |
| POST | 10,422,627 |
| OPTIONS | 138 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | max(bytes) as max_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `max` surfaces worst-case conditions. A single outlier can cause `max` to spike even when `avg` looks healthy — pair `max` with `p99` to distinguish rare extreme outliers from the general tail.
- `max` is useful for detecting oversized responses or capacity issues that `avg` would mask.
- Combine `max` with `min` in a single query to see the full observed range in one result set.
