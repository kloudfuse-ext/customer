# Duration comparison

Compares a label value as a duration when the literal carries a duration unit such as `300ms`, `1.5s`, or `2h`. Label values in Go duration format (`28.82661ms`) are parsed automatically, making this the natural filter for latency fields.

## Syntax

```
| <label> > <duration>    (also ==, !=, >=, <, <=)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | A label whose value is a duration string, such as `duration=28.8ms` extracted by `logfmt`. |
| `<duration>` | Required | A duration literal with a unit: `ns`, `us`, `ms`, `s`, `m`, `h`. |

## Example

Find slow Loki datasource requests in Grafana logs — anything that took longer than 10 milliseconds.

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana"} |= "duration=" | logfmt | duration > 10ms
```

**Expected output:**

```
logger=context userId=0 orgId=0 uname= t=2026-07-04T15:41:43.03381621Z level=info msg="Request Completed" meth ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseQLDatasource dsUID=P5BE00A3D5765370D uname=grafa ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseQLDatasource dsUID=P5BE00A3D5765370D uname=grafa ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="grafana"} |= "duration=" | logfmt | duration > 10ms' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- The comparison type comes from the literal: `10ms` triggers duration parsing, a bare `10` compares numerically.
