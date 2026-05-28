# Host Demo

Demonstrates collecting metrics, logs, and traces from a **standalone host or VM**
(e.g. AWS EC2, GCP instance, Azure VM) using a local agent installed directly on the host.

Unlike the Kubernetes demos, the agent runs as a system service on the host — not as a DaemonSet.
The `host-demo` pod runs with `hostNetwork: true` so it can send telemetry to `localhost`,
where the local agent is listening.

## What gets emitted

The `host-demo` pod (`manifest.yaml`) emits all three signal types every second:

| Signal | What | Destination |
|--------|------|-------------|
| **Traces** | `handle_request` (SERVER) → `db_query` (CLIENT) spans | Local agent OTLP receiver on `localhost:4318` |
| **Metrics** | `demo_requests_total`, `demo_errors_total`, `demo_active_connections`, `demo_request_duration_seconds` | Local agent OTLP receiver on `localhost:4318` |
| **Logs** | Structured JSON — INFO, WARNING, ERROR log records | stdout → collected by agent from container log files |

The local agent also collects **host-level metrics** (CPU, memory, disk, network) independently of the pod.

## Choose your agent

| Directory | Agent | Install method |
|-----------|-------|---------------|
| [`dd-agent/`](dd-agent/) | Datadog Agent 7 | `install_script_agent7.sh` — runs as a systemd service |
| [`otel/`](otel/) | OTel Collector Contrib | `.deb` / `.rpm` package — runs as a systemd service |

Both agents listen for OTLP on `localhost:4318` (HTTP) and `localhost:4317` (gRPC).

## Quick start

```bash
# 1. Install the agent on the host (see dd-agent/README.md or otel/README.md)

# 2. Deploy the demo pod
#    Replace <namespace> in manifest.yaml first, then:
kubectl apply -f manifest.yaml

# 3. Confirm the pod is running
kubectl logs host-demo -n <namespace> -f
```

## How hostNetwork works

```
┌─────────────────────────────────────────┐
│  Kubernetes Node / VM                   │
│                                         │
│  ┌──────────────┐    OTLP HTTP          │
│  │  host-demo   │ ──:4318──────────┐   │
│  │  pod         │                  ▼   │
│  │  (hostNet)   │    ┌─────────────────┐│
│  └──────────────┘    │  Local Agent    ││
│                      │  (dd-agent or   ││
│                      │   otel)         ││
│                      └────────┬────────┘│
│                               │ OTLP/HTTPS
└───────────────────────────────┼─────────┘
                                ▼
                    Kloudfuse Ingester
                    https://<kloudfuse-hostname>
```
