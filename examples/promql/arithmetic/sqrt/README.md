# sqrt

Applies `sqrt` to every sample value of the input vector, preserving all labels. Square root of every sample.

## Syntax

```
sqrt(<expr>)
```

## Example

Compute the square root of 256 — the result is 16.

<!-- validation: kind=instant minutes=10 -->
```promql
sqrt(vector(256))
```

**Expected output:**

| Value |
|---|
| 16 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sqrt(vector(256))' \
  --data-urlencode "time=$(date -u +%s)"
```
