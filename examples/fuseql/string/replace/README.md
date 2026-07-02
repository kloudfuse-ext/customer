# replace

Replaces all occurrences of a search string or regular expression pattern within a source string. Use `replace` to normalize field values — for example, stripping version tokens from URLs or redacting numeric IDs before grouping.

## Syntax

```
| replace(<sourceString>, <searchString>, <replaceString>) as <alias>

| replace(<sourceString>, <regexPattern>, <replaceString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<sourceString>` | Required | The string field or literal to search within. |
| `<searchString>` or `<regexPattern>` | Required | The literal string or regex pattern to find. All occurrences are replaced. |
| `<replaceString>` | Required | The string to substitute for each match. Use `""` to delete matches. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Replace the protocol version token `HTTP/2.0` with the shorthand `h2` in URL fields, then return the first normalized URL per method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| replace(url, "HTTP/2.0", "h2") as url2
| first(url2) by method
```

**Expected output:**

| method | first(url2) |
|---|---|
| GET | /ingester/health/ h2 |
| POST | /ingester/otlp/v1/logs HTTP/1.1 |
| HEAD | /ingester/health/ h2 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | replace(url, \\\"HTTP/2.0\\\", \\\"h2\\\") as url2 | first(url2) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Both literal strings and regex patterns are supported as the search argument.
- Use an empty string `""` as the replacement to delete matched text.
- All occurrences within the field are replaced, not just the first.
