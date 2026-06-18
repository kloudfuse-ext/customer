# Logs Demo — Elastic Beats (Filebeat manifest)

Deploys **Filebeat** as a Kubernetes DaemonSet via a direct manifest (no Helm).
Uses the same Kloudfuse ingestion endpoint as the Helm-based Filebeat deployment in `../filebeat/`.

## Why manifest instead of Elastic Agent

Elastic Agent v8.x standalone mode routes all inputs through a Fleet coordinator.
When Fleet enrollment is disabled (`fleet.enabled: false`), the coordinator starts
with an empty policy and never processes inputs from the config file — resulting in
no data being shipped.

For container log collection without a Fleet/Kibana server, Filebeat is the
recommended approach. Both Filebeat and Elastic Agent use the same
`/ingester/api/v1/filebeat` endpoint and produce equivalent results in Kloudfuse.

## How it works

- Filebeat reads container log files from `/var/log/containers/` on each node.
- The `add_kubernetes_metadata` processor enriches records with pod, namespace, and container fields.
- Logs are delivered to `https://<kloudfuse-hostname>/ingester/api/v1/filebeat` via the Elasticsearch-compatible output.
- `setup.ilm.enabled: false` and `setup.template.enabled: false` are required — Kloudfuse does not implement Elasticsearch index management.

## Prerequisites

- `kubectl` with cluster access.
- The `logs-demo` pod from [`../log-emitter/`](../log-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the header.

## Deploy

```bash
# Replace <kloudfuse-hostname> and <token> in manifest.yaml first, then:
kubectl apply -f manifest.yaml
```

## Verify logs in Kloudfuse

Logs are stored in the **Logs store**. Query in the Kloudfuse UI using the `agent` label
to distinguish this deployment from the Helm-based Filebeat:

```
agent="filebeat" kube_namespace="$NAMESPACE"
```

Filter by container name:

```
agent="filebeat" kube_namespace="$NAMESPACE" kube_container_name="log-emitter"
```

## Tear down

```bash
kubectl delete -f manifest.yaml
```
