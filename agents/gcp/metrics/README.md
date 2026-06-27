# GCP Metrics → Kloudfuse Demo

Demonstrates end-to-end ingestion of GCP Cloud Monitoring metrics into the Kloudfuse platform at **https://\<kloudfuse-hostname\>/** using the Prometheus Stackdriver Exporter.

## How it works

```
GCP Cloud Monitoring Metrics API
  └─ Prometheus Stackdriver Exporter (pod inside GKE)
       └─ Prometheus scrape  ──▶  Kloudfuse
                                      └─ Metrics Explorer UI
```

1. The Stackdriver Exporter pod polls the Cloud Monitoring Metrics API on a configurable interval.
2. It exposes results in Prometheus format.
3. Kloudfuse scrapes the exporter and stores metrics.
4. Metrics appear in the Kloudfuse Metrics Explorer prefixed with `gcp.`.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| `gcloud` CLI | Authenticated via `gcloud auth login` |
| `kubectl` | Configured to reach your Kloudfuse GKE cluster |
| `curl`, `jq` | Standard utilities |
| GCP project | With billing enabled |
| Kloudfuse | Running on GKE; namespace defaults to `kfuse` |

---

## Environment variables

Export these before running any script:

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export KLOUDFUSE_URL="https://<kloudfuse-hostname>"
export KLOUDFUSE_SA_TOKEN="<your-kloudfuse-service-account-token>"

# Optional overrides (defaults shown):
export KFUSE_NAMESPACE="kfuse"
export KUBECONTEXT=""          # blank = use current kubectl context

# Comma-separated list of GCP metric type prefixes to collect
export METRIC_PREFIXES="compute.googleapis.com,container.googleapis.com,storage.googleapis.com,pubsub.googleapis.com"

# Set to "true" to also assign roles/compute.viewer for label enrichment
export ENABLE_ENRICHMENT="true"

# Space-separated list of GCP zones for enrichment
export GCP_ZONES="us-central1-a us-central1-b"
```

---

## Setup

```bash
chmod +x setup.sh teardown.sh
./setup.sh
```

The script will:

1. Enable the Cloud Monitoring and Compute APIs.
2. Create the GCP service account `kloudfuse-gcp`.
3. Assign `roles/monitoring.viewer` (and `roles/compute.viewer` if enrichment is enabled).
4. Download a JSON key to `kloudfuse-gcp-credentials.json`.
5. Create a Kubernetes secret `kfuse-gcp-credentials` in the `kfuse` namespace.
6. Print the Helm values snippet to add to `custom-values.yaml`.
7. Verify Cloud Monitoring API access and check if GCP metrics are already in Kloudfuse.

### After setup — Helm upgrade

Copy the Helm values snippet printed by the script into your `custom-values.yaml`, then run a Helm upgrade on your Kloudfuse installation. The Stackdriver Exporter pod will start and begin scraping metrics.

> **Note:** The first metrics appear approximately one scrape interval (≈5 minutes) after the exporter pod starts.

---

## Metric prefixes

Control which GCP services are scraped via `METRIC_PREFIXES`:

| Prefix | GCP service |
|---|---|
| `compute.googleapis.com` | Compute Engine (VMs, disks, networking) |
| `container.googleapis.com` | Google Kubernetes Engine |
| `storage.googleapis.com` | Cloud Storage |
| `cloudsql.googleapis.com` | Cloud SQL |
| `run.googleapis.com` | Cloud Run |
| `pubsub.googleapis.com` | Cloud Pub/Sub |
| `kubernetes.io/node` | GKE node metrics |

---

## Verify in the Kloudfuse UI

1. Open **https://\<kloudfuse-hostname\>/**.
2. Click **Metrics** → **Explorer**.
3. In the metric search field, type `gcp.` to list all ingested GCP metrics.

Metrics follow the naming convention:

| Cloud Monitoring metric | Kloudfuse metric name |
|---|---|
| `compute.googleapis.com/instance/cpu/utilization` | `gcp.compute.instance.cpu.utilization` |
| `container.googleapis.com/container/cpu/usage_time` | `gcp.container.container.cpu.usage_time` |
| `storage.googleapis.com/api/request_count` | `gcp.storage.api.request_count` |
| `pubsub.googleapis.com/topic/send_message_operation_count` | `gcp.pubsub.topic.send_message_operation_count` |

---

## Teardown

Removes the GCP service account, IAM bindings, Kubernetes secret, and local credentials file:

```bash
./teardown.sh
```

After teardown, revert the changes in `custom-values.yaml` and run a Helm upgrade to disable the Stackdriver Exporter and metrics enrichment.

---

## Troubleshooting

### Stackdriver Exporter pod is in CrashLoopBackOff

```bash
kubectl logs -n kfuse -l app=prometheus-stackdriver-exporter --tail=50
```

| Error | Resolution |
|---|---|
| `could not find default credentials` | Secret missing or `credentials.json` key absent — re-run `setup.sh` |
| `Error 403: caller does not have permission` | Service account lacks `roles/monitoring.viewer` — re-run `setup.sh` |
| `rpc error: code = InvalidArgument` | `projectId` doesn't match an active GCP project |

### No GCP metrics appear in Kloudfuse

```bash
# Confirm the exporter pod is running
kubectl get pods -n kfuse -l app=prometheus-stackdriver-exporter

# Check for scrape errors
kubectl logs -n kfuse -l app=prometheus-stackdriver-exporter | grep -i error

# List available compute metrics to confirm API access
gcloud monitoring metrics list \
  --project=$GCP_PROJECT_ID \
  --filter="metric.type:compute.googleapis.com" \
  --limit=5
```

### Enrichment labels not appearing on metrics

```bash
# Confirm enrichmentEnabled includes gcp in custom-values.yaml
# Check ingester logs
kubectl logs -n kfuse -l app=ingester | grep -i "gcp\|enrich\|error"
```

New labels can take up to `gcpScrapeIntervalMinutes` (default: 30 min) to appear.

---

## Resources

- [Prometheus Stackdriver Exporter](https://github.com/prometheus-community/stackdriver_exporter)
- [Google Cloud metrics reference](https://cloud.google.com/monitoring/api/metrics_gcp)
- [Kloudfuse GCP Metrics documentation](https://docs.kloudfuse.io/data-collection/cloud-services/gcp/metrics)
