# Not equal (!=)

Selects log streams whose label value is not equal to the given string. Use it to exclude one stream from an otherwise broad selection — for example, all log levels except `error` while investigating what happened before failures.

## Syntax

```
{<label>="<value>", <label2>!="<value2>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The stream label to test. |
| `<value>` | Required | The string value to exclude. Comparison is case-sensitive. |

## Example

Select Grafana logs at every level except `error`. The result contains `info`, `warn`, and `debug` lines only.

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana", level!="error"}
```

**Expected output:**

```
logger=ngalert.state.manager rule_uid=bfoy7tneurcw0f org_id=1 t=2026-07-04T15:38:05.346683129Z level=info msg="Detected  ...
logger=ngalert.state.manager rule_uid=bfoy7tneurcw0f org_id=1 t=2026-07-04T15:38:05.346756834Z level=info msg="Detected  ...
logger=ngalert.state.manager rule_uid=deer5zpvjivpdf org_id=1 t=2026-07-04T15:38:05.314430324Z level=info msg="Detected  ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="grafana", level!="error"}' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- A stream selector cannot consist of only negative matchers; include at least one positive matcher such as `source="grafana"`.
