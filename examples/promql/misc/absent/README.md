# absent

Returns a single series with value 1 when the given selector matches nothing, and returns nothing when series exist. This inversion powers absence alerting: a target that stopped reporting produces no series for a normal rule to fire on.

## Syntax

```
absent(<vector expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<vector expression>` | Required | The selector expected to match series. |

## Example

Check for a metric that does not exist on this cluster — `absent` returns 1, the signal an alert would fire on.

<!-- validation: kind=instant minutes=10 -->
```promql
absent(nonexistent_demo_metric{app_kubernetes_io_instance="kfuse"})
```

**Expected output:**

| app_kubernetes_io_instance | Value |
|---|---|
| kfuse | 1 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=absent(nonexistent_demo_metric{app_kubernetes_io_instance="kfuse"})' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Equality matchers from the selector are carried into the result labels, so the alert knows what went missing.
- For absence over a window rather than one instant, use `absent_over_time`.
