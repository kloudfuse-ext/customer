# by

Groups the matching spans by the value of an attribute, returning one span set per distinct value — a quick way to see which services or operations contribute matches.

## Syntax

```
{ <conditions> } | by(<field>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The attribute or intrinsic to group by. |

## Example

Group the demo spans by their service name — one group per demo service.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*"} | by(.service_name)
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-java-service | database | 50 ms |
| demo-go-service | database | 50 ms |
| demo-python-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*"} | by(.service_name)' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```
