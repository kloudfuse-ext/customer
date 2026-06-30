# concat

Concatenates two or more strings (or numbers coerced to strings) into a single string. Use `concat` whenever you need to build composite fields — for example, combining an HTTP method and status code into a single label for grouping or display.

## Syntax

```
| concat(<field1>, <field2>, ...) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field1>, <field2>, ...` | Required | Two or more string or numeric fields or literals to join, in order. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Combine the HTTP method and status code into a single `method_status` label, then count how often each combination appears.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| concat(method, " ", status) as method_status
| count by method_status
```

**Expected output:**

| method_status | _count |
|---|---|
| POST 200 | 2,159,442 |
| GET 200 | 2,891 |
| GET 304 | 198 |
| HEAD 200 | 183 |

> Values shown are confirmed from a 5-minute nginx log window.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | concat(method, \\\" \\\", status) as method_status | count by method_status\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Accepts any number of arguments (two or more).
- Numeric arguments are automatically coerced to strings before concatenation.
- Use a literal space `" "` as a separator argument to add spacing between fields.
