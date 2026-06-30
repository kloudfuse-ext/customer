# tolowercase

Converts all letters of a string to lowercase. Use `tolowercase` to normalize fields before grouping or comparison — for example, ensuring that HTTP methods parsed from log lines are case-insensitively aggregated.

## Syntax

```
| tolowercase(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | A string field or literal to convert to lowercase. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Normalize the HTTP method field to lowercase and count log lines by lowercased method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| tolowercase(method) as method_lower
| count by method_lower
```

**Expected output:**

| method_lower | _count |
|---|---|
| get | 3,091 |
| post | 2,159,649 |
| head | 183 |

> Results are confirmed from a 5-minute nginx log window.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | tolowercase(method) as method_lower | count by method_lower\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Non-alphabetic characters (digits, punctuation) are unaffected.
- Equivalent to calling `toLowerCase` — FuseQL operator names are case-insensitive.
