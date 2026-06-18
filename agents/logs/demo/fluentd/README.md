# Logs Demo — Fluentd

Deploys **Fluentd** as a Kubernetes DaemonSet using the `fluent/helm-charts` chart.
Collects container logs and forwards them to Kloudfuse via the HTTP output plugin.

## How it works

- Fluentd collects container logs via its default input configuration.
- The `kubernetes_metadata` filter enriches records with pod, namespace, and container fields.
- Logs are delivered to `https://<kloudfuse-hostname>/ingester/v1/fluentd` using the HTTP output plugin.

## Prerequisites

- Helm 3 installed.
- The `logs-demo` pod from [`../log-emitter/`](../log-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the header.

## Deploy

```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update

# Replace <kloudfuse-hostname> and <token> in helm-values.yaml first, then:
helm upgrade --install fluentd fluent/fluentd \
  -f helm-values.yaml \
  --namespace logging \
  --create-namespace
```

## Verify logs in Kloudfuse

Logs are stored in the **Logs store**. Query in the Kloudfuse UI:

```
source="fluentd"
```

Filter by Kubernetes namespace:

```
source="fluentd" namespace="$NAMESPACE"
```

Filter by log level:

```
source="fluentd" level="ERROR"
```

## Tear down

```bash
helm uninstall fluentd -n logging
```
