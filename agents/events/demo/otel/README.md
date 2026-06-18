# Events Demo — OpenTelemetry Collector

Deploys the **OTel Collector Contrib** as a single-replica **Deployment** (not DaemonSet) to collect
Kubernetes Events via the `k8s_events` receiver and forward them to Kloudfuse.

> **Important:** The Collector must be deployed as a Deployment, not a DaemonSet.
> Running as a DaemonSet causes duplicate events due to upstream
> [issue #42266](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/42266).

## How it works

- The `k8s_events` receiver watches the Kubernetes API server for cluster events.
- A `resource/k8s_events` processor tags each event with `kf_events_agent=otlp`.
- Events are exported to `https://<kloudfuse-hostname>/ingester/otlp/k8s_events` — a dedicated
  endpoint that Kloudfuse treats as Kubernetes events, not log records.
- The events pipeline is separate from any logs pipeline (required — do not merge them).

## Prerequisites

- Helm 3 installed.
- OTel Collector Contrib version **0.130.0 or later**.
- The `events-demo` pod from [`../event-emitter/`](../event-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` in `helm-values.yaml`
  or remove the `Kf-Api-Key` header if auth is not enabled.

## Deploy

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Replace <kloudfuse-hostname> and <token> in helm-values.yaml first, then:
helm upgrade --install otel-events open-telemetry/opentelemetry-collector \
  -f helm-values.yaml \
  --namespace otel \
  --create-namespace
```

## Verify events in Kloudfuse

OTel Kubernetes events are stored in the **Logs store** (not the Events store), tagged with `kf_events_agent=otlp`.
Query via the Loki API:

```logql
{kf_events_agent="otlp"}
```

Filter to a specific namespace:

```logql
{kf_events_agent="otlp", k8s_namespace_name="$NAMESPACE"}
```

Events emitted by the `events-demo` pod will appear as log records with the event reason and message in the log body.

> **Note:** These events appear in *Logs*, not in the *Events* explorer. This is different from the Datadog Agent path — see [`../dd-agent/`](../dd-agent/).

## Tear down

```bash
helm uninstall otel-events -n otel
```
