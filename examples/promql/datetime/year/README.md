# year

Returns the year, utc for each sample's timestamp. Called with no argument, it uses the query evaluation time. Date functions gate time-dependent alert rules — for example, suppressing a batch-job alert on weekends.

## Syntax

```
year([<vector of timestamps>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<vector>` | Optional | Timestamps to convert; defaults to the evaluation time. |

## Example

Return the current year, utc in UTC.

<!-- validation: kind=instant minutes=10 -->
```promql
year()
```

**Expected output:**

| Value |
|---|
| 2,026 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=year()' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- All date functions operate in UTC.
