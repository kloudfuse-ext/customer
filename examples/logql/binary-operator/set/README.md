# Set operators (and, or, unless)

Combines two vectors as sets keyed by label values: `and` keeps left-side series that have a match on the right, `or` returns the left side plus unmatched right-side series, and `unless` keeps left-side series that have no match on the right. Values always come from the left side.

## Syntax

```
<expr> and <expr>  |  <expr> or <expr>  |  <expr> unless <expr>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expr>` | Required | Metric expressions on both sides; matching is by identical label sets. |

## Example

List Grafana's log levels excluding any level that also produced error-level lines — `unless` subtracts the right-hand set from the left.

<!-- validation: kind=instant minutes=10 -->
```logql
  sum by (level) (count_over_time({source="grafana"}[5m]))
unless
  sum by (level) (count_over_time({source="grafana", level="error"}[5m]))
```

**Expected output:**

| level | Value |
|---|---|
| debug | 9,778 |
| info | 98,609 |
| warn | 11 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (level) (count_over_time({source="grafana"}[5m])) unless sum by (level) (count_over_time({source="grafana", level="error"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- A common pattern is `<query> or vector(0)` to guarantee a result row even when the query matches nothing.
