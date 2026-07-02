# !== (facet terms not exist)

Exact facet term exclusion operator. Selects log lines where a facet does not have a specific indexed term value. The logical complement of `==` (facet terms exist).

## Syntax

```fuseql
@facetName!=="value"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `@facetName` | Yes | The facet name, prefixed with `@`. |
| `"value"` | Yes | The indexed term value the facet must not contain. |

## Example

Return log lines where the `traceFlags` facet does not have the term value `1`.

```fuseql
source="nginx" @traceFlags!=="1" | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse | 13,277 |
| kfuse-ingress | ~2,309,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @traceFlags!==\\\"1\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `!==` is the term-exclusion counterpart to `==`. Behavior may differ from `!=` when the facet is tokenized into multiple terms.
- Lines where the facet is absent are also included in the results.
