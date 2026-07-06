# Ordering comparisons (>, >=, <, <=)

Compares numeric attributes and duration intrinsics with `>`, `>=`, `<`, and `<=`. Durations take Go-style units (`100ms`, `2s`); the most common use is latency filtering on the `duration` intrinsic.

## Syntax

```
{ duration > <duration> }    (also >=, <, <=)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<duration>` | Required | A duration literal such as `40ms` or `1s`, or a number for numeric attributes. |

## Example

Find demo spans that took at least 40 milliseconds — the 50 ms root spans match.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*" && duration >= 40ms}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-java-service | database | 50 ms |
| demo-java-service | database | 50 ms |
| demo-python-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*" && duration >= 40ms}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```
