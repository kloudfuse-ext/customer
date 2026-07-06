# bottomk

Returns the `k` input series with the smallest values, keeping their labels. The quiet outliers are often as interesting as the noisy ones.

## Syntax

```
bottomk(<k>, <expr>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<k>` | Required | How many series to return. |

## Example

Find the two Kloudfuse services running the fewest goroutines.

<!-- validation: kind=instant minutes=10 -->
```promql
bottomk(2, sum by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_instance="kfuse"}
))
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| analytics-service | 11 |
| recorder | 14 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=bottomk(2, sum by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_instance="kfuse"} ))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `bottomk` ranks only series that exist; detect fully missing series with `absent`.
