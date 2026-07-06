# hour

Returns the hour of the day (0–23), utc for each sample's timestamp. Called with no argument, it uses the query evaluation time. Date functions gate time-dependent alert rules — for example, suppressing a batch-job alert on weekends.

## Syntax

```
hour([<vector of timestamps>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<vector>` | Optional | Timestamps to convert; defaults to the evaluation time. |

## Example

Return the current hour of the day in UTC.

<!-- validation: kind=instant minutes=10 -->
```promql
hour()
```

**Expected output:**

| Value |
|---|
| 19 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=hour()' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- All date functions operate in UTC.
