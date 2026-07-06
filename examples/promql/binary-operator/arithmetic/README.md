# Arithmetic operators

Combines two expressions — or an expression and a scalar — with `+`, `-`, `*`, `/`, `%`, or `^`. Between two vectors, series with identical label sets are matched pairwise; unmatched series drop out of the result.

## Syntax

```
<expr> <op> <expr>    where <op> is + - * / % ^
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expr>` | Required | A vector expression or scalar literal on either side. |

## Example

Compute each Kloudfuse query service's share of the group's total goroutines, as a percentage.

<!-- validation: kind=instant minutes=10 -->
```promql
  sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"})
/ on () group_left ()
  sum(go_goroutines{app_kubernetes_io_name=~".*query-service"})
* 100
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| trace-query-service | 3.342 |
| events-query-service | 3.296 |
| logs-query-service | 21.32 |
| rum-query-service | 1.438 |
| query-service | 70.6 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"}) / on () group_left () sum(go_goroutines{app_kubernetes_io_name=~".*query-service"}) * 100' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Division by zero produces no result for that series rather than an error.
- Standard precedence applies (`^` highest, then `* / %`, then `+ -`); parenthesize to override.
