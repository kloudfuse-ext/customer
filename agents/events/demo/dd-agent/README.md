# Events Demo — Datadog Agent

Deploys the **Datadog Cluster Agent + node Agents** via Helm to collect Kubernetes Events and forward
them to Kloudfuse. The Cluster Agent watches the Kubernetes API server for events; node agents forward
process-level and container lifecycle events.

## How it works

- The **Cluster Agent** collects pod scheduling, node condition, and deployment rollout events via the
  Kubernetes API (`use_v2_api.events: true`).
- The **node agents** forward process-level events via `process_config.events_dd_url`.
- All event data is forwarded to `https://<kloudfuse-hostname>/ingester`.

## Prerequisites

- Helm 3 installed.
- Datadog Agent version **7.41 or higher** and Helm chart version **3.1.10 or higher**.
- The `events-demo` pod from [`../event-emitter/`](../event-emitter/) deployed and running.
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

## Verify events in Kloudfuse

Kubernetes events collected by the Datadog Agent are stored in the **Events store** (not Logs).
Query via the `/events-query` GraphQL API:

```graphql
{
  events(
    durationSecs: 300,
    filter: { and: [{eq: {name: "@source", value: "kubernetes"}}] },
    timestamp: "<ISO-8601-timestamp>",
    limit: 20
  ) {
    id title text severity source eventType host
    labels { name value }
    timestamp
  }
}
```

Events emitted by the `events-demo` pod will appear with:
- `source: "kubernetes"`
- `eventType: "kubernetes_apiserver"`
- `labels` containing `kube_namespace=steve`, `kube_name=events-demo`
- `text` containing the reason (`DemoHeartbeat`, `DemoWarning`, `DemoInfo`)

> **Note:** These events appear in the *Events* store, not in *Logs*. This is different from the OTel path — see [`../otel/`](../otel/).

## Tear down

```bash
helm uninstall datadog-agent -n datadog-agent
kubectl delete namespace datadog-agent
```
