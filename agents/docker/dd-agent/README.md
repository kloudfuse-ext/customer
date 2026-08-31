# Docker Demo — Datadog Agent

Runs the **Datadog Agent** as a Docker container alongside a small log-emitting
workload. The Agent collects host and container metrics and tails every
container's stdout (`container_collect_all`), forwarding both to Kloudfuse.

Validated end-to-end against a live Kloudfuse cluster (see **Verify** below):
**metrics and container logs both arrive.** APM traces are configured but were
not exercised in this demo (no instrumented application).

## How it works

- `datadog/datadog.yaml` points the Agent at Kloudfuse (`dd_url`, `logs_dd_url`,
  `apm_dd_url`) and enables container log collection.
- `datadog/Dockerfile` bakes that config into the official `gcr.io/datadoghq/agent:7` image.
- `docker-compose.yaml` runs the Agent plus a `log-emitter` workload.
- Metrics are routed to `/ingester/api/v2/series` via `use_v2_api.series: true`.
  This is **required** — the cluster's `api/v1/series` endpoint is not used.

## Prerequisites

- Docker (Engine or Desktop) with Compose v2.
- The external hostname of your Kloudfuse cluster.
- An ingestion API key (or `kloudfuse` if ingestion auth is disabled).
- Agent version **7.41+**.

## Deploy

```bash
# 1. Set the cluster hostname in datadog/datadog.yaml (replace <kloudfuse-hostname>).

# 2. Provide the API key (required as an env var by the Agent container entrypoint):
export DD_API_KEY=<ingestion-api-key>      # or: export DD_API_KEY=kloudfuse

# 3. Build and start:
docker compose up -d --build

# 4. Confirm the Agent is healthy and flushing:
docker exec datadog-agent agent status | grep -A2 "Last Successful"
```

> **Note on TLS:** `skip_ssl_validation: true` is set because dev clusters often
> present a self-signed or expired certificate. Remove it to enforce TLS validation.

> **Note on `DD_API_KEY`:** The Agent container's entrypoint refuses to start
> without the `DD_API_KEY` environment variable, even though `api_key` is also
> present in `datadog.yaml`.

## Verify

Metrics (Prometheus datasource) — expect a non-zero series count for the demo host:

```bash
curl -sk -G -H "Authorization: Bearer $GRAFANA_TOKEN" \
  --data-urlencode 'query=count({host="docker-demo-host"})' \
  "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<prometheus-uid>/api/v1/query"
```

Logs (Loki datasource) — expect the emitted lines:

```bash
NOW=$(date +%s)000000000; AGO=$(( $(date +%s) - 900 ))000000000
curl -sk -G -H "Authorization: Bearer $GRAFANA_TOKEN" \
  --data-urlencode 'query={source=~".+"} |= "doctest log line"' \
  --data-urlencode "start=$AGO" --data-urlencode "end=$NOW" --data-urlencode "limit=5" \
  "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<loki-uid>/loki/api/v1/query_range"
```

Or in the Kloudfuse UI: **Metrics** → filter `host = docker-demo-host`; **Logs** →
search `doctest log line` (stream labels `container_name=doctest-workload`,
`image_name=alpine`, `source=alpine`).

## Tear down

```bash
docker compose down
```
