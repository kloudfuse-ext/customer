# or

Union operator (OR logic) between two search filter conditions. Selects log lines that satisfy at least one of the conditions. In regular search, express OR using a quoted `OR` inside a field value; in advanced search, write the keyword `or` between two full expressions.

## Syntax

**Regular search:**
```fuseql
label="valueA OR valueB"
```

**Advanced search:**
```fuseql
@facet="valueA" or @facet="valueB"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| left condition | Yes | A search filter expression on a label, facet, or term. |
| right condition | Yes | A second search filter expression; at least one must match. |

## Example

Return log lines from the nginx source (regular search OR example).

```fuseql
source="nginx" level="info OR warning" | count by level
```

**Expected output (illustrative):**

| level | _count |
|---|---|
| info | 316,858 |
| warning | ~1,200 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" level=\\\"info OR warning\\\" | count by level\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- In regular search, the `OR` keyword must appear inside the quoted value string: `level="info OR warning"`.
- In advanced search, use lowercase `or` between two `@facet` expressions: `@level="info" or @level="warning"`.
- Use parentheses to control precedence when mixing `or` with `and`.
