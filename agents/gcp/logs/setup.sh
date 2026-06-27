#!/usr/bin/env bash
# =============================================================================
# GCP Logs → Kloudfuse Demo — Setup
# =============================================================================
# Creates all GCP-side resources required for the Kloudfuse log integration:
#   • Pub/Sub topic and pull subscription
#   • Cloud Logging log sink
#   • Service account with pubsub.subscriber role
#   • Service account JSON key
#   • Kubernetes secret in the Kloudfuse namespace
#
# After running this script, apply the printed custom-values.yaml snippet and
# run a Helm upgrade on your Kloudfuse installation to activate the pipeline.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these or export them before running
# ---------------------------------------------------------------------------
PROJECT_ID="${GCP_PROJECT_ID:?Please export GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
KFUSE_NAMESPACE="${KFUSE_NAMESPACE:-kfuse}"
KUBECONTEXT="${KUBECONTEXT:-}"          # leave blank to use current context

TOPIC_NAME="kloudfuse-logs"
SUBSCRIPTION_NAME="kloudfuse-gcp-subscription"
SINK_NAME="kloudfuse-logs-sink"
SA_NAME="kloudfuse-gcp"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
CREDENTIALS_FILE="kloudfuse-gcp-credentials.json"
K8S_SECRET_NAME="kfuse-gcp-credentials"

KLOUDFUSE_URL="${KLOUDFUSE_URL:?Please export KLOUDFUSE_URL (e.g. https://<kloudfuse-hostname>)}"
KLOUDFUSE_SA_TOKEN="${KLOUDFUSE_SA_TOKEN:?Please export KLOUDFUSE_SA_TOKEN}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
warn()  { echo "[WARN]  $*"; }
die()   { echo "[ERROR] $*" >&2; exit 1; }

