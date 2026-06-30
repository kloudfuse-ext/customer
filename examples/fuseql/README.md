# FuseQL API Examples

Python examples for querying Kloudfuse logs programmatically using the FuseQL GraphQL API.

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

## Examples

### `query_log_metrics.py` — Aggregated metrics from logs

Uses `getLogMetricsResultWithKfuseQl` to run FuseQL queries that aggregate, group, or
use `timeslice`. Returns a single response.

```bash
# Count all logs in the last hour, bucketed into 5-minute slices
python3 query_log_metrics.py --query "* | timeslice 5m | count by (_timeslice)"

# Count error logs grouped by source, last 30 minutes
python3 query_log_metrics.py \
  --query 'level="error" | count by (source)' \
  --minutes 30

# Error rate over time per source
python3 query_log_metrics.py \
  --query 'level="error" | timeslice 5m | count by (_timeslice, source)' \
  --minutes 60

# Custom time range
python3 query_log_metrics.py \
  --query '* | count by (source)' \
  --start 2026-06-27T03:00:00Z \
  --end   2026-06-27T04:00:00Z
```

### `fetch_logs.py` — Paginated raw log retrieval

Uses `getLogsWithFuseQlStream` to fetch raw log rows with cursor-based pagination.
Results stream in pages of up to 200 rows each.

```bash
# Fetch all error logs from the last hour, print to stdout
python3 fetch_logs.py --query 'level="error"'

# Fetch logs from a specific source, write as JSON Lines to a file
python3 fetch_logs.py \
  --query 'source="grafana"' \
  --minutes 60 \
  --output grafana_errors.jsonl

# Stop after fetching 1000 rows
python3 fetch_logs.py \
  --query 'level="error"' \
  --max-rows 1000
```

### `lookup_tables.py` — Manage lookup tables

Create, list, and delete lookup tables used by the FuseQL `lookup` operator.

```bash
# List all lookup tables
python3 lookup_tables.py list

# Create a lookup table from a CSV file
python3 lookup_tables.py create \
  --name cluster_costs \
  --primary-key ClusterName \
  --file cluster_costs.csv

# Delete a lookup table
python3 lookup_tables.py delete --name cluster_costs
```
