# MongoDB Demo — OTel Collector

Monitors the **kfuse-mongodb** MongoDB instance (MongoDB 7.0) using the OpenTelemetry
Collector `mongodbreceiver`, deployed as a single-pod Deployment in the `otel` namespace.

## How it works

- The OTel Collector Contrib image (`otel/opentelemetry-collector-contrib`) connects directly
  to `kfuse-mongodb.steve.svc.cluster.local:27017` using the `kfmon` monitoring user.
- It queries `serverStatus` and `dbStats` every 60 seconds via the `mongodbreceiver`.
- Metrics are exported via OTLP HTTP to `https://steve-dev-gcp.kloudfuse.io/ingester/otlp/metrics`.
- Deployed as a `Deployment` (not DaemonSet) — a single collector pod is sufficient for
  database monitoring.

## Monitoring user

A dedicated low-privilege user `kfmon` exists in the `kfuse-mongodb` `admin` database.
It was created with minimal permissions:

```js
use admin
db.createUser({
  user: "kfmon",
  pwd: "<password>",
  roles: [
    { role: "clusterMonitor", db: "admin" },
    { role: "read", db: "local" }
  ]
})
```

`clusterMonitor` grants read-only access to monitoring commands (`serverStatus`,
`replSetGetStatus`, etc.) without any write privileges. `read` on `local` is required
for oplog access.

## Note on replica set warning

The collector logs a warning at startup:

```
failed to find secondary hosts: (NoReplicationEnabled) not running with --replSet
```

This is expected for a standalone MongoDB instance and does not affect metric collection.

## Prerequisites

- MongoDB deployed via `../mongodb-manifest.yaml` (creates the `kfuse-mongodb` StatefulSet
  and the `kfmon` user automatically).
- Helm 3 installed.
- The external hostname of your Kloudfuse cluster.

## Deploy

```bash
# 1. Deploy MongoDB (if not already running)
kubectl apply -f ../mongodb-manifest.yaml

# 2. Create namespace and credentials secret
kubectl create namespace otel 2>/dev/null || true

kubectl create secret generic otel-mongodb-credentials \
  --from-literal=password='<password>' \
  -n otel

# 3. Deploy the collector
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

helm upgrade --install otel-mongodb open-telemetry/opentelemetry-collector \
  -f helm-values.yaml \
  --namespace otel
```

## Verify

Check the collector is running and exporting metrics:

```bash
kubectl logs -n otel -l app.kubernetes.io/instance=otel-mongodb --tail=50
```

Query metrics in Kloudfuse:

```
mongodb_connection_count{service_name="kfuse-mongodb"}
mongodb_collection_count{service_name="kfuse-mongodb"}
mongodb_cache_operations{service_name="kfuse-mongodb"}
```

## Tear down

```bash
helm uninstall otel-mongodb -n otel
kubectl delete secret otel-mongodb-credentials -n otel
```
