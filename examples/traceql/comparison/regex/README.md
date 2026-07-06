# Regex match (=~)

Selects spans where an attribute or intrinsic matches an RE2 regular expression — one condition for a whole family of values.

## Syntax

```
{ .<attribute> =~ "<regex>" }
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `.<attribute>` | Required | The attribute or intrinsic to test. |
| `<regex>` | Required | An RE2 regular expression. |

## Example

Match all three demo services with a single expression.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo-.*-service"}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-java-service | database | 50 ms |
| demo-python-service | database | 50 ms |
| demo-java-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo-.*-service"}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- RE2 does not support look-ahead or back-references.
