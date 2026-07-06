# time

Returns the evaluation timestamp of the query in Unix seconds, as a scalar. The standard building block for age calculations: `time() - <timestamp metric>` gives seconds since an event.

## Syntax

```
time()
```

## Example

Return the evaluation time as a chartable vector.

<!-- validation: kind=instant minutes=10 -->
```promql
vector(time())
```

**Expected output:**

| Value |
|---|
| 1,783,194,966 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=vector(time())' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `time()` is a scalar; wrap it in `vector()` to chart it or compare it against vectors.
