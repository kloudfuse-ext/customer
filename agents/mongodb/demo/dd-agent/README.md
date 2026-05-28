# MongoDB Demo — Datadog Agent

Monitors the **kfuse-mongodb** MongoDB instance (MongoDB 7.0) using the Datadog Agent's
built-in `mongo` check via Kubernetes Autodiscovery.

## How it works

- The agent discovers the `kfuse-mongodb` pod via Autodiscovery annotations.
- It resolves `%%host%%` to the pod's cluster IP and opens a TCP connection to port 27017.
- It runs the mongo check, collecting metrics from `serverStatus`, `dbStats`, and replication status.
- Metrics are forwarded to `https://steve-dev-gcp.kloudfuse.io/ingester`.

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

## Prerequisites

- MongoDB deployed via `../mongodb-manifest.yaml` (creates the `kfuse-mongodb` StatefulSet
  and the `kfmon` user automatically).
- Helm 3 installed.
- The external hostname of your Kloudfuse cluster.

## Deploy

```bash
# 1. Deploy MongoDB (if not already running)
kubectl apply -f ../mongodb-manifest.yaml

# 2. Add Autodiscovery annotations to the kfuse-mongodb StatefulSet
kubectl patch statefulset kfuse-mongodb -n steve --patch-file patch-annotations.yaml
kubectl rollout restart statefulset/kfuse-mongodb -n steve

# 3. Deploy the Datadog Agent
helm repo add datadog https://helm.datadoghq.com
helm repo update

helm upgrade --install datadog-mongodb datadog/datadog \
  --version 3.65.0 \
  -f helm-values.yaml \
  --namespace datadog-agent \
  --create-namespace
```

## Verify

Run the mongo check manually from the agent pod:

```bash
AGENT_POD=$(kubectl get pod -n datadog-agent -l app=datadog-mongodb -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n datadog-agent $AGENT_POD -- agent check mongo
```

Query metrics in Kloudfuse:

```
mongodb_connections_current{service:kfuse-mongodb}
mongodb_opcounters_queryps{service:kfuse-mongodb}
mongodb_mem_resident{service:kfuse-mongodb}
```

## Tear down

```bash
helm uninstall datadog-mongodb -n datadog-agent
# Optionally remove the annotations patch:
kubectl patch statefulset kfuse-mongodb -n steve --type=json \
  -p='[{"op":"remove","path":"/spec/template/metadata/annotations/ad.datadoghq.com~1mongodb.check_names"}]'
```
