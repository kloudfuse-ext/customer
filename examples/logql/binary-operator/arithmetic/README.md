# Arithmetic operators

Combines two metric expressions — or an expression and a scalar — with `+`, `-`, `*`, `/`, `%`, or `^`. Between two vectors, series with identical label sets are matched and the operation applies to each pair; unmatched series are dropped. The classic use is a ratio: errors divided by totals.

## Syntax

```
<expr> <op> <expr>    where <op> is + - * / % ^
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expr>` | Required | A metric expression or a scalar literal on either side. |

## Example

Compute Grafana's error-log percentage: error lines divided by all lines, times 100. Both sides group `by (source)` so their label sets match.

<!-- validation: kind=instant minutes=10 -->
```logql
  sum by (source) (count_over_time({source="grafana", level="error"}[5m]))
/
  sum by (source) (count_over_time({source="grafana"}[5m]))
* 100
```

**Expected output:**

| source | Value |
|---|---|
| grafana | 41.55 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (source) (count_over_time({source="grafana", level="error"}[5m])) / sum by (source) (count_over_time({source="grafana"}[5m])) * 100' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Division by zero yields no result for that series rather than an error.
- Precedence follows arithmetic convention (`^` highest, then `* / %`, then `+ -`); parenthesize to override.
