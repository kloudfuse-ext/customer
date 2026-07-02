# and

Intersection operator (AND logic) between two search filter conditions. Selects only log lines that satisfy both conditions simultaneously. In regular search, AND is implied by writing two conditions side by side; in advanced search, write the keyword `and` explicitly.

## Syntax

**Regular search (implied AND):**
```fuseql
label1="value1" label2="value2"
```

**Advanced search:**
```fuseql
@facet1="value1" and @facet2="value2"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| left condition | Yes | A search filter expression on a label, facet, or term. |
| right condition | Yes | A second search filter expression that must also match. |

## Example

Filter nginx logs to show only `info`-level entries from the nginx source.

```fuseql
source="nginx" level="info" | count by kube_namespace
```

**Expected output:**

| kube_namespace | _count |
|---|---|
| kfuse | 13,277 |
| kfuse-ingress | 2,310,176 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" level=\\\"info\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- In regular search, placing two conditions side by side is equivalent to AND — no keyword is needed.
- In advanced search mode (using `@` for facets), use the lowercase keyword `and`.
- Parentheses can group compound expressions: `(source="nginx" and level="info") or source="nginx-error"`.
