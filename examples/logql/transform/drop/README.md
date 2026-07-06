# drop

Removes the named labels from each line's label set. Use it after a parser that extracted more fields than you need — fewer labels means fewer distinct series when the pipeline feeds a metric query, and less noise in log results.

## Syntax

```
| drop <label> [, <label> ...] [, <label>="<value>"]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | One or more label names to remove. |
| `<label>="<value>"` | Optional | Conditional form: the label is dropped only on lines where it equals the given value. |

## Example

Parse Filebeat JSON events, then drop the source-code location fields that the `json` parser extracted but the investigation does not need.

<!-- validation: kind=range minutes=30 -->
```logql
{source="filebeat"}
| json
| drop log_origin_file_name, log_origin_file_line
```

**Expected output:**

```
{"log.level":"info","@timestamp":"2026-07-04T15:36:22.411Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:36:52.410Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:37:52.411Z","log.logger":"monitoring","log.origin":{"file.name ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="filebeat"} | json | drop log_origin_file_name, log_origin_file_line' \
  --data-urlencode "start=$(date -u -v-30M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- `drop` affects only the pipeline label set, not the stored log data.
- When most labels should go, `keep` is the shorter way to express the same intent.
