# bytes_rate

Computes the per-second byte throughput of each stream in the range window — `bytes_over_time` divided by the window length. Use it to compare logging bandwidth across sources or to alert on sudden surges in log volume.

## Syntax

```
bytes_rate({<selector>} [<pipeline>] [<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<selector>` | Required | Stream selector, optionally followed by a filter/parser pipeline. |
| `<range>` | Required | The window to compute the rate over, such as `[1m]` or `[5m]`. |

## Example

Measure the Kafka brokers' current logging bandwidth in bytes per second, averaged over five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
sum(bytes_rate({source="kafka"}[5m]))
```

**Expected output:**

| Value |
|---|
| 3,564.21 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(bytes_rate({source="kafka"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Pair with `topk` to rank the noisiest sources: `topk(5, sum by (source) (bytes_rate({source=~".+"}[5m])))`.
