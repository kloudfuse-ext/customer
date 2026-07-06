# Line regex not match (!~)

Discards log lines that match an RE2 regular expression. Use it to exclude several patterns at once with alternation, which is more compact than chaining multiple `!=` filters.

## Syntax

```
{<selector>} !~ "<regex>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<regex>` | Required | An RE2 regular expression, unanchored. Matching lines are removed. |

## Example

Hide routine `INFO` and `DEBUG` entries from ZooKeeper logs to surface warnings, errors, and unleveled output.

<!-- validation: kind=range minutes=10 -->
```logql
{source="zookeeper"} !~ "INFO|DEBUG"
```

**Expected output:**

```
Removing file: Jul 4, 2026, 2:57:21?PM /bitnami/zookeeper/data/version-2/snapshot.277012cbbbf
Removing file: Jul 4, 2026, 2:59:46?PM /bitnami/zookeeper/data/version-2/snapshot.277012e1dfa
Removing file: Jul 4, 2026, 2:50:34?PM /bitnami/zookeeper/data/version-2/snapshot.2770128d5b4
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="zookeeper"} !~ "INFO|DEBUG"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- When the excluded values are stream labels (such as `level`), prefer the stream-selector form `{source="zookeeper", level!~"info|debug"}` — it avoids scanning the excluded lines at all.
