# touppercase

Converts all letters of a string to uppercase. Use `touppercase` to normalize fields for display or comparison — for example, ensuring that parsed string values appear in a consistent uppercase form in dashboards or alert messages.

## Syntax

```
| touppercase(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | A string field or literal to convert to uppercase. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Normalize the HTTP method field to uppercase and count log lines by uppercased method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| touppercase(method) as method_upper
| count by method_upper
```

**Expected output:**

| method_upper | _count |
|---|---|
| GET | 3,091 |
| POST | 2,159,649 |
| HEAD | 183 |

> Results are confirmed from a 5-minute nginx log window.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | touppercase(method) as method_upper | count by method_upper\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Non-alphabetic characters (digits, punctuation) are unaffected.
- For case-insensitive grouping, `tolowercase` and `touppercase` produce equivalent results.
