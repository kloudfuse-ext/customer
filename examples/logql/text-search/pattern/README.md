# Pattern match (|>)

Keeps log lines that match a pattern expression. Patterns use the literal text of the line with `<_>` as a wildcard for any run of characters, giving grep-like power without regex escaping. This is often the most readable way to match structured plain-text formats such as access logs.

## Syntax

```
{<selector>} |> "<pattern>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<pattern>` | Required | A pattern expression. Literal text must match exactly; each `<_>` matches any text. The pattern must match the entire line. |

## Example

Match nginx access-log lines whose quoted request section starts with `POST`, without writing a regex.

<!-- validation: kind=range minutes=10 -->
```logql
{source="nginx"} |> "<_>\"POST <_>"
```

**Expected output:**

```
10.2.140.127 - - [04/Jul/2026:15:38:33 +0000] "POST /write HTTP/1.1" 200 0 "-" "vmagent" 5099 0.012 [kfuse-ingester-8090 ...
10.2.128.131 - - [04/Jul/2026:15:38:33 +0000] "POST /ingester/v1/fluent_bit HTTP/1.1" 200 0 "-" "Fluent-Bit" 835 0.012 [ ...
10.2.134.34 - - [04/Jul/2026:15:38:33 +0000] "POST /ingester/v1/fluent_bit HTTP/1.1" 200 0 "-" "Fluent-Bit" 929 0.011 [k ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} |> "<_>\"POST <_>"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Double quotes inside the pattern must be escaped as `\"` because the pattern itself is a double-quoted string.
- The same pattern syntax powers the `pattern` parser, which extracts the wildcard positions into labels.
