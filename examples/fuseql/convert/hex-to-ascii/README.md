# hextoascii

Converts a hexadecimal string to its ASCII text representation by interpreting each pair of hex characters as a byte. Use `hextoascii` to decode hex-encoded payloads, tokens, or message bodies that appear in log fields as raw hex strings.

## Syntax

```
| hextoascii(<hexString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<hexString>` | Required | A hexadecimal string field or literal where each pair of characters represents one ASCII byte. |
| `<alias>` | Required | Name for the resulting ASCII string field. |

## Example

Decode a known hex-encoded string to verify the ASCII output.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| hextoascii("48656c6c6f") as decoded
| first(decoded) by method
```

**Expected output:**

| method | first(decoded) |
|---|---|
| GET | Hello |
| POST | Hello |

> `48656c6c6f` is the hex encoding of `Hello`.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | hextoascii(\\\"48656c6c6f\\\") as decoded | first(decoded) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The input must contain an even number of valid hex characters.
- Non-printable bytes may appear as replacement characters depending on the rendering context.
