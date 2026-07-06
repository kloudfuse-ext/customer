# vector

Returns the given scalar as a vector with one series and no labels. Its main use is the fallback idiom `<query> or vector(0)`, which turns an empty result into an explicit zero so dashboards and downstream arithmetic stay well-defined.

## Syntax

```
vector(<scalar>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<scalar>` | Required | The value to return. |

## Example

Count series of a metric that does not exist; the count is empty, so `or vector(0)` supplies the zero.

<!-- validation: kind=instant minutes=10 -->
```promql
count(nonexistent_demo_metric) or vector(0)
```

**Expected output:**

| Value |
|---|
| 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=count(nonexistent_demo_metric) or vector(0)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- The fallback series has no labels; add them with `label_replace` if later stages match on labels.