kubectl_cmd() {
  if [[ -n "${KUBECONTEXT}" ]]; then
    kubectl --context="${KUBECONTEXT}" "$@"
  else
    kubectl "$@"
  fi
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
info "Checking required tools..."
for cmd in gcloud kubectl curl jq; do
  command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' is not installed or not in PATH."
done

info "Verifying gcloud authentication..."
gcloud auth print-access-token >/dev/null 2>&1 || die "Not authenticated. Run: gcloud auth login"

info "Verifying project exists..."
gcloud projects describe "${PROJECT_ID}" --format='value(projectId)' >/dev/null 2>&1 \
  || die "Project '${PROJECT_ID}' not found or not accessible."

# ---------------------------------------------------------------------------
# Step 1 — Enable required APIs
# ---------------------------------------------------------------------------
info "Enabling required GCP APIs..."
gcloud services enable pubsub.googleapis.com logging.googleapis.com \
  --project="${PROJECT_ID}" --quiet
ok "APIs enabled."

# ---------------------------------------------------------------------------
# Step 2 — Pub/Sub topic
# ---------------------------------------------------------------------------
info "Creating Pub/Sub topic: ${TOPIC_NAME}..."
if gcloud pubsub topics describe "${TOPIC_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  warn "Topic '${TOPIC_NAME}' already exists — skipping."
else
  gcloud pubsub topics create "${TOPIC_NAME}" --project="${PROJECT_ID}"
  ok "Topic created."
fi

# ---------------------------------------------------------------------------
# Step 3 — Pull subscription
# ---------------------------------------------------------------------------
info "Creating Pub/Sub subscription: ${SUBSCRIPTION_NAME}..."
if gcloud pubsub subscriptions describe "${SUBSCRIPTION_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  warn "Subscription '${SUBSCRIPTION_NAME}' already exists — skipping."
else
  gcloud pubsub subscriptions create "${SUBSCRIPTION_NAME}" \
    --topic="${TOPIC_NAME}" \
    --project="${PROJECT_ID}" \
    --message-retention-duration=1d \
    --expiration-period=never
  ok "Subscription created."
fi

# ---------------------------------------------------------------------------
# Step 4 — Log sink
# ---------------------------------------------------------------------------
info "Creating log sink: ${SINK_NAME}..."
if gcloud logging sinks describe "${SINK_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  warn "Log sink '${SINK_NAME}' already exists — skipping."
else
  gcloud logging sinks create "${SINK_NAME}" \
    "pubsub.googleapis.com/projects/${PROJECT_ID}/topics/${TOPIC_NAME}" \
    --project="${PROJECT_ID}"
  ok "Log sink created."
fi

# ---------------------------------------------------------------------------
# Step 5 — Grant sink writer permission on the topic
# ---------------------------------------------------------------------------
info "Granting sink writer permission on topic..."
SINK_SA=$(gcloud logging sinks describe "${SINK_NAME}" \
  --project="${PROJECT_ID}" \
  --format='value(writerIdentity)')

gcloud pubsub topics add-iam-policy-binding "${TOPIC_NAME}" \
  --project="${PROJECT_ID}" \
  --member="${SINK_SA}" \
  --role="roles/pubsub.publisher" \
  --quiet >/dev/null
ok "Publisher role granted to sink writer: ${SINK_SA}"

# ---------------------------------------------------------------------------
# Step 6 — Service account
# ---------------------------------------------------------------------------
info "Creating service account: ${SA_NAME}..."
if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  warn "Service account '${SA_EMAIL}' already exists — skipping creation."
else
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="Kloudfuse GCP Integration" \
    --project="${PROJECT_ID}"
  ok "Service account created."
fi

info "Assigning roles/pubsub.subscriber to ${SA_EMAIL}..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.subscriber" \
  --quiet >/dev/null
ok "Role assigned."

# ---------------------------------------------------------------------------
# Step 7 — Service account JSON key
# ---------------------------------------------------------------------------
if [[ -f "${CREDENTIALS_FILE}" ]]; then
  warn "Credentials file '${CREDENTIALS_FILE}' already exists — skipping key creation."
else
  info "Creating service account JSON key..."
  gcloud iam service-accounts keys create "${CREDENTIALS_FILE}" \
    --iam-account="${SA_EMAIL}"
  ok "Key written to ${CREDENTIALS_FILE}."
fi

# ---------------------------------------------------------------------------
# Step 8 — Kubernetes secret
# ---------------------------------------------------------------------------
info "Creating Kubernetes secret '${K8S_SECRET_NAME}' in namespace '${KFUSE_NAMESPACE}'..."
if kubectl_cmd get secret "${K8S_SECRET_NAME}" -n "${KFUSE_NAMESPACE}" >/dev/null 2>&1; then
  warn "Secret '${K8S_SECRET_NAME}' already exists — skipping."
else
  kubectl_cmd create secret generic "${K8S_SECRET_NAME}" \
    --from-file=credentials.json="${CREDENTIALS_FILE}" \
    --namespace "${KFUSE_NAMESPACE}"
  ok "Kubernetes secret created."
fi

# ---------------------------------------------------------------------------
# Step 9 — Print Helm values snippet
# ---------------------------------------------------------------------------
cat <<HELM

=============================================================================
Add the following to your custom-values.yaml, then run a Helm upgrade:
=============================================================================

global:
  enrichmentEnabled:
    - gcp
  gcpConfig:
    secretName: "${K8S_SECRET_NAME}"
    projectId: "${PROJECT_ID}"
    pubsub:
      enabled: true
      subscriptions:
        - projectId: "${PROJECT_ID}"
          subscriptionId: "${SUBSCRIPTION_NAME}"

=============================================================================
HELM

# ---------------------------------------------------------------------------
# Step 10 — Smoke test: publish a test message and verify it lands in Kloudfuse
# ---------------------------------------------------------------------------
info "Publishing a test log message to the Pub/Sub topic..."
gcloud pubsub topics publish "${TOPIC_NAME}" \
  --project="${PROJECT_ID}" \
  --message='{"message":"kloudfuse-logs-demo-test","severity":"INFO","resource":{"type":"global"}}'
ok "Test message published."

info "Waiting 30 seconds for the message to reach Kloudfuse..."
sleep 30

info "Querying Kloudfuse API to confirm log ingestion..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${KLOUDFUSE_SA_TOKEN}" \
  "${KLOUDFUSE_URL}/loki/api/v1/query?query=%7Bsource%3D%22gcp%22%7D&limit=1")

if [[ "${HTTP_STATUS}" == "200" ]]; then
  ok "Kloudfuse API responded HTTP 200 — GCP log source is reachable."
  echo
  echo "Next step: open the Kloudfuse Logs UI and run the FuseQL query:"
  echo '  source="gcp"'
else
  warn "Kloudfuse API returned HTTP ${HTTP_STATUS}."
  warn "The pipeline may still be starting up. Check again in a few minutes or"
  warn "inspect the ingester pod logs:"
  echo "  kubectl logs -n ${KFUSE_NAMESPACE} -l app=ingester --tail=100 | grep -i pubsub"
fi

echo
ok "Setup complete for project: ${PROJECT_ID}"
echo "  Topic:        ${TOPIC_NAME}"
echo "  Subscription: ${SUBSCRIPTION_NAME}"
echo "  Log sink:     ${SINK_NAME}"
echo "  SA:           ${SA_EMAIL}"
echo "  K8s secret:   ${K8S_SECRET_NAME} (namespace: ${KFUSE_NAMESPACE})"
echo "  Credentials:  ${CREDENTIALS_FILE}  ← keep this file secure"
