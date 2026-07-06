# Or (||)

Combines conditions so that a span matches when any condition holds. Parenthesize when mixing `&&` and `||` to make precedence explicit.

## Syntax

```
{ <condition> || <condition> }
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<condition>` | Required | Any attribute or intrinsic comparison. |

## Example

Find spans for either of the demo operations.

<!-- validation: kind=search minutes=15 -->
```traceql
{name = "database" || name = "user"}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-java-service | database | 50 ms |
| demo-go-service | database | 50 ms |
| demo-python-service | database | 51 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={name = "database" || name = "user"}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```
