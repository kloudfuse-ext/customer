# scalar

Converts a vector containing exactly one series into a scalar, so its value can be used where PromQL requires a scalar argument. If the input has zero or multiple series, the result is `NaN`.

## Syntax

```
scalar(<single-series vector>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<vector>` | Required | An expression that yields exactly one series. |

## Example

Turn the total Kloudfuse goroutine count into a scalar and re-wrap it as a vector for display.

<!-- validation: kind=instant minutes=10 -->
```promql
vector(scalar(sum(go_goroutines{app_kubernetes_io_instance="kfuse"})))
```

**Expected output:**

| Value |
|---|
| 386,610 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=vector(scalar(sum(go_goroutines{app_kubernetes_io_instance="kfuse"})))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Prefer vector-to-vector arithmetic with `on () group_left` over `scalar()` when labels must be preserved.
