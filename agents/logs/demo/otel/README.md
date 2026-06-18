# Logs Demo — OpenTelemetry Collector

Deploys the **OTel Collector Contrib** as a DaemonSet to collect container logs from each node
and forward them to Kloudfuse.

> **Note:** For log collection, deploy as a **DaemonSet** (one collector per node reads local log files).
> This is the opposite of the events demo, which requires a Deployment to avoid duplicates.

## How it works

- The `logsCollection` preset enables a `filelog` receiver reading `/var/log/pods/*/*/*.log` on each node.
- The `kubernetesAttributes` preset enriches each log record with pod name, namespace, container, etc.
- Logs are exported to `https://<kloudfuse-hostname>/ingester/otlp/v1/logs`.

## Prerequisites

- Helm 3 installed.
- The `logs-demo` pod from [`../log-emitter/`](../log-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the header.

## Deploy

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Replace <kloudfuse-hostname> and <token> in helm-values.yaml first, then:
helm upgrade --install otel-logs open-telemetry/opentelemetry-collector \
  -f helm-values.yaml \
  --namespace otel \
  --create-namespace
```

## Verify logs in Kloudfuse

Logs are stored in the **Logs store**. Filter by namespace in the Kloudfuse UI:

```logql
{k8s_namespace_name="$NAMESPACE"}
```

Or filter to just the demo pod:

```logql
{k8s_pod_name="logs-demo"}
```

## Tear down

```bash
helm uninstall otel-logs -n otel
```
