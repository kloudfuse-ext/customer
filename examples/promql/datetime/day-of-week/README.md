# day_of_week

Returns the day of the week (0–6, sunday = 0), utc for each sample's timestamp. Called with no argument, it uses the query evaluation time. Date functions gate time-dependent alert rules — for example, suppressing a batch-job alert on weekends.

## Syntax

```
day_of_week([<vector of timestamps>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<vector>` | Optional | Timestamps to convert; defaults to the evaluation time. |

## Example

Return the current day of the week in UTC.

<!-- validation: kind=instant minutes=10 -->
```promql
day_of_week()
```

**Expected output:**

| Value |
|---|
| 6 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=day_of_week()' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- All date functions operate in UTC.
