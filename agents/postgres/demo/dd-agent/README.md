# PostgreSQL Demo — Datadog Agent

Monitors the **kfuse-configdb** PostgreSQL instance (PostgreSQL 14) using the Datadog Agent's
built-in `postgres` check via Kubernetes Autodiscovery.

## How it works

- The agent discovers the `kfuse-configdb` pod via Autodiscovery annotations.
- It resolves `%%host%%` to the pod's cluster IP and opens a TCP connection to port 5432.
- It runs the postgres check, querying `pg_stat_database`, `pg_stat_bgwriter`, `pg_stat_statements`, and `pg_stat_replication`.
- Metrics are forwarded to `https://<kloudfuse-hostname>/ingester`.

## Monitoring user

A dedicated low-privilege user `kfmon` exists in the `kfuse-configdb` instance.
It was created with minimal permissions following PostgreSQL 14 best practices:

```sql
CREATE USER kfmon WITH PASSWORD '<password>' CONNECTION LIMIT 5;
GRANT pg_monitor TO kfmon;               -- read-only access to all pg_stat_* views
GRANT SELECT ON pg_stat_database TO kfmon;
GRANT SELECT ON pg_stat_statements TO kfmon;
GRANT SELECT ON pg_stat_statements_info TO kfmon;  -- required on PostgreSQL 14+
```

`pg_monitor` (PostgreSQL 10+) grants read-only access to all monitoring views without
any write privileges. The `CONNECTION LIMIT 5` cap prevents the monitoring user from
consuming connection slots needed by the application.

## Prerequisites

- The `kfmon` user already exists in `kfuse-configdb` (see above).
- Helm 3 installed.
- The external hostname of your Kloudfuse cluster.

## Deploy

```bash
# 1. Add Autodiscovery annotations to kfuse-configdb
#    Replace <password> in patch-annotations.yaml first, then:
kubectl patch statefulset kfuse-configdb -n $NAMESPACE --patch-file patch-annotations.yaml
kubectl rollout restart statefulset/kfuse-configdb -n $NAMESPACE

# 2. Deploy the Datadog Agent
helm repo add datadog https://helm.datadoghq.com
helm repo update

# Replace <kloudfuse-hostname> in helm-values.yaml first, then:
helm upgrade --install datadog-postgres datadog/datadog \
  --version 3.65.0 \
  -f helm-values.yaml \
  --namespace datadog-agent \
  --create-namespace
```

## Verify

Run the postgres check manually from the agent pod:

```bash
AGENT_POD=$(kubectl get pod -n datadog-agent -l app=datadog-postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n datadog-agent $AGENT_POD -- agent check postgres
```

Query metrics in Kloudfuse:

```
postgresql.connections{service:kfuse-configdb}
postgresql.rows_fetched{service:kfuse-configdb}
```

## Tear down

```bash
helm uninstall datadog-postgres -n datadog-agent
# Optionally remove the annotations patch:
kubectl patch statefulset kfuse-configdb -n $NAMESPACE --type=json \
  -p='[{"op":"remove","path":"/spec/template/metadata/annotations/ad.datadoghq.com~1postgresql.check_names"}]'
```
