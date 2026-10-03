# fillmissing

Fills gaps in an aggregated result by synthesizing rows for the group combinations that returned no data. Use `fillmissing` when absent rows would otherwise be invisible — a time bucket with zero events simply does not appear in the result, so charts interpolate straight through the gap and alerts never see the value that should have been `0`.

## Syntax

```fuseql
| fillmissing <generator>[, <generator>, ...]
| fillmissing <generator>[, ...] with <value> for <field>[, <value> for <field>, ...]
| fillmissing <generator>[, ...] [with ...] takelast
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<generator>` | Required | `timeslice`, `timeslice(<duration>)`, `values("v1", "v2", ...) in <field>`, or `values all in <field>`. Multiple generators combine as a Cartesian product. |
| `with <value> for <field>` | Optional | Fill value for a synthesized row's `<field>`, overriding the type default (`0` for numeric, `false` for boolean, `null` otherwise). |
| `takelast` | Optional | Copy the previous bucket's non-key values forward instead of using the default. Requires a `timeslice` generator. |

## Example

Count `browser`-source log events per 5-minute bucket, then restore the buckets with no events.

```fuseql
source="browser"
| timeslice 5m
| count by (_timeslice)
| fillmissing timeslice
```

**Expected output (without `fillmissing`, only the non-zero buckets appear):**

| _timeslice | _count |
|---|---|
| 2026-09-30 17:50:00 UTC | 1 |
| 2026-09-30 17:55:00 UTC | 4 |
| 2026-09-30 18:10:00 UTC | 2 |
| 2026-09-30 18:25:00 UTC | 1 |
| 2026-09-30 18:55:00 UTC | 8 |
| 2026-09-30 19:10:00 UTC | 2 |
| 2026-09-30 19:15:00 UTC | 2 |

**Expected output (with `fillmissing timeslice`, every bucket in the range appears):**

| _timeslice | _count |
|---|---|
| 2026-09-30 17:25:00 UTC | 0 |
| 2026-09-30 17:30:00 UTC | 0 |
| 2026-09-30 17:35:00 UTC | 0 |
| 2026-09-30 17:40:00 UTC | 0 |
| 2026-09-30 17:45:00 UTC | 0 |
| 2026-09-30 17:50:00 UTC | 1 |
| 2026-09-30 17:55:00 UTC | 4 |
| 2026-09-30 18:00:00 UTC | 0 |
| 2026-09-30 18:05:00 UTC | 0 |
| 2026-09-30 18:10:00 UTC | 2 |
| ... | ... |
| 2026-09-30 19:20:00 UTC | 0 |
| 2026-09-30 19:25:00 UTC | 0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"browser\\\" | timeslice 5m | count by (_timeslice) | fillmissing timeslice\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Additional generators, verified live

**`values(...) in <field>` with a per-field default** — guarantee a fixed set of label values, marking absent ones distinctly from a genuine zero count:

```fuseql
source="nginx"
| count by (status)
| fillmissing values("info", "error", "debug") in status with -1 for _count
```

| _count | status |
|---|---|
| -1 | debug |
| 5 | error |
| 33,868,840 | info |

`debug` never occurred in the window, so it is synthesized with the override value `-1`; `info` and `error` are real rows, untouched.

**`timeslice, values all in <field>` (dense grid) + `takelast`** — every (bucket, label) pair gets a row, and gaps after a series' first real row carry the previous value forward instead of defaulting to `0`:

```fuseql
source="browser"
| timeslice 10m
| count by (_timeslice, status)
| fillmissing timeslice, values all in status takelast
```

Confirmed: rows are ordered by the non-time group key first (`error` rows, then `warn` rows), then by time ascending within each group — no separate sort stage needed. Buckets *before* a series' first real row keep the `0` default (nothing to carry forward yet); every bucket after it repeats the last real value until the next real row arrives.

**Error case** — a `timeslice` generator on an aggregation with no upstream `timeslice` stage fails outright rather than silently doing nothing:

```fuseql
source="nginx" | count by (status) | fillmissing timeslice
```

```
GraphQL error: fillmissing timeslice generator requires a time-bucketed result, but the input has no TimeKey
```

**Error case** — a `with` value that doesn't match its column's type (a quoted string for the numeric `_count` column) is rejected rather than filled:

```fuseql
source="nginx" | count by (status) | fillmissing values("info","error","debug") in status with "oops" for _count
```

```
GraphQL error: Request failed
```

**Default fill values by column type** — confirmed `0` for numeric columns (see the `values(...)` example above) and `null` for STRING columns: aggregating `first(url) as first_url by (method)` and filling in two methods (`DELETE`, `PATCH`) that had no real rows produced `first_url: null` for both, while the real `GET`/`HEAD`/`POST`/`PUT` rows kept their real first-seen URL. (The documented `false` default for BOOLEAN columns was not verified — no FuseQL aggregation function in this cluster's operator set (`first`, `last`, etc. are string/numeric-only) produces a boolean-typed output column to test against.)

**10,000-row combination cap** — confirmed. A query combining a 1-day, 1-minute `timeslice` (1,440 buckets) with a 20-value `values(...)` generator on `status` (28,800 possible combinations) returned exactly **10,000 rows** and succeeded (no error), with all 20 status values still represented (~500 rows each) rather than the cap simply truncating the tail chronologically or dropping whole groups.

## Notes

- `fillmissing` must follow an aggregation operator; it runs in memory on the aggregated result and is never pushed down to the underlying store.
- The `timeslice` generator's bucket width resolves from, in order: an explicit `timeslice(<duration>)` in the `fillmissing` clause, the width of the upstream `timeslice` stage, or an automatic width derived from the query's time range. Verified: `fillmissing timeslice(10m)` after an upstream `timeslice 5m` synthesizes new gap rows on a 10-minute cadence while leaving the original 5-minute real rows untouched — synthesized buckets align to whatever buckets are already present in the result rather than forcing every row onto a uniform grid. The third tier ("automatic width derived from the query's time range") could not be independently exercised — every path that produces a time-bucketed result in this cluster already has an upstream `timeslice` stage, so tier 2 always applies first; it's unclear whether tier 3 is reachable in practice.
- Buckets are enumerated across the entire query time range, so leading and trailing gaps are filled, not just gaps between existing rows.
- `fillmissing` never adds columns — confirmed via `ColumnHeaders` staying identical before/after `fillmissing` in every test above.
- **KNOWN ISSUE, not a `fillmissing` bug specifically:** the `timeslice <duration> as <alias>` generator variant, and the doc's claim that plain `fillmissing timeslice` "targets... the alias from `timeslice <duration> as <alias>`", could not be verified. Renaming the bucket column with `as <alias>` and then grouping by that alias (e.g. `timeslice 5m as ts | count by (ts)`) silently collapses the result to a single ungrouped total row on this cluster via `getLogMetricsResultWithKfuseQl` — the alias is accepted by the parser (it shows up in `GroupKeys`) but the actual per-bucket grouping never happens, and `TimeKey` comes back empty. This reproduced with three different alias names (`bucket_ts`, `ts`, `_myslice`) and is upstream of `fillmissing` — it means the `timeslice[(<duration>)] in <field>` generator (for naming the bucket field explicitly) is also currently untestable, since there's no way to produce a correctly-aliased time-bucketed result to fill gaps in. Flagging for engineering — this looks like a real bug in aliased-`timeslice` grouping on the FuseQL metrics endpoint, not a documentation issue on its own, but it does mean two of the documented `fillmissing` generator forms (bare `timeslice` targeting an alias, and `timeslice[(<duration>)] in <field>`) are unverified and possibly broken.
