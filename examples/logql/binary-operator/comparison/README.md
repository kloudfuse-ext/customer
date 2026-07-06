# Comparison operators

Compares metric values with `==`, `!=`, `>`, `>=`, `<`, or `<=`. Against a scalar, the comparison acts as a filter: series that fail the test are dropped, which is exactly the shape an alert condition needs. Add the `bool` modifier to keep every series and return 1 or 0 instead.

## Syntax

```
<expr> > <scalar>    (also ==, !=, >=, <, <=; add bool to return 0/1)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<scalar>` | Required | The threshold to compare against (or another vector for pairwise comparison). |
| `bool` | Optional | Returns 1/0 per series instead of filtering, as in `> bool 100`. |

## Example

Keep only the Grafana log levels that produced more than 100 lines in the last five minutes — quieter levels drop out of the result.

<!-- validation: kind=instant minutes=10 -->
```logql
sum by (level) (count_over_time({source="grafana"}[5m])) > 100
```

**Expected output:**

| level | Value |
|---|---|
| debug | 9,461 |
| error | 75,432 |
| info | 94,655 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (level) (count_over_time({source="grafana"}[5m])) > 100' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Alert rules are typically written in this form: the alert fires while the filtered result is non-empty.
