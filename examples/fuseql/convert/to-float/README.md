# tofloat

Parses a string representation of a number, or an integer, to a floating-point value. Use `tofloat` when a field is stored as a string but must be treated as a float for precise arithmetic or aggregation.

## Syntax

```
| tofloat(<number>) as <alias>

| tofloat(<numberString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` or `<numberString>` | Required | A numeric field, integer, or string representation of a number to convert to a floating-point value. |
| `<alias>` | Required | Name for the resulting float field. |

## Example

Convert the `bytes` field parsed from nginx logs to a float and compute the average response size per HTTP method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| tofloat(bytes) as bytes_float
| avg(bytes_float) as avg_bytes by method
```

**Expected output:**

| method | avg_bytes |
|---|---|
| GET | 87284.0 |
| POST | 37.0 |
| HEAD | 0.0 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | tofloat(bytes) as bytes_float | avg(bytes_float) as avg_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Use `tofloat` when dividing counts to compute rates, so the result is not integer-truncated.
- Use `toint` when you need an integer result and decimal precision is not needed.
