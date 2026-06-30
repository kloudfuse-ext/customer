# urldecode

Decodes a percent-encoded URL string by replacing `%XX` escape sequences with their original characters. Use `urldecode` when log fields contain percent-encoded URLs or query parameters that need to be read in plain text for analysis or grouping.

## Syntax

```
| urldecode(<urlString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<urlString>` | Required | A percent-encoded string field or literal to decode. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Decode a percent-encoded URL back to its plain-text form.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| urlencode(url) as url_encoded
| urldecode(url_encoded) as url_decoded
| first(url_decoded) by method
```

**Expected output:**

| method | first(url_decoded) |
|---|---|
| GET | /ingester/health/ HTTP/2.0 |
| POST | /ingester/otlp/v1/logs HTTP/2.0 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | urlencode(url) as url_encoded | urldecode(url_encoded) as url_decoded | first(url_decoded) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- A string that is not percent-encoded is returned unchanged.
- Use `urlencode` to encode a plain string before passing to `urldecode`.
