# base64decode

Converts a base64-encoded string into its original ASCII or UTF-8 representation. Use `base64decode` to reverse base64 encoding found in log fields — for example, decoding encoded credentials, tokens, or payloads captured in application logs.

## Syntax

```
| base64decode(<base64String>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<base64String>` | Required | A base64-encoded string field or literal to decode. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Decode known base64-encoded HTTP method strings back to their original values.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| base64encode(method) as method_b64
| base64decode(method_b64) as method_decoded
| first(method_decoded) by method
```

**Expected output:**

| method | first(method_decoded) |
|---|---|
| GET | GET |
| POST | POST |
| HEAD | HEAD |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | base64encode(method) as method_b64 | base64decode(method_b64) as method_decoded | first(method_decoded) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Providing an invalid base64 string returns an error or empty result.
- Use paired with `base64encode` to round-trip values and verify encoding fidelity.
