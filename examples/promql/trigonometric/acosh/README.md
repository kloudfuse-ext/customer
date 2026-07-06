# acosh

Computes the inverse hyperbolic cosine of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
acosh(<expr>)
```

## Example

Compute the inverse hyperbolic cosine of 2 — ≈ 1.317.

<!-- validation: kind=instant minutes=10 -->
```promql
acosh(vector(2))
```

**Expected output:**

| Value |
|---|
| 1.317 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=acosh(vector(2))' \
  --data-urlencode "time=$(date -u +%s)"
```
