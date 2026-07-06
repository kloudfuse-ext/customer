# exp

Applies `exp` to every sample value of the input vector, preserving all labels. e raised to each sample value.

## Syntax

```
exp(<expr>)
```

## Example

Compute e^1 — the result is Euler's number, ≈ 2.718.

<!-- validation: kind=instant minutes=10 -->
```promql
exp(vector(1))
```

**Expected output:**

| Value |
|---|
| 2.718 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=exp(vector(1))' \
  --data-urlencode "time=$(date -u +%s)"
```
