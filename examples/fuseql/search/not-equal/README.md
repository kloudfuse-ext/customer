# != (not equal)

Exact-exclusion filter operator. Selects log lines where a label or facet does not equal the specified value. Case-sensitive.

## Syntax

```fuseql
label!="value"
@facetName!="value"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `label` or `@facetName` | Yes | The label key or (with `@` prefix) facet name to filter on. |
| `"value"` | Yes | The exact string value the field must not equal. |

## Example

Return all nginx logs except those at the `info` level.

```fuseql
source="nginx" level!="info" | count by level
```

**Expected output (illustrative):**

| level | _count |
|---|---|
| warning | ~1,200 |
| error | ~450 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" level!=\\\"info\\\" | count by level\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `!=` is the exact-exclusion counterpart to `=`.
- For excluding pattern matches, use `!~` (not regex).
- Combining `!=` conditions for the same field produces AND logic — to exclude multiple values, chain multiple `!=` conditions.
