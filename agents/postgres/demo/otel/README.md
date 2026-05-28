# PostgreSQL Demo — OTel Collector

Monitors the **kfuse-configdb** PostgreSQL instance (PostgreSQL 14) using the OpenTelemetry
Collector `postgresqlreceiver`, deployed as a single-pod Deployment in the `otel` namespace.

## How it works

- The OTel Collector Contrib image (`otel/opentelemetry-collector-contrib`) connects directly
  to `<postgres-host>:<postgres-port>` using the `kfmon` monitoring user.
- It queries `pg_stat_database`, `pg_stat_bgwriter`, `pg_stat_statements`, and
  `pg_stat_replication` every 60 seconds.
- Metrics are exported via OTLP HTTP to `https://<kloudfuse-hostname>/ingester/otlp/metrics`.
- Deployed as a `Deployment` (not DaemonSet) — a single collector pod is sufficient for
  database monitoring.

## Monitoring user

A dedicated low-privilege user `kfmon` exists in the `kfuse-configdb` instance.
It was created with minimal permissions following PostgreSQL 14 best practices:

```sql
CREATE USER kfmon WITH PASSWORD '<password>' CONNECTION LIMIT 20;
GRANT pg_monitor TO kfmon;               -- read-only access to all pg_stat_* views
GRANT SELECT ON pg_stat_database TO kfmon;
GRANT SELECT ON pg_stat_statements TO kfmon;
GRANT SELECT ON pg_stat_statements_info TO kfmon;  -- required on PostgreSQL 14+
```

`pg_monitor` (PostgreSQL 10+) grants read-only access to all monitoring views without
any write privileges. `CONNECTION LIMIT 20` is required for the OTel `postgresqlreceiver`
because it opens one connection per database per metric query — monitoring 4 databases
requires up to ~24 concurrent connections per scrape cycle. A limit of 5 causes
`too many connections for role` errors on every scrape. The dd-agent check, by contrast,
uses a single persistent connection per instance and only needs `CONNECTION LIMIT 5`.

## Prerequisites

- The `kfmon` user already exists in `kfuse-configdb` (see above).
- Helm 3 installed.
- The external hostname of your Kloudfuse cluster.

## Deploy

```bash
# 1. Create namespace and secret
kubectl create namespace otel 2>/dev/null || true

kubectl create secret generic otel-postgres-credentials \
  --from-literal=password='<kfmon-password>' \
  -n otel

# 2. Deploy the collector
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Replace <kloudfuse-hostname> in helm-values.yaml first, then:
helm upgrade --install otel-postgres open-telemetry/opentelemetry-collector \
  -f helm-values.yaml \
  --namespace otel
```

## Verify

Check the collector is running and exporting metrics:

```bash
kubectl logs -n otel -l app.kubernetes.io/name=opentelemetry-collector --tail=50
```

Query metrics in Kloudfuse (PromQL — OTel `.` converted to `_`):

```
postgresql_backends{service_name="kfuse-configdb"}
postgresql_db_size{service_name="kfuse-configdb"}
postgresql_commits{service_name="kfuse-configdb"}
```

## Tear down

```bash
helm uninstall otel-postgres -n otel
kubectl delete secret otel-postgres-credentials -n otel
```
