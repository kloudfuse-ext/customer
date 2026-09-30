# Events API Examples

Python examples for querying Kloudfuse events programmatically over GraphQL.

## Prerequisites

```bash
pip install requests
```

## Configuration

Set your Kloudfuse host and Service Account token:

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=glsa_...
```

Or pass them directly as arguments (see `--help` on each script).

Requests go to the `/events-query` endpoint — distinct from the `/query` endpoint used
by the logs and metrics APIs.

## Filtering

Filters are passed as a JSON object matching the `EventFilter` GraphQL input type:
`eq`, `neq`, `startsWith`, `endsWith`, `contains`, `regex`, `nregex`, `keyExists`, `and`, `or`, `not`.
Each comparison operator takes `{"name": ..., "value": ...}`.

`name` must be `@`-prefixed for a top-level event field (facet) — for example `@severity`
or `@source` — and bare for a label name — for example `kube_namespace`. See
`reference/api/events.adoc` in kf-docs for the full field list.

```bash
# Single condition
--filter '{"eq": {"name": "@severity", "value": "error"}}'

# Combined conditions
--filter '{"and": [{"eq": {"name": "@severity", "value": "error"}}, {"eq": {"name": "@source", "value": "kubernetes"}}]}'
```

## Examples

### `fetch_events.py` — Raw event retrieval

Uses the `events` query, paginating with `offset` (200 rows per page).

```bash
# All events in the last hour
python3 fetch_events.py

# Error-severity Kubernetes events, last 30 minutes
python3 fetch_events.py \
  --filter '{"and": [{"eq": {"name": "@severity", "value": "error"}}, {"eq": {"name": "@source", "value": "kubernetes"}}]}' \
  --minutes 30

# Write to a file as JSON Lines, capped at 500 rows
python3 fetch_events.py --filter '{"eq": {"name": "@source", "value": "kubernetes"}}' \
  --output events.jsonl --max-rows 500
```

### `query_event_counts.py` — Aggregated event counts

Uses the `eventCounts` query to count events, optionally grouped by a facet/label and
bucketed over time.

```bash
# Count of events by severity over the last hour
python3 query_event_counts.py --group-by @severity

# Kubernetes events, bucketed into 5-minute windows, grouped by severity
python3 query_event_counts.py \
  --filter '{"eq": {"name": "@source", "value": "kubernetes"}}' \
  --group-by @severity --round-secs 300

# Raw JSON output
python3 query_event_counts.py --group-by @source --json
```

## Live validation

`test_events_api.sh` runs every documented Events API operation against a live instance
and checks the response shape:

```bash
TOKEN=<sa-token> HOST=<your-instance> bash test_events_api.sh
```
