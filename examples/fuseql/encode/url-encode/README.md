# urlencode

Percent-encodes a string so that special characters are replaced with their `%XX` ASCII equivalents, making the string safe for use in a URL. Use `urlencode` to sanitize field values before embedding them in URLs or query strings.

## Syntax

```
| urlencode(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | A string field or literal to percent-encode. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Percent-encode the parsed URL field (which includes spaces and slashes in the protocol token) and return the first encoded value per method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| urlencode(url) as url_encoded
| first(url_encoded) by method
```

**Expected output:**

| method | first(url_encoded) |
|---|---|
| GET | /ingester/health/%20HTTP%2F2.0 |
| POST | /ingester/otlp/v1/logs%20HTTP%2F2.0 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | urlencode(url) as url_encoded | first(url_encoded) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Spaces are encoded as `%20` and forward slashes as `%2F`.
- Use `urldecode` to reverse the encoding.
