# name

The operation name of the span, as set by the instrumentation — an HTTP route, database statement type, or logical step name. Supports all string comparisons including regex.

## Syntax

```
{ name = "<operation>" }
```

## Example

Find the demo services' child operation, `user`.

<!-- validation: kind=search minutes=15 -->
```traceql
{name = "user"}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-go-service | database | 50 ms |
| demo-python-service | database | 50 ms |
| demo-java-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={name = "user"}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```
