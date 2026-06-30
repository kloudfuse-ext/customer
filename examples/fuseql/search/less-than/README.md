# < (less than)

Numeric comparison filter operator. Selects log lines where a numeric facet value is strictly less than the specified number. The boundary value is excluded.

## Syntax

```fuseql
@facetName<number
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `@facetName` | Yes | A numeric facet name, prefixed with `@`. |
| `number` | Yes | The exclusive upper bound; only values strictly below this are returned. |

## Example

Return nginx logs for requests that completed quickly (response time less than 100 ms).

```fuseql
source="nginx" @duration_ms<100 | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse-ingress | ~1,800,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @duration_ms<100 | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The boundary value is excluded — use `<=` to include it.
- Combine with `>` to create exclusive ranges: `@duration_ms>50 and @duration_ms<100`.
