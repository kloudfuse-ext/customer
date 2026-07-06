# keep

Removes every label except the ones named. `keep` is the complement of `drop`: state what you want instead of what you do not, which is usually shorter after a parser that extracts many fields.

## Syntax

```
| keep <label> [, <label> ...] [, <label>="<value>"]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | One or more label names to retain; all other labels are removed. |
| `<label>="<value>"` | Optional | Conditional form: the label is kept only on lines where it equals the given value. |

## Example

Parse Filebeat JSON events and reduce the label set to just the log level and message.

<!-- validation: kind=range minutes=30 -->
```logql
{source="filebeat"} | json | keep log_level, message
```

**Expected output:**

```
{"log.level":"info","@timestamp":"2026-07-04T15:41:52.411Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:41:22.410Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:40:52.410Z","log.logger":"monitoring","log.origin":{"file.name ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="filebeat"} | json | keep log_level, message' \
  --data-urlencode "start=$(date -u -v-30M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Stream labels can be kept or removed like any other label — `keep` applies to the whole label set.
