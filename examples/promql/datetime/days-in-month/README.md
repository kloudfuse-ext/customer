# days_in_month

Returns the number of days in the month (28–31), utc for each sample's timestamp. Called with no argument, it uses the query evaluation time. Date functions gate time-dependent alert rules — for example, suppressing a batch-job alert on weekends.

## Syntax

```
days_in_month([<vector of timestamps>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<vector>` | Optional | Timestamps to convert; defaults to the evaluation time. |

## Example

Return the current number of days in the month in UTC.

<!-- validation: kind=instant minutes=10 -->
```promql
days_in_month()
```

**Expected output:**

| Value |
|---|
| 31 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=days_in_month()' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- All date functions operate in UTC.
