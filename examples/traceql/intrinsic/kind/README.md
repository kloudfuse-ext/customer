# kind

The span kind assigned by the instrumentation: `server`, `client`, `producer`, `consumer`, or `internal`. Use it to separate inbound handling from outbound calls within the same service.

## Syntax

```
{ kind = server }    (values: server, client, producer, consumer, internal)
```

## Example

Find the demo services' inbound (server) spans — the `database` root spans.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*" && kind = server}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-python-service | database | 50 ms |
| demo-java-service | database | 50 ms |
| demo-python-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*" && kind = server}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- Kind values are unquoted keywords. The attribute form `.span_kind = "SPAN_KIND_SERVER"` also works on Kloudfuse.
