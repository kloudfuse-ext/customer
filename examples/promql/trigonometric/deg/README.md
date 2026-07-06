# deg

Converts every sample value of the input vector from radians to degrees, preserving all labels.

## Syntax

```
deg(<expr>)
```

## Example

Convert π radians to degrees — the result is 180.

<!-- validation: kind=instant minutes=10 -->
```promql
deg(vector(pi()))
```

**Expected output:**

| Value |
|---|
| 180 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=deg(vector(pi()))' \
  --data-urlencode "time=$(date -u +%s)"
```
