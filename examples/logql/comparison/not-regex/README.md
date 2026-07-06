# Regex not match (!~)

Selects log streams whose label value does not match an RE2 regular expression. Use it to exclude several values with one matcher — for example, dropping both `debug` and `info` noise in a single expression.

## Syntax

```
{<label>="<value>", <label2>!~"<regex>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The stream label to test. |
| `<regex>` | Required | An RE2 regular expression. Streams where the entire label value matches are excluded. |

## Example

Select Grafana logs while excluding the chatty `debug` and `info` levels, leaving `warn` and `error` lines.

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana", level!~"debug|info"}
```

**Expected output:**

```
logger=ngalert.state.manager rule_uid=ffls7hdn4xsshd org_id=1 t=2026-07-04T15:38:08.312822406Z level=error msg="Error in ...
logger=ngalert.state.manager rule_uid=ffls7hdn4xsshd org_id=1 t=2026-07-04T15:38:08.312940088Z level=error msg="Error in ...
logger=ngalert.state.manager rule_uid=ffls7hdn4xsshd org_id=1 t=2026-07-04T15:38:08.314370235Z level=error msg="Error in ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="grafana", level!~"debug|info"}' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Like `=~`, the expression is anchored — `!~"debug"` excludes only the exact value `debug`, not values containing it.
