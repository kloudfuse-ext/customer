# String comparison

Compares a label value against a quoted string using `=`, `!=`, `=~`, or `!~`. String label filters work on both original stream labels and labels extracted by parsers, which makes them the standard way to filter on parsed fields mid-pipeline.

## Syntax

```
| <label> = "<value>"    (also !=, =~, !~)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | A stream label or a label extracted earlier in the pipeline. |
| `<value>` | Required | A quoted string for `=`/`!=`, or an anchored RE2 regular expression for `=~`/`!~`. |

## Example

Parse Grafana datasource logs and keep only the `queryData` endpoint, using the `endpoint` label created by the `logfmt` parser.

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana"} |= "duration=" | logfmt | endpoint="queryData"
```

**Expected output:**

```
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseQLDatasource dsUID=P5BE00A3D5765370D uname=grafa ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseQLDatasource dsUID=P5BE00A3D5765370D uname=grafa ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseQLDatasource dsUID=P5BE00A3D5765370D uname=grafa ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="grafana"} |= "duration=" | logfmt | endpoint="queryData"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Multiple label filters can be chained; see the combining filters operator for `and`/`or` semantics.
