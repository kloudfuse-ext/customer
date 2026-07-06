# select

Requests additional attributes or intrinsics in the returned span sets, so the values appear in the search results without opening each trace.

## Syntax

```
{ <conditions> } | select(<field>, <field>, ...)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | One or more attributes (`.service_name`) or intrinsics (`name`) to include in the results. |

## Example

Return the demo spans together with their operation name and service attribute.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name = "demo-python-service"} | select(name, .service_name)
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
  --data-urlencode 'q={.service_name = "demo-python-service"} | select(name, .service_name)' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- `select` changes what is returned, not what matches.
