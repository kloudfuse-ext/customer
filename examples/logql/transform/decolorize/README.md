# decolorize

Removes ANSI terminal color codes from the log line, leaving plain text. Development tools and container runtimes often emit colored output; `decolorize` makes such lines readable in query results and safe for downstream parsing.

## Syntax

```
| decolorize
```

## Example

Strip any color escape sequences from JVM garbage-collection log lines before reading them.

<!-- validation: kind=range minutes=10 -->
```logql
{source="busybox"} | decolorize
```

**Expected output:**

```
[1728193.358s][info][gc] GC(89702) Pause Young (Mixed) (G1 Evacuation Pause) 32237M->7943M(40960M) 52.316ms
[2486072.473s][info][gc] GC(168886) Pause Young (Normal) (G1 Evacuation Pause) 40968M->12435M(49152M) 37.498ms
[1980334.497s][info][gc] GC(98036) Pause Young (Normal) (G1 Evacuation Pause) 33254M->9208M(40960M) 32.426ms
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="busybox"} | decolorize' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Lines without color codes pass through unchanged, so `decolorize` is safe to apply unconditionally.
