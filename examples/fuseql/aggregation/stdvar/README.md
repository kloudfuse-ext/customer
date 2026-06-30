# stdvar

Computes the variance of a numeric field across matched log lines. Variance is the square of the standard deviation and quantifies the spread of values around the mean. The very high variance for GET versus POST reflects the wide range of payload sizes returned by GET requests. Null or missing field values are ignored.

## Syntax

```fuseql
| stdvar(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to compute the variance of. Null or missing values are ignored. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_stdvar`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and compute the variance in response body size per HTTP method. The very high variance for GET versus POST reflects the wide range of payload sizes returned by GET requests.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| stdvar(bytes) as var_bytes by method
```

**Expected output:**

| method | var_bytes |
|---|---|
| GET | 1,149,810,367,291.90 |
| POST | 3,591,132.22 |
| OPTIONS | 4,761.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | stdvar(bytes) as var_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Variance squares the unit (bytes²), making the result difficult to interpret directly. Use `stddev` when you need a human-readable spread in the original unit.
- Use `stdvar` when you need to mathematically combine variance across groups (e.g. pooled variance calculations).
- For dashboards and alerts where you want a spread figure in the original unit, use `stddev` instead.
