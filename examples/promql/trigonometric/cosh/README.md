# cosh

Computes the hyperbolic cosine of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
cosh(<expr>)
```

## Example

Compute the hyperbolic cosine of 1 — ≈ 1.543.

<!-- validation: kind=instant minutes=10 -->
```promql
cosh(vector(1))
```

**Expected output:**

| Value |
|---|
| 1.543 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=cosh(vector(1))' \
  --data-urlencode "time=$(date -u +%s)"
```
