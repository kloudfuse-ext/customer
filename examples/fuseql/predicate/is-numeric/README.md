# isnumeric

Checks whether a string value can be successfully parsed as a number (integer or floating-point). Returns `true` for valid numeric strings, `false` otherwise.

## Syntax

```fuseql
| isnumeric(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Yes | A string field or literal to test. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Verify that the `bytes` field parsed from nginx access logs is always numeric before using it in arithmetic aggregations.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| isnumeric(bytes) as bytes_numeric
| count by bytes_numeric
```

**Expected output:**

| bytes_numeric | _count |
|---|---|
| True | 2,162,923 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | isnumeric(bytes) as bytes_numeric | count by bytes_numeric\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Use `isnumeric` as a guard before applying `sum`, `avg`, `max`, or other numeric aggregations to parsed fields.
- If any rows return `False`, add `| where bytes_numeric` before aggregating to avoid type errors.
- Both integers (`"123"`) and floats (`"1.234"`) return `true`; strings like `"abc"` or `""` return `false`.
