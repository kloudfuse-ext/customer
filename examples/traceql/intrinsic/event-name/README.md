# event:name

Matches spans that carry a span event with the given name — most commonly `exception`, which OpenTelemetry SDKs attach when a span records an error. Link attributes use the `link:` scope the same way.

## Syntax

```
{ event:name = "<event>" }
```

## Example

Search for spans that recorded an exception event. The demo services never fail, so the result is empty — on production data this returns the failing spans.

<!-- validation: kind=search minutes=15 expect=empty -->
```traceql
{event:name = "exception"}
```

**Expected output:** no matching traces — the demo services emit no such data.

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={event:name = "exception"}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```
