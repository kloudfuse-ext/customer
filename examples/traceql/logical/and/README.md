# And (&&)

Combines conditions so that a span matches only when every condition holds. This is the workhorse for narrowing a search: service plus operation, service plus latency, and so on.

## Syntax

```
{ <condition> && <condition> }
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<condition>` | Required | Any attribute or intrinsic comparison. |

## Example

Find the Python demo service's outbound client spans.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name = "demo-python-service" && kind = client}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-python-service | database | 50 ms |
| demo-python-service | database | 50 ms |
| demo-python-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name = "demo-python-service" && kind = client}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- Both conditions are evaluated against the same span. Cross-span (structural) matching is not supported: the Kloudfuse docs.
