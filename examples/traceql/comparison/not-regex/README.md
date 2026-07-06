# Regex not match (!~)

Selects spans where an attribute or intrinsic does not match an RE2 regular expression — exclude several values with one condition.

## Syntax

```
{ .<attribute> !~ "<regex>" }
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `.<attribute>` | Required | The attribute or intrinsic to test. |
| `<regex>` | Required | Matching spans are excluded. |

## Example

Find demo spans whose operation name does not start with `data` — the `user` spans match, the `database` spans do not.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*" && name !~ "data.*"}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-go-service | database | 50 ms |
| demo-go-service | database | 50 ms |
| demo-go-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*" && name !~ "data.*"}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```
