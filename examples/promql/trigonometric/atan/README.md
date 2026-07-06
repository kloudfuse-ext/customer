# atan

Computes the arctangent of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
atan(<expr>)
```

## Example

Find the angle whose tangent is 1 — the result is 45 degrees.

<!-- validation: kind=instant minutes=10 -->
```promql
deg(atan(vector(1)))
```

**Expected output:**

| Value |
|---|
| 45 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=deg(atan(vector(1)))' \
  --data-urlencode "time=$(date -u +%s)"
```
