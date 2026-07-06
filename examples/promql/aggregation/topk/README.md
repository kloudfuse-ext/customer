# topk

Returns the `k` input series with the largest values, keeping their labels — ranking questions answered directly.

## Syntax

```
topk(<k>, <expr>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<k>` | Required | How many series to return. |

## Example

Rank the three Kloudfuse services running the most goroutines.

<!-- validation: kind=instant minutes=10 -->
```promql
topk(3, sum by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_instance="kfuse"}
))
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| ingester | 100,406 |
| trace-transformer | 96,123 |
| query-service | 64,244 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=topk(3, sum by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_instance="kfuse"} ))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- In range queries the top set is re-evaluated at every step, so membership can change over time.
