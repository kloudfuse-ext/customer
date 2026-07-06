# Equal (=)

Selects spans where an attribute or intrinsic equals the given value. Attribute names take a leading dot (`.service_name`); scoped forms (`resource.`, `span.`) restrict where the attribute is looked up. String values are quoted; numbers, durations, and enums like span kind are not.

## Syntax

```
{ .<attribute> = "<value>" }
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `.<attribute>` | Required | The span or resource attribute, or an intrinsic such as `name`, `duration`, `kind`, `status`. |
| `<value>` | Required | Quoted string, number, duration (`100ms`), or enum value. |

## Example

Find traces containing spans from the `demo-python-service`.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name = "demo-python-service"}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-python-service | database | 51 ms |
| demo-python-service | database | 50 ms |
| demo-python-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name = "demo-python-service"}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- An unscoped attribute (`.name`) searches span attributes and resource attributes; use `resource.` or `span.` to pin the scope.
