# GCP Logs → Kloudfuse Demo

Demonstrates end-to-end ingestion of GCP Cloud Logging entries into the Kloudfuse platform at **https://\<kloudfuse-hostname\>/** using Cloud Pub/Sub as the transport layer.

## How it works

```
GCP Resources
  └─ Cloud Logging
       └─ Log Sink  ──▶  Pub/Sub Topic
                               └─ Pull Subscription  ──▶  Kloudfuse Ingester
                                                                └─ Log Analytics UI
```

1. GCP services write log entries to Cloud Logging.
2. A Log Sink routes matching entries to a Pub/Sub topic.
3. The Kloudfuse ingester continuously pulls batches from the subscription.
4. Logs appear in the Kloudfuse Log Analytics UI within 30–60 seconds.

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
export GCP_REGION="us-central1"
export KFUSE_NAMESPACE="kfuse"
export KUBECONTEXT=""          # blank = use current kubectl context
```

---

## Setup

```bash
chmod +x setup.sh teardown.sh
./setup.sh
```

The script will:

1. Enable the Pub/Sub and Cloud Logging APIs.
2. Create the Pub/Sub topic `kloudfuse-logs`.
3. Create the pull subscription `kloudfuse-gcp-subscription`.
4. Create a log sink that routes all log entries to the topic.
5. Create a GCP service account `kloudfuse-gcp` with `roles/pubsub.subscriber`.
6. Download a JSON key to `kloudfuse-gcp-credentials.json`.
7. Create a Kubernetes secret `kfuse-gcp-credentials` in the `kfuse` namespace.
8. Print the Helm values snippet to add to `custom-values.yaml`.
9. Publish a test log message and query the Kloudfuse API to confirm ingestion.

### After setup — Helm upgrade

Copy the Helm values snippet printed by the script into your `custom-values.yaml`, then run a Helm upgrade on your Kloudfuse installation. The exact command is in your deployment runbook.

---

## Verify in the Kloudfuse UI

1. Open **https://\<kloudfuse-hostname\>/**.
2. Click **Logs** → **Search**.
3. Set the time picker to **Last 15 minutes**.
4. Click **Advanced Search** and enter:

```fuseql
source="gcp"
```

Any result confirms GCP log records are reaching Kloudfuse.

### Useful FuseQL queries

```fuseql
# All GCP logs
source="gcp"

# Count by resource type
source="gcp" | count by resource.type

# Cloud Audit Logs only
logName="projects/YOUR_PROJECT_ID/logs/cloudaudit.googleapis.com%2Factivity"
```

---

## Teardown

Removes all GCP resources, the Kubernetes secret, and the local credentials file:

```bash
./teardown.sh
```

After teardown, revert the changes in `custom-values.yaml` and run a Helm upgrade to disable the GCP log pipeline.

---

## Troubleshooting

### No messages in the Pub/Sub subscription

```bash
# Confirm the sink is active
gcloud logging sinks describe kloudfuse-logs-sink --project=$GCP_PROJECT_ID

# Pull a test message manually
gcloud pubsub subscriptions pull kloudfuse-gcp-subscription \
  --project=$GCP_PROJECT_ID --limit=1 --auto-ack
```

### Kloudfuse pod cannot pull from Pub/Sub

```bash
# Check the secret contains credentials.json
kubectl get secret kfuse-gcp-credentials -n kfuse \
  -o jsonpath='{.data}' | jq 'keys'

# Check ingester logs
kubectl logs -n kfuse -l app=ingester --tail=100 | grep -i "pubsub\|gcp\|error"
```

### Logs appear in Pub/Sub but not in Kloudfuse

```bash
# Restart the ingester to pick up configuration changes
kubectl rollout restart deployment -n kfuse -l app=ingester
```

---

## Resources

- [GCP Cloud Logging — Configure log sinks](https://cloud.google.com/logging/docs/export/configure_export_v2)
- [GCP Pub/Sub — Create subscriptions](https://cloud.google.com/pubsub/docs/create-subscription)
- [Kloudfuse GCP Logs documentation](https://docs.kloudfuse.io/data-collection/cloud-services/gcp/logs)
