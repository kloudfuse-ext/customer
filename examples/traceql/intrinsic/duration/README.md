# duration

The elapsed time of the span. Compare it with duration literals to find slow (or suspiciously fast) operations — the single most used intrinsic in trace search.

## Syntax

```
{ duration > <duration> }
```

## Example

Find demo spans that ran for 40 milliseconds or longer.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*" && duration >= 40ms}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-java-service | database | 50 ms |
| demo-go-service | database | 51 ms |
| demo-java-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*" && duration >= 40ms}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- `duration` is the span's own time, including its children; for whole-trace latency use `traceDuration`.
