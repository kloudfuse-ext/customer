# status

The span status set by the instrumentation: `ok`, `error`, or `unset`. `{ status = error }` is the standard entry point for failure investigation.

## Syntax

```
{ status = error }    (values: ok, error, unset)
```

## Example

The demo services do not set an explicit status, so their spans match `unset`.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*" && status = unset}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-python-service | database | 50 ms |
| demo-go-service | database | 50 ms |
| demo-java-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*" && status = unset}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- Status values are unquoted keywords, not strings.
