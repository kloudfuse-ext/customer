# Not equal (!=)

Selects spans where an attribute or intrinsic is not equal to the given value. Combine with a positive condition to keep the search scoped.

## Syntax

```
{ .<attribute> != "<value>" }
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `.<attribute>` | Required | The attribute or intrinsic to test. |
| `<value>` | Required | The value to exclude. |

## Example

Find demo traces from every service except the Python one.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*" && .service_name != "demo-python-service"}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-java-service | database | 50 ms |
| demo-java-service | database | 50 ms |
| demo-java-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*" && .service_name != "demo-python-service"}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- Spans that do not carry the attribute at all do not match a `!=` condition.
