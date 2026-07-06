# Bytes comparison

Compares a label value as a byte size when the literal carries a size unit such as `512B`, `1KB`, or `2GiB`. Plain numeric label values are treated as byte counts, so response-size fields from access logs work without conversion.

## Syntax

```
| <label> > <size>    (also ==, !=, >=, <, <=)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | A label whose value is a byte count or size string. |
| `<size>` | Required | A size literal with a unit: `B`, `KB`, `MB`, `GB`, `KiB`, `MiB`, and so on. |

## Example

Extract the response size from nginx access logs and keep responses larger than one kilobyte.

<!-- validation: kind=range minutes=3 -->
```logql
{source="nginx"}
| regexp "\" (?P<status>[0-9]{3}) (?P<resp_bytes>[0-9]+)"
| resp_bytes > 1KB
```

**Expected output:**

```
10.20.10.88 - - [04/Jul/2026:15:41:48 +0000] "POST /ingester/api/v1/filebeat/_bulk HTTP/1.1" 200 4848 "-" "Ela ...
10.20.10.88 - - [04/Jul/2026:15:41:48 +0000] "POST /ingester/api/v1/filebeat/_bulk HTTP/1.1" 200 4848 "-" "Ela ...
10.20.10.88 - - [04/Jul/2026:15:41:48 +0000] "POST /ingester/api/v1/filebeat/_bulk HTTP/1.1" 200 4848 "-" "Ela ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} | regexp "\" (?P<status>[0-9]{3}) (?P<resp_bytes>[0-9]+)" | resp_bytes > 1KB' \
  --data-urlencode "start=$(date -u -v-3M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- `1KB` is 1000 bytes; use `1KiB` for 1024.
