# isblank

Checks whether a string value is null, empty, or contains only whitespace characters (spaces, tabs, newlines). Returns `true` for all three cases; returns `false` for any string that contains at least one non-whitespace character.

## Syntax

```fuseql
| isblank(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Yes | A string field or literal to test. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Check whether the `url` field extracted from nginx access logs is blank.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| isblank(url) as url_blank
| count by url_blank
```

**Expected output:**

| url_blank | _count |
|---|---|
| False | 2,162,923 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | isblank(url) as url_blank | count by url_blank\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `isblank` is a superset of `isempty`: blank includes empty, but also catches whitespace-only strings.
- Prefer `isblank` over `isempty` when your data may contain whitespace-only placeholder values from upstream systems.
- Use `| where isblank(field)` to filter rows with missing values, or `| where not isblank(field)` to keep only populated rows.
