# bottomk

Returns the `k` input series with the smallest values, keeping their labels. Use it to find the quiet outliers — services logging suspiciously little are often as interesting as the noisy ones.

## Syntax

```
bottomk(<k>, <metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<k>` | Required | How many series to return. |

## Example

Find the two quietest of these five sources by log volume over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
bottomk(2, sum by (source) (
  count_over_time({source=~"zookeeper|kafka|busybox|filebeat|catalog-service"}[5m])
))
```

**Expected output:**

| source | Value |
|---|---|
| catalog-service | 92 |
| filebeat | 9 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=bottomk(2, sum by (source) ( count_over_time({source=~"zookeeper|kafka|busybox|filebeat|catalog-service"}[5m]) ))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `bottomk` only ranks series that exist; a service logging nothing at all produces no series — detect that with `absent_over_time`.
