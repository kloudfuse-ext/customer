# asin

Computes the arcsine of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
asin(<expr>)
```

## Example

Find the angle whose sine is 0.5 — the result is 30 degrees.

<!-- validation: kind=instant minutes=10 -->
```promql
deg(asin(vector(0.5)))
```

**Expected output:**

| Value |
|---|
| 30 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=deg(asin(vector(0.5)))' \
  --data-urlencode "time=$(date -u +%s)"
```
