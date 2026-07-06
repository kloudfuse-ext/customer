# rad

Converts every sample value of the input vector from degrees to radians, preserving all labels.

## Syntax

```
rad(<expr>)
```

## Example

Convert 180 degrees to radians — the result is π, ≈ 3.14159.

<!-- validation: kind=instant minutes=10 -->
```promql
rad(vector(180))
```

**Expected output:**

| Value |
|---|
| 3.142 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=rad(vector(180))' \
  --data-urlencode "time=$(date -u +%s)"
```
