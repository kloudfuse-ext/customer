# line_format

Replaces the log line with text rendered from a Go template. The template can reference any label as `{{.label}}`, which makes `line_format` the tool for trimming noisy lines down to the fields that matter, or for assembling a new line from parsed fields.

## Syntax

```
| line_format "<template>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<template>` | Required | A Go template string. `{{.label}}` inserts a label value; template functions such as `upper`, `trunc`, and `printf` are available. |

## Example

Reduce verbose Grafana datasource lines to a compact summary built from three parsed fields.

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana"} |= "duration="
| logfmt
| line_format "{{.level}} {{.endpoint}} took {{.duration}}"
```

**Expected output:**

```
info queryData took 96.062µs
info queryData took 213.193168ms
info queryData took 128.308µs
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="grafana"} |= "duration=" | logfmt | line_format "{{.level}} {{.endpoint}} took {{.duration}}"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- `line_format` changes only the line content; the label set is untouched.
- A pipeline stage after `line_format` sees the new line — including line filters and parsers.
