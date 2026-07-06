# logfmt

Parses the log line as logfmt — the space-separated `key=value` format used by Grafana, Heroku, and many Go services — and adds every key as a label. Quoted values may contain spaces; keys are sanitized to valid label names.

## Syntax

```
| logfmt [<label>="<key>", ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expression>` | Optional | One or more `label="key"` pairs that extract only the named keys. Without expressions, all keys become labels. |

## Example

Parse Grafana's own logfmt output and keep only datasource requests that completed with HTTP status 200. The extracted `statusCode` label comes from the `statusCode=200` token in each line.

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana"} |= "duration=" | logfmt | statusCode="200"
```

**Expected output:**

```
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseLogsDatasource dsUID=P10239062BE9ED4EF uname=gra ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseLogsDatasource dsUID=P10239062BE9ED4EF uname=gra ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseLogsDatasource dsUID=P10239062BE9ED4EF uname=gra ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="grafana"} |= "duration=" | logfmt | statusCode="200"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Malformed logfmt lines flow through with `__error__` set to `LogfmtParserErr`.
- The `|= "duration="` line filter before the parser cheaply restricts parsing to the lines that carry the fields of interest.
