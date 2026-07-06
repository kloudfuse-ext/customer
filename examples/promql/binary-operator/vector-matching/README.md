# Vector matching (on, ignoring, group_left)

By default a binary operator matches series whose full label sets are identical. `on (labels)` restricts matching to the listed labels; `ignoring (labels)` matches on everything else. When one side has fewer series, `group_left` / `group_right` declare the many-to-one direction and can copy labels from the one side.

## Syntax

```
<expr> <op> on (<labels>) [group_left [(<labels>)]] <expr>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `on (<labels>)` | Optional | Match series using only these labels. |
| `ignoring (<labels>)` | Optional | Match series using all labels except these. |
| `group_left / group_right` | Optional | Allow many-to-one matching; the side named by the modifier is the many side. |

## Example

Divide each service's goroutine count by the all-service total: `on ()` matches every left series to the single right-side series, and `group_left ()` permits the many-to-one pairing.

<!-- validation: kind=instant minutes=10 -->
```promql
  sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"})
/ on () group_left ()
  sum(go_goroutines{app_kubernetes_io_instance="kfuse"})
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| logs-transformer | 0.00696586 |
| recorder | 3.63482e-05 |
| trace-transformer | 0.2496 |
| hydration-service | 0.00142796 |
| ingress-nginx | 0.01019 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"}) / on () group_left () sum(go_goroutines{app_kubernetes_io_instance="kfuse"})' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Without `group_left`, a many-to-one match is an error — PromQL makes the direction explicit on purpose.
