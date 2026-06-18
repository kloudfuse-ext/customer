# APM Demo — New Relic Agent (Python)

Deploys a Python pod instrumented with the **New Relic Python agent**.
Emits one background task per second (`demo/loop`) with a child `db/query` span,
forwarded to Kloudfuse via the New Relic collector protocol.

## How it works

- The New Relic Python agent connects to `https://<kloudfuse-hostname>/agent_listener/invoke_raw_method`.
- It performs a `preconnect` → `connect` handshake then sends compressed metric and span batches on each harvest cycle (default: 60 seconds).
- `NEW_RELIC_HOST` must be the bare hostname — no `https://` prefix, no trailing slash, no path.
  The agent constructs the full collector URL internally.
- `NEW_RELIC_LICENSE_KEY` is used to authenticate each request.

## Prerequisites

- The `kloudfuse-api-key` secret deployed in the target namespace:
  ```bash
  kubectl create secret generic kloudfuse-api-key \
    --from-literal=value=<token> \
    -n $NAMESPACE
  ```
- If auth is not enabled, remove the `NEW_RELIC_LICENSE_KEY` env var from `manifest.yaml`.

## Deploy

```bash
# Replace <KFUSE_CLUSTER_DNS> in manifest.yaml first, then:
kubectl apply -f manifest.yaml
```

## Verify traces in Kloudfuse

Data arrives after the first harvest cycle (~60 seconds after startup). In the Kloudfuse UI,
navigate to **APM > Services** — `demo-newrelic-service` appears once the first harvest completes.

To query directly:

```
source="apm" service.name="demo-newrelic-service"
```

## Key caveats

- **`NEW_RELIC_HOST` is the bare hostname only** — `<kloudfuse-hostname>`, not `https://<kloudfuse-hostname>` or `<kloudfuse-hostname>/ingester`.
- **Data arrives after the harvest cycle** — the agent buffers data locally and flushes every 60 seconds by default. Traces do not appear immediately.
- **`get_agent_commands` response mismatch** — after connecting, the agent polls `/agent_listener/invoke_raw_method?method=get_agent_commands`. Kloudfuse returns a response in a slightly different format than New Relic HQ, causing a `TypeError` in the agent's command parser on each harvest cycle. This is a non-fatal error and does not affect trace or metric delivery. Traces arrive in Kloudfuse normally.
- **OTLP host warning at startup** — the agent logs `Unable to find corresponding OTLP host using default otlp.nr-data.net`. This is harmless; Kloudfuse receives data via the collector protocol, not OTLP.

## Tear down

```bash
kubectl delete pod apm-demo-newrelic -n $NAMESPACE
```
