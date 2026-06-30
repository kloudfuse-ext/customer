# min

Returns the lowest value of a numeric field across matched log lines. The `min` operator works on numeric facets and ignores null or missing values. Use it to find the smallest response body size, best-case values, or the minimum resource usage observed in a window.

## Syntax

```fuseql
| min(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to find the minimum of. Null or missing values are ignored. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_min`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and find the smallest response body size. A min_bytes of 0 indicates that some responses sent no body — for example, 204 No Content or 304 Not Modified responses.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| min(bytes) as min_bytes by method
```

**Expected output:**

| method | min_bytes |
|---|---|
| GET | 0 |
| POST | 0 |
| OPTIONS | 0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | min(bytes) as min_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- A result of 0 bytes does not mean the response failed — status codes like 204 No Content and 304 Not Modified legitimately send no body.
- Combine `min` and `max` to see the full range of response sizes in one result set.
- `min` is useful for establishing a baseline — if `min` is rising over time, it may indicate a systemic shift even when most values still look normal.
