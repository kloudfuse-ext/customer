# base64encode

Converts an ASCII or UTF-8 string to its base64-encoded representation. Use `base64encode` to safely encode binary or special-character data for transport or storage.

## Syntax

```
| base64encode(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | A string field or literal to encode as base64. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Encode the HTTP method field and count unique encoded values.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| base64encode(method) as method_b64
| count by method_b64
```

**Expected output:**

| method_b64 | decoded (reference) | _count |
|---|---|---|
| R0VU | GET | 3,091 |
| UE9TVA== | POST | 2,159,649 |
| SEVBRA== | HEAD | 183 |

> Results are confirmed from a 5-minute nginx log window. The decoded column is shown for reference only.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | base64encode(method) as method_b64 | count by method_b64\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Encodes ASCII and UTF-8 strings to standard base64 (RFC 4648).
- Use `base64decode` to reverse the encoding.
