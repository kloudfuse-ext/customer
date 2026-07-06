# Comparison operators

Compares values with `==`, `!=`, `>`, `>=`, `<`, or `<=`. Against a scalar the comparison filters: series that fail the test are dropped — exactly the shape an alert condition needs. The `bool` modifier keeps every series and returns 1 or 0 instead.

## Syntax

```
<expr> > <scalar>    (also ==, !=, >=, <, <=; add bool for 0/1)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<scalar>` | Required | The threshold, or another vector for pairwise comparison. |
| `bool` | Optional | Return 1/0 per series instead of filtering: `> bool 100`. |

## Example

Keep only the Kloudfuse services currently running more than 100 goroutines.

<!-- validation: kind=instant minutes=10 -->
```promql
sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"})
> 100
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| zapper | 2,566 |
| kfuse-redis | 584 |
| az-service | 1,009 |
| logs-query-service | 19,306 |
| query-service | 64,236 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"}) > 100' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Alert rules use this form directly: the alert fires while the filtered result is non-empty.
