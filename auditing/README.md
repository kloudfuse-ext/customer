# Auditing & Performance Logs

FuseQL query examples for the Kloudfuse audit log and performance log streams.

## Prerequisites

```yaml
global:
  RBACEnabled: true
  EnableAuditLogs: true
  EnablePerfLogs: true        # required only for performance logs

kfuse-audit-log-vector:
  enabled: true
```

See the [Auditing documentation](https://docs.kloudfuse.com/administration/auditing/auditing/) for full configuration details.

## Log sources

| Source filter | Stream |
|---|---|
| `source="kf-audit-log"` | Authentication and mutation events from all services |
| `source="kf-performance-log"` | Every query processed by the platform, with duration |

## Notes on validated output

Results marked **Validated** were run against `<your-kloudfuse-hostname>` on 2026-07-17.

The structured facets (`action`, `user_email`, `resource_type`, `status`, `duration_ms`) are
present in every log entry's JSON body and are visible in the Logs UI Facets panel. Whether
they are available for aggregation via the API depends on how the cluster's Pinot schema
indexes those columns. Results marked **Illustrative** show the expected output structure
for a cluster with full facet indexing configured.

## Examples

- [audit-logs.md](audit-logs.md) — Volume, authentication events, user activity, mutations, authorization failures
- [performance-logs.md](performance-logs.md) — Query volume by service, latency analysis, per-user breakdown

## Running queries via the API

```bash
cd examples/fuseql
python3 query_log_metrics.py \
  --host <kloudfuse-hostname> \
  --token <service-account-token> \
  --query 'source="kf-audit-log" | count by action' \
  --minutes 10080
```
