# json

Parses the log line as JSON and adds every property as a label. Nested properties are flattened with underscores, and characters that are not valid in label names (such as dots) are replaced with underscores — `log.level` becomes `log_level`. Pass expressions to extract only specific fields.

## Syntax

```
| json [<label>="<expression>", ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expression>` | Optional | One or more `label="field"` pairs that extract only the named fields. Without expressions, all JSON properties become labels. |

## Example

Parse Filebeat's ECS-JSON log lines and keep only entries whose `log.level` property (flattened to `log_level`) is `info`.

<!-- validation: kind=range minutes=30 -->
```logql
{source="filebeat"} | json | log_level="info"
```

**Expected output:**

```
{"log.level":"info","@timestamp":"2026-07-04T15:37:52.411Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:34:52.411Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:36:22.411Z","log.logger":"monitoring","log.origin":{"file.name ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="filebeat"} | json | log_level="info"' \
  --data-urlencode "start=$(date -u -v-30M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Lines that are not valid JSON pass through unchanged with the `__error__` label set to `JSONParserErr`. Filter them out with `| __error__=""` or keep only them with `| __error__!=""`.
- Extracting all properties from large JSON objects creates many labels; prefer expressions such as `| json level="log.level", msg="message"` on wide events.
