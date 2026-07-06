# Offset modifier (offset)

Shifts the evaluation time of a single selector into the past. `offset` is the tool for same-query time comparison: this hour's value next to yesterday's, this week against last week.

## Syntax

```
<metric>{<matchers>} offset <duration>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<duration>` | Required | How far back to shift, such as `1h`, `1d`, or `1w`. Must immediately follow the selector. |

## Example

Compare the current total goroutine count of Kloudfuse services against one hour ago — a value near 1.0 means no change.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(go_goroutines{app_kubernetes_io_instance="kfuse"})
/
sum(go_goroutines{app_kubernetes_io_instance="kfuse"} offset 1h)
```

**Expected output:**

| Value |
|---|
| 0.9839 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(go_goroutines{app_kubernetes_io_instance="kfuse"}) / sum(go_goroutines{app_kubernetes_io_instance="kfuse"} offset 1h)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `offset` binds to its selector, not to the whole expression — each selector that should look back needs its own `offset`.
