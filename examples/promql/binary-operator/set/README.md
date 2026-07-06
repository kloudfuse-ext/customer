# Set operators (and, or, unless)

Combines two vectors as sets keyed by label values: `and` keeps left-side series with a match on the right, `or` returns the left plus unmatched right-side series, and `unless` keeps left-side series with no match on the right. Values come from the left side.

## Syntax

```
<expr> and <expr>  |  <expr> or <expr>  |  <expr> unless <expr>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expr>` | Required | Vector expressions on both sides; matching is by identical label sets. |

## Example

List Kloudfuse services' goroutine counts, excluding services that are currently above 500 — `unless` subtracts the right-hand set.

<!-- validation: kind=instant minutes=10 -->
```promql
  sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"})
unless
  sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"}) > 500
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| recorder | 14 |
| archive-writer | 103 |
| analytics-service | 11 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"}) unless sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"}) > 500' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `<query> or vector(0)` is the standard fallback idiom for guaranteeing a result row.
