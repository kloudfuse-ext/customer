# hextodec

Converts a hexadecimal (base-16) string to its decimal (base-10) integer value. Use `hextodec` to decode hex-encoded identifiers, status codes, or addresses that appear in log fields before performing arithmetic or numeric comparisons.

## Syntax

```
| hextodec(<hexString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<hexString>` | Required | A hexadecimal string field or literal to convert to a decimal integer. |
| `<alias>` | Required | Name for the resulting decimal integer field. |

## Example

Convert hex status code strings back to their decimal equivalents.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| dectohex(status) as status_hex
| hextodec(status_hex) as status_dec
| first(status_dec) by status
```

**Expected output:**

| status | first(status_dec) |
|---|---|
| 200 | 200 |
| 304 | 304 |
| 404 | 404 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | dectohex(status) as status_hex | hextodec(status_hex) as status_dec | first(status_dec) by status\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The hex string must contain valid hexadecimal characters (0-9, a-f, A-F).
- Use `dectohex` to convert in the opposite direction.
