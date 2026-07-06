# count

Counts the matching spans in each trace of each trace, then compares the result against a threshold. Traces that fail the comparison are dropped — this filters at the trace level, using evidence from all matching spans.

## Syntax

```
{ <conditions> } | count() <op> <value>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | count(): none; others: Required | A numeric field or intrinsic, typically `duration`. |
| `<op> <value>` | Required | Comparison against the aggregate: `>`, `>=`, `<`, `<=`, `=`, `!=`. |

## Example

Keep only traces that contain more than one matching span — both demo spans qualify.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name = "demo-python-service"} | count() > 1
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
  --data-urlencode 'q={.service_name = "demo-python-service"} | count() > 1' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- The aggregate runs per trace, over the spans matched by the spanset filter; the comparison decides whether the whole trace is returned.
- count() takes no argument.
