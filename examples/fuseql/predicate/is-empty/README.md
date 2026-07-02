# isempty

Checks whether a string value is exactly an empty string — zero characters, no content, no whitespace. Returns `true` only for `""`; returns `false` for whitespace-only strings, null, or any non-empty string.

## Syntax

```fuseql
| isempty(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Yes | A string field or literal to test. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Check whether the `url` field extracted from nginx access logs is empty.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| isempty(url) as url_empty
| count by url_empty
```

**Expected output:**

| url_empty | _count |
|---|---|
| False | 2,162,923 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | isempty(url) as url_empty | count by url_empty\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `isempty` returns `false` for strings containing only spaces — use `isblank` to also catch whitespace-only values.
- Use `| where isempty(field)` to filter rows where a parse produced no value for a field.
- Use `| where not isempty(field)` to keep only rows where the field was populated.
