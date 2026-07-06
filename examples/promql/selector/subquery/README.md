# Subquery ([1h:5m])

A subquery evaluates any instant expression repeatedly over a range, producing a range vector from computed values instead of raw samples. This lets range functions consume derived series — the max of a rate, the average of a sum — without creating a recording rule first.

## Syntax

```
<expression>[<range>:<resolution>]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The window to evaluate over. |
| `<resolution>` | Optional | Step between inner evaluations; defaults to the global evaluation interval. |

## Example

Find the highest total Kloudfuse goroutine count seen in the last hour, sampled every five minutes.

<!-- validation: kind=instant minutes=10 -->
```promql
max_over_time(sum(go_goroutines{app_kubernetes_io_instance="kfuse"})[1h:5m])
```

**Expected output:**

| Value |
|---|
| 385,840 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=max_over_time(sum(go_goroutines{app_kubernetes_io_instance="kfuse"})[1h:5m])' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Subqueries re-evaluate the inner expression at every resolution step — heavier than reading raw samples, so prefer a plain range vector when one suffices.
