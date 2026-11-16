# Events Demo — OpenTelemetry Collector

Deploys the **OTel Collector Contrib** as a single-replica **Deployment** to collect
Kubernetes Events via the `k8s_events` receiver and forward them to Kloudfuse.

> **Note:** This example collects events only, and runs one replica so each event is sent once.
> To collect logs, metrics, events and Kubernetes objects from one install, use
> [`agents/kubernetes/otel`](../../../kubernetes/otel/). It runs the Collector as a DaemonSet and
> uses leader election, which the `k8s_events` receiver supports from Collector 0.137.0, so events
> are still sent once.

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

OTel Kubernetes events appear in the **Events** view, with source `kubernetes` and the label
`kf_events_agent=otlp`. Filter the Events view by:

```
kf_events_agent = otlp
```

Add `kube_namespace = $NAMESPACE` to see one namespace. Events emitted by the `events-demo` pod
appear with the event reason and message.

> **Note:** Checked on Kloudfuse 4.3. Events from the Datadog Agent path appear in the same view —
> see [`../dd-agent/`](../dd-agent/).

## Tear down

```bash
helm uninstall otel-events -n otel
```
