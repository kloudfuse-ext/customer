# toint

Parses a string representation of a number, or a floating-point number, to an integer by truncating the decimal portion. Use `toint` when a field is stored as a string but must be treated as an integer for arithmetic, comparison, or aggregation.

## Syntax

```
| toint(<number>) as <alias>

| toint(<numberString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` or `<numberString>` | Required | A numeric field, floating-point value, or string representation of a number to convert. Decimal portions are truncated. |
| `<alias>` | Required | Name for the resulting integer field. |

## Example

Convert the `bytes` field parsed from nginx logs to an integer and compute the average response size per HTTP method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| toint(bytes) as bytes_int
| avg(bytes_int) as avg_bytes by method
```

**Expected output:**

| method | avg_bytes |
|---|---|
| GET | 87,284 |
| POST | 37 |
| HEAD | 0 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | toint(bytes) as bytes_int | avg(bytes_int) as avg_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Decimal values are truncated, not rounded — `toint("1.9")` returns `1`.
- Use `tofloat` when decimal precision matters.
