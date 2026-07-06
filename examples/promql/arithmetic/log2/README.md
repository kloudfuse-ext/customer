# log2

Applies `log2` to every sample value of the input vector, preserving all labels. Base-2 logarithm of every sample.

## Syntax

```
log2(<expr>)
```

## Example

Compute log2(1024) — the result is 10.

<!-- validation: kind=instant minutes=10 -->
```promql
log2(vector(1024))
```

**Expected output:**

| Value |
|---|
| 10 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=log2(vector(1024))' \
  --data-urlencode "time=$(date -u +%s)"
```
