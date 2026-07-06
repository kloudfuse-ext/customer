# atanh

Computes the inverse hyperbolic tangent of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
atanh(<expr>)
```

## Example

Compute the inverse hyperbolic tangent of 0.5 — ≈ 0.549.

<!-- validation: kind=instant minutes=10 -->
```promql
atanh(vector(0.5))
```

**Expected output:**

| Value |
|---|
| 0.5493 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=atanh(vector(0.5))' \
  --data-urlencode "time=$(date -u +%s)"
```
