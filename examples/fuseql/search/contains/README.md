# ** (contains)

Substring match filter operator. Selects log lines where a label or facet value contains the specified string anywhere within it. Case-sensitive.

## Syntax

```fuseql
label**"substring"
@facet**"substring"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `label` or `@facet` | Yes | The label or facet name to match against. |
| `"substring"` | Yes | The string that must appear anywhere in the field value. |

## Example

Return logs from deployments whose name contains `ingress-ingress`.

```fuseql
source="nginx" kube_deployment**"ingress-ingress" | count by kube_deployment
```

**Expected output:**

| kube_deployment | _count |
|---|---|
| kfuse-ingress-ingress-nginx-controller | 316,505 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" kube_deployment**\\\"ingress-ingress\\\" | count by kube_deployment\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `**` is case-sensitive. For case-insensitive substring matching, use the regex operator: `label=~"(?i)substring"`.
- For prefix matching use `*~`; for suffix matching use `~*`; for exact matching use `=`.
- `**` is more readable than a wildcard regex for plain literal substring checks.
