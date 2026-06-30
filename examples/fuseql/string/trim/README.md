# trim

Removes leading and trailing whitespace characters from a string. Use `trim` to clean up fields that may contain incidental spaces introduced during parsing — for example, stripping whitespace from values extracted with `parse` before grouping or comparison.

## Syntax

```
| trim(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | A string field or literal from which to remove leading and trailing whitespace. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Trim any leading or trailing whitespace from parsed URL fields, then return the first cleaned URL per method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| trim(url) as url_trimmed
| first(url_trimmed) by method
```

**Expected output:**

| method | first(url_trimmed) |
|---|---|
| GET | /ingester/health/ HTTP/2.0 |
| POST | /ingester/otlp/v1/logs HTTP/2.0 |
| HEAD | /ingester/health/ HTTP/2.0 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | trim(url) as url_trimmed | first(url_trimmed) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Only leading and trailing whitespace is removed — internal spaces within the string are preserved.
- Whitespace includes spaces, tabs, and newline characters.
