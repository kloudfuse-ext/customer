# max

Takes the maximum of a field over the matching spans of each trace, then compares the result against a threshold. Traces that fail the comparison are dropped — this filters at the trace level, using evidence from all matching spans.

## Syntax

```
{ <conditions> } | max(<field>) <op> <value>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | count(): none; others: Required | A numeric field or intrinsic, typically `duration`. |
| `<op> <value>` | Required | Comparison against the aggregate: `>`, `>=`, `<`, `<=`, `=`, `!=`. |

## Example

Keep traces whose slowest matching span exceeds 10 ms.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*"} | max(duration) > 10ms
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-go-service | database | 51 ms |
| demo-java-service | database | 50 ms |
| demo-python-service | database | 51 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*"} | max(duration) > 10ms' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- The aggregate runs per trace, over the spans matched by the spanset filter; the comparison decides whether the whole trace is returned.
