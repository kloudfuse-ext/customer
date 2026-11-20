# and

Intersection operator (AND logic) between two search filter conditions. Selects only log lines that satisfy both conditions simultaneously. Write the keyword `and` between the conditions; it is required, and `AND` also works.

## Syntax

**Labels:**
```fuseql
label1="value1" and label2="value2"
```

**Facets:**
```fuseql
@facet1="value1" and @facet2="value2"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| left condition | Yes | A search filter expression on a label, facet, or term. |
| right condition | Yes | A second search filter expression that must also match. |

## Example

Count nginx logs at `info` level, grouped by namespace.

```fuseql
source="nginx" and level="info" | count by kube_namespace
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
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" and level=\\\"info\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Conditions are not combined implicitly. Writing two conditions side by side without `and`, such as `source="nginx" level="info"`, fails with `syntax error` in the Logs *Code* input and in aggregation queries (`getLogMetricsResultWithKfuseQl`). A raw log query (`getLogsWithFuseQlStream`) returns no rows and no error. Verified against Kloudfuse 4.4.0.
- Parentheses can group compound expressions: `(source="nginx" and level="info") or source="nginx-error"`.
