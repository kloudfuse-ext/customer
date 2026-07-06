# vector

Returns the given scalar as a single series with no labels. Its main job is the fallback idiom `<query> or vector(0)`: when the query returns nothing — no errors logged, no lines matched — the result is an explicit 0 instead of an empty panel, which keeps dashboards and downstream arithmetic well-defined.

## Syntax

```
vector(<scalar>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<scalar>` | Required | The numeric value to return. |

## Example

Count log lines from a service that does not exist on this cluster. The count itself is empty, so the `or vector(0)` fallback supplies the 0.

<!-- validation: kind=instant minutes=10 -->
```logql
sum(count_over_time({source="payments-service"}[5m])) or vector(0)
```

**Expected output:**

| Value |
|---|
| 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(count_over_time({source="payments-service"}[5m])) or vector(0)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- The fallback series has no labels; if later stages match on labels, add them with `label_replace`.
