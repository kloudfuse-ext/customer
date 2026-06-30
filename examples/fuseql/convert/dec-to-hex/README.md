# dectohex

Converts a decimal (base-10) integer to its hexadecimal (base-16) string representation. Use `dectohex` to transform numeric fields — such as HTTP status codes or port numbers — into hex for display or correlation with hex-encoded identifiers.

## Syntax

```
| dectohex(<longField>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<longField>` | Required | A decimal integer field or literal to convert to hexadecimal. |
| `<alias>` | Required | Name for the resulting hexadecimal string field. |

## Example

Convert HTTP status codes parsed from nginx logs to their hexadecimal equivalents.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| dectohex(status) as status_hex
| first(status_hex) by status
```

**Expected output:**

| status | first(status_hex) |
|---|---|
| 200 | c8 |
| 304 | 130 |
| 404 | 194 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | dectohex(status) as status_hex | first(status_hex) by status\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Output is lowercase hex (e.g., `c8` not `C8`).
- Use `hextodec` to reverse the conversion.
