# APM Demo — Elastic APM Agent (Python)

Deploys a Python pod instrumented with the **Elastic APM Python agent**.
Emits one transaction per second (`GET /demo`) with a child `db.query` span,
forwarded to Kloudfuse via the Elastic APM intake API.

## How it works

- The `elastic-apm` Python agent captures transactions and spans as they execute.
- It batches them and POSTs gzip-compressed NDJSON to `https://<kloudfuse-hostname>/ingester/intake/v2/events`.
- `ELASTIC_APM_SERVER_URL` is set to the Kloudfuse ingester root — the agent appends `/intake/v2/events` automatically.
- `ELASTIC_APM_SECRET_TOKEN` is passed as `Authorization: Bearer <token>` by the agent.

## Prerequisites

- The `kloudfuse-api-key` secret deployed in the target namespace:
  ```bash
  kubectl create secret generic kloudfuse-api-key \
    --from-literal=value=<token> \
    -n $NAMESPACE
  ```
- If auth is not enabled, remove the `ELASTIC_APM_SECRET_TOKEN` env var from `manifest.yaml`.

## Deploy

```bash
# Replace <KFUSE_CLUSTER_DNS> in manifest.yaml first, then:
kubectl apply -f manifest.yaml
```

## Verify traces in Kloudfuse

In the Kloudfuse UI, navigate to **APM > Services** — `demo-elastic-service` appears within
a minute of the first transaction being flushed.

To query directly:

```
source="apm" service.name="demo-elastic-service"
```

## Key caveats

- **Do not append `/intake/v2/events` to `ELASTIC_APM_SERVER_URL`** — the agent appends it automatically. Including it in the URL results in double-path requests that return 404.
- **`ELASTIC_APM_SERVER_URL` must end at `/ingester`** — not `/ingester/`.
- The agent also fetches `/ingester/config/v1/agents` at startup for remote configuration. Kloudfuse returns 404 for this endpoint — this is harmless and does not affect trace delivery.

## Tear down

```bash
kubectl delete pod apm-demo-elastic -n $NAMESPACE
```
