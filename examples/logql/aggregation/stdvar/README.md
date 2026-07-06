# stdvar

Computes the population variance of the input series values — the square of `stddev` — per group when `by (...)` is given.

## Syntax

```
stdvar by (<labels>) (<metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keeps only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Groups by every label except the listed ones. |

## Example

Compute the variance of per-stream log counts across Grafana's streams in the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
stdvar(count_over_time({source="grafana"}[5m]))
```

**Expected output:**

| Value |
|---|
| 14,372,873.41 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=stdvar(count_over_time({source="grafana"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- For a value in the same unit as the inputs, use `stddev`.
