# Fingerprint fields

Every log line is assigned a **fingerprint**: the structural template of the line, with variable values replaced by placeholders. In FuseQL, the fingerprint is available as two fields:

| Field | Contents | Filter | Group by |
|---|---|---|---|
| `__kf_fp_hash` | A 16-character hex hash of the fingerprint, for example `d2321dd15f29bb9e` | Yes | Yes |
| `__kf_fp` | The fingerprint template, for example `logger=<v_0> <p_0>=<v_1> ...` | No (matches nothing) | No (returns a single `null` group) |

`fp_hash` and `fingerprint` are accepted as aliases for `__kf_fp_hash`. Before Release 4.4.0, raw log rows returned these fields as `fpString` and `fpHash`.

Verified against Kloudfuse 4.4.0. Run `check_fingerprint.py` to validate every example on your own cluster.

## Syntax

```fuseql
<filter> and __kf_fp_hash="<hash>"
<filter> and __kf_fp_hash!="<hash>"
<filter> and __kf_fp_hash in ("<hash>", "<hash>", ...)
<filter> | count by (__kf_fp_hash)
<filter> | count_unique(__kf_fp_hash)
```

## Examples

### Count logs by fingerprint

Find the line shapes that account for the most log volume from a source.

```fuseql
source="grafana" | count by (__kf_fp_hash) | sort by _count desc | limit 3
```

**Expected output:**

| _count | __kf_fp_hash |
|---|---|
| 423,906 | d2321dd15f29bb9e |
| 119,118 | 529973e21aed70b3 |
| 87,530 | 70fe5c34ff46aef6 |

### Filter to one fingerprint

Combine a fingerprint filter with other filters using `and`.

```fuseql
source="grafana" and __kf_fp_hash="d2321dd15f29bb9e"
```

Use `!=` to exclude a noisy fingerprint, or `in` to select several:

```fuseql
source="grafana" and __kf_fp_hash!="d2321dd15f29bb9e" | count
source="grafana" and __kf_fp_hash in ("d2321dd15f29bb9e", "529973e21aed70b3") | count
```

### Count distinct fingerprints over time

A jump in the number of distinct fingerprints often means new code paths or new error types.

```fuseql
* | timeslice 5m | count_unique(__kf_fp_hash) by (_timeslice, source)
```

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"grafana\\\" | count by (__kf_fp_hash) | sort by _count desc | limit 3\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Validate

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=<service-account-token>
python3 check_fingerprint.py --source grafana --minutes 15
```

## Notes

- Combine filters with an explicit `and`. Two filters side by side, such as `source="grafana" __kf_fp_hash="..."`, is a syntax error.
- Regular expressions are not supported on the hash: `__kf_fp_hash=~"..."` fails with `unsupported operator regex_match on fingerprint`.
- `__kf_fp` cannot be used to filter or group. A filter on it matches no logs, without an error, and grouping by it returns a single `null` group. Use `__kf_fp_hash`, and fetch a raw row to see the template.
- `fp_hash` still works in filters and group-by, but the output column takes the name you used, so `count by (fp_hash)` returns a `fp_hash` column.
