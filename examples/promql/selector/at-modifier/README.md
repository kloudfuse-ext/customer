# At modifier (@)

Fixes the evaluation time of a selector to an absolute Unix timestamp, regardless of the query's own evaluation time. `@ start()` and `@ end()` pin to the boundaries of the query range — useful for showing a constant baseline across every step of a range query.

## Syntax

```
<metric>{<matchers>} @ <unix-seconds>    (also @ start(), @ end())
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<unix-seconds>` | Required | Absolute timestamp in Unix seconds, or the functions `start()` / `end()` for the query-range boundaries. |

## Example

Chart the ratio of the current Kloudfuse goroutine total to its value at the start of the query range — a drift indicator that always compares against the same baseline sample.

<!-- validation: kind=range_metric minutes=30 -->
```promql
sum(go_goroutines{app_kubernetes_io_instance="kfuse"})
/
sum(go_goroutines{app_kubernetes_io_instance="kfuse"} @ start())
```

**Expected output:**

| Value |
|---|
| 1.003 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(go_goroutines{app_kubernetes_io_instance="kfuse"}) / sum(go_goroutines{app_kubernetes_io_instance="kfuse"} @ start())' \
  --data-urlencode "start=$(date -u -v-30M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "step=60"
```

## Notes

- `@` and `offset` can be combined; order does not matter.
