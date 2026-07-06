# acos

Computes the arccosine of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
acos(<expr>)
```

## Example

Find the angle whose cosine is 0.5 — the result is 60 degrees.

<!-- validation: kind=instant minutes=10 -->
```promql
deg(acos(vector(0.5)))
```

**Expected output:**

| Value |
|---|
| 60 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=deg(acos(vector(0.5)))' \
  --data-urlencode "time=$(date -u +%s)"
```
