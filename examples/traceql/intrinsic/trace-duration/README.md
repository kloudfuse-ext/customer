# traceDuration

The end-to-end elapsed time of the entire trace, measured across all its spans. Use it to find slow requests regardless of which span inside them was slow.

## Syntax

```
{ traceDuration > <duration> }
```

## Example

Find demo traces that took at least 10 milliseconds end to end.

<!-- validation: kind=search minutes=15 -->
```traceql
{.service_name =~ "demo.*" && traceDuration > 10ms}
```

**Expected output:**

| Root service | Root span | Duration |
|---|---|---|
| demo-go-service | database | 50 ms |
| demo-java-service | database | 50 ms |
| demo-go-service | database | 50 ms |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<trace-ds-uid>/api/search" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'q={.service_name =~ "demo.*" && traceDuration > 10ms}' \
  --data-urlencode "start=$(date -u -v-15M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=5"
```

## Notes

- A trace matches when any span satisfies the other conditions and the whole trace exceeds the duration.
