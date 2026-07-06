# sinh

Computes the hyperbolic sine of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
sinh(<expr>)
```

## Example

Compute the hyperbolic sine of 1 — ≈ 1.175.

<!-- validation: kind=instant minutes=10 -->
```promql
sinh(vector(1))
```

**Expected output:**

| Value |
|---|
| 1.175 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sinh(vector(1))' \
  --data-urlencode "time=$(date -u +%s)"
```
