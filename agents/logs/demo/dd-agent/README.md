# Logs Demo — Datadog Agent

Deploys the **Datadog node Agent** as a DaemonSet to collect container logs from all pods
on each node and forward them to Kloudfuse.

## How it works

- The node agent reads container log files from `/var/log/containers/` on each node.
- Logs are shipped via HTTP to `<kloudfuse-hostname>:443` (`logs_dd_url` in `agents.customAgentConfig`).
- The Datadog Autodiscovery annotation on the `logs-demo` pod sets `source=logs-demo` and `service=logs-demo`.
- The Cluster Agent is disabled — it is not required for log collection.

## Prerequisites

- Helm 3 installed.
- Datadog Agent version **7.41 or higher** and Helm chart version **3.1.10 or higher**.
- The `logs-demo` pod from [`../log-emitter/`](../log-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.

## Deploy

```bash
helm repo add datadog https://helm.datadoghq.com
helm repo update

# Replace <kloudfuse-hostname> in helm-values.yaml first, then:
kubectl create namespace datadog-agent
helm upgrade --install datadog-agent datadog/datadog \
  -f helm-values.yaml \
  -n datadog-agent \
  --version 3.65.0
```

## Verify logs in Kloudfuse

Logs are stored in the **Logs store**. In the Kloudfuse UI, query:

```
source="logs-demo"
```

Or filter by level:

```
source="logs-demo" level="ERROR"
```

> **Note:** The `logs_dd_url` value uses `<hostname>:443` format (no `/ingester` prefix).
> This is different from `dd_url` (metrics/events) which uses `https://<hostname>/ingester`.

## Tear down

```bash
helm uninstall datadog-agent -n datadog-agent
kubectl delete namespace datadog-agent
```
