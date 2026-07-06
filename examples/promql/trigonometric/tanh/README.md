# tanh

Computes the hyperbolic tangent of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
tanh(<expr>)
```

## Example

Compute the hyperbolic tangent of 1 — ≈ 0.762.

<!-- validation: kind=instant minutes=10 -->
```promql
tanh(vector(1))
```

**Expected output:**

| Value |
|---|
| 0.7616 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=tanh(vector(1))' \
  --data-urlencode "time=$(date -u +%s)"
```
