# format

Returns a formatted string by substituting fields or literals into a format specifier string. Use `format` when you need to produce human-readable summaries or labels from multiple fields. Supports standard `printf`-style `%s` (string) and `%d` (integer) specifiers.

## Syntax

```
| format(<formatSpecifierString>, <field1>, ...) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<formatSpecifierString>` | Required | A string containing `%s` or `%d` placeholders, replaced in order by the subsequent arguments. |
| `<field1>, ...` | Required | One or more fields or literals to substitute into the format string. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Build a summary sentence combining the HTTP method and status code, then return the first example per method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| format("%s returned %s", method, status) as summary
| first(summary) by method
```

**Expected output:**

| method | first(summary) |
|---|---|
| GET | GET returned 200 |
| POST | POST returned 200 |
| HEAD | HEAD returned 200 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | format(\\\"%%s returned %%s\\\", method, status) as summary | first(summary) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Use `%s` for string fields and `%d` for integer fields in the format specifier.
- Arguments are substituted left-to-right in the order they appear after the format string.
