# sin

Computes the sine of every sample value of the input vector, preserving all labels. Angles are in radians; convert with `rad()` and `deg()`.

## Syntax

```
sin(<expr>)
```

## Example

Compute the sine of 30 degrees — the result is 0.5.

<!-- validation: kind=instant minutes=10 -->
```promql
sin(rad(vector(30)))
```

**Expected output:**

| Value |
|---|
| 0.5 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sin(rad(vector(30)))' \
  --data-urlencode "time=$(date -u +%s)"
```
