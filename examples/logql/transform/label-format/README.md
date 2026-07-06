# label_format

Renames a label or assigns it a value rendered from a Go template. `label_format status=statusCode` renames `statusCode` to `status`; a double-quoted right-hand side is treated as a template, so labels can also be derived from other labels.

## Syntax

```
| label_format <new>=<old> [, <label>="<template>"]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<new>=<old>` | Required | Renames label `<old>` to `<new>`. The right-hand side is a bare label name. |
| `<label>="<template>"` | Optional | Sets `<label>` to the rendered Go template value; reference other labels as `{{.label}}`. |

## Example

Rename the parsed `statusCode` label to the shorter `status` and keep only successful requests using the new name.

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana"} |= "duration="
| logfmt
| label_format status=statusCode
| status="200"
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
  --data-urlencode 'query={source="grafana"} |= "duration=" | logfmt | label_format status=statusCode | status="200"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Renaming with a bare label name moves the value — the old label is removed.
- Multiple assignments in one `label_format` are separated by commas, but a label can be assigned only once per stage.
