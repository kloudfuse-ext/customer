# in

Checks whether a field value is a member of a specified set of strings or numbers. Use in a `where` clause to keep only matching rows, or inside `if` to branch on membership. The check is case-sensitive for string values.

## Syntax

**where form:**
```fuseql
| where in(<field>, <value1>[, <value2>, ...])
```

**if form:**
```fuseql
| if(in(<field>, <value1>[, <value2>, ...]), <value_if_true>, <value_if_false>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Yes | The field whose value is tested for membership. |
| `<value1>, ...` | Yes | One or more literal string or numeric values forming the allowed set. |
| `as <alias>` | Yes (if form) | Name for the output column when used with `if`. |

## Example

Filter nginx access logs to count only GET and POST requests.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| where in(method, "GET", "POST")
| count by method
```

**Expected output:**

| method | _count |
|---|---|
| GET | 3,091 |
| POST | 2,159,649 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | where in(method, \\\"GET\\\", \\\"POST\\\") | count by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `in` is preferred over chaining multiple `or` conditions when testing the same field against many values — it is more readable and compiles to the same plan.
- The check is case-sensitive; normalize with `toLowerCase` if needed.
- The `in` operator works in `where` clauses (filter rows) and `if` expressions (classify rows). It does not work as a standalone pipe stage producing an alias directly.
