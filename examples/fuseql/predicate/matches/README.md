# matches

Tests whether a field value matches a RE2-compliant regular expression. Use in a `where` clause to filter log lines, or inside `if` to branch on pattern matches.

## Syntax

**where form:**
```fuseql
| where matches(<field>, "<regex>")
```

**if form:**
```fuseql
| if(matches(<field>, "<regex>"), <value_if_true>, <value_if_false>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Yes | The field whose value is tested against the pattern. |
| `"<regex>"` | Yes | A RE2-compliant regular expression string. |
| `as <alias>` | Yes (if form) | Name for the output column when used with `if`. |

## Example

Filter nginx access logs to count only requests to health-check endpoints.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| where matches(url, ".*health.*")
| count by method
```

**Expected output (illustrative):**

| method | _count |
|---|---|
| GET | ~180 |
| POST | ~12 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | where matches(url, \\\".*health.*\\\") | count by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- FuseQL uses RE2 syntax — look-ahead and look-behind assertions are not supported.
- `matches` works in `where` clauses and `if` expressions. It returns a syntax error when used as a standalone pipe stage producing an alias directly (`| matches(field, regex) as alias`).
- For simple substring checks, a `where` clause with a `contains` field expression may be faster. Use `matches` when you need anchoring (`^`, `$`) or character classes.
