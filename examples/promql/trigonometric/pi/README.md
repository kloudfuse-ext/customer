# pi

Returns π as a scalar. Wrap it in `vector()` when a vector result is needed, or use it directly as a scalar argument.

## Syntax

```
pi()
```

## Example

Return π as a chartable vector.

<!-- validation: kind=instant minutes=10 -->
```promql
vector(pi())
```

**Expected output:**

| Value |
|---|
| 3.142 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=vector(pi())' \
  --data-urlencode "time=$(date -u +%s)"
```
