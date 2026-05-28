# Logs Demo — Filebeat

Deploys **Filebeat** as a Kubernetes DaemonSet using the `elastic/filebeat` Helm chart.
Collects container logs from `/var/log/containers/` on each node and forwards them to
Kloudfuse via the Elasticsearch output plugin.

## How it works

- Filebeat's `container` input reads log files from `/var/log/containers/*.log` on each node.
- The `add_kubernetes_metadata` processor enriches records with pod, namespace, and container fields.
- Logs are delivered to `https://<kloudfuse-hostname>/ingester/api/v1/filebeat` (Elasticsearch-compatible endpoint).
- `setup.ilm.enabled: false` and `setup.template.enabled: false` are required — Kloudfuse does not implement Elasticsearch index management.

## Prerequisites

- Helm 3 installed.
- The `logs-demo` pod from [`../log-emitter/`](../log-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the header.

## Deploy

```bash
helm repo add elastic https://helm.elastic.co
helm repo update

# Replace <kloudfuse-hostname> and <token> in helm-values.yaml first, then:
helm upgrade --install filebeat elastic/filebeat \
  -f helm-values.yaml \
  --namespace logging \
  --create-namespace
```

## Verify logs in Kloudfuse

Logs are stored in the **Logs store**. Query in the Kloudfuse UI:

```
source="filebeat"
```

Filter to the demo pod by Kubernetes namespace:

```
source="filebeat" kubernetes.namespace="steve"
```

## Tear down

```bash
helm uninstall filebeat -n logging
```
