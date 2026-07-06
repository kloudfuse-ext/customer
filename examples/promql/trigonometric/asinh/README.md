# asinh

Computes the inverse hyperbolic sine of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
asinh(<expr>)
```

## Example

Compute the inverse hyperbolic sine of 1 — ≈ 0.881.

<!-- validation: kind=instant minutes=10 -->
```promql
asinh(vector(1))
```

**Expected output:**

| Value |
|---|
| 0.8814 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=asinh(vector(1))' \
  --data-urlencode "time=$(date -u +%s)"
```
