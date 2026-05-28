# Events Demo — Kubernetes Event Emitter

A minimal pod that continuously emits **Kubernetes Events** into the cluster. These events are then
collected by the `dd-agent` or `otel` agents in this demo and forwarded to Kloudfuse.

## How it works

The manifest uses `python:3.12-slim`. On first start the container:

1. Runs `pip install kubernetes` to get the Kubernetes Python client.
2. Writes `emitter.py` to disk.
3. Launches a loop that creates one Kubernetes Event per second via the in-cluster API.

Events are attached to the `events-demo` pod itself and cycle through three types:

| Reason | Type | Message |
|--------|------|---------|
| `DemoHeartbeat` | Normal | Heartbeat — pipeline is active |
| `DemoWarning` | Warning | Synthetic warning — validates Warning-type ingestion |
| `DemoInfo` | Normal | Informational — service health check passed |

## Prerequisites

- `kubectl` configured against your cluster.
- The `steve` namespace must exist, or change `namespace:` in `manifest.yaml` to match your environment.

## Deploy

```bash
kubectl apply -f manifest.yaml
```

## Verify events are being emitted

First startup takes ~20 s while `pip install` runs. Watch the logs:

```bash
kubectl logs events-demo -n steve -f
```

Wait until you see:
```
events-demo starting event loop (1 event/second) on pod events-demo
[2025-01-01T00:00:01Z] Normal/DemoHeartbeat: Demo event emitter heartbeat — cluster events pipeline is active
```

Confirm events appear in the cluster:

```bash
kubectl get events -n steve --field-selector involvedObject.name=events-demo
```

## Next steps

Once the emitter is running, deploy one of the agent configs in this demo to collect and
forward these events to Kloudfuse:

- [`../dd-agent/`](../dd-agent/) — Datadog Agent via Helm → events land in the **Events store** (`source="kubernetes"`)
- [`../otel/`](../otel/) — OpenTelemetry Collector via Helm → events land in **Logs** (`kf_events_agent="otlp"`)

> **Note:** The two agents store events in different places in Kloudfuse. Use the agent that matches
> where you want to query events — Events explorer (dd-agent) or Logs/Loki (otel).

## Tear down

```bash
kubectl delete -f manifest.yaml
```
