#!/usr/bin/env bash
# =============================================================================
# GCP Logs → Kloudfuse Demo — Teardown
# =============================================================================
# Removes all GCP and Kubernetes resources created by setup.sh:
#   • Kubernetes secret
#   • Service account (and its keys)
#   • Log sink
#   • Pub/Sub subscription
#   • Pub/Sub topic
#   • Local credentials file
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — must match what was used in setup.sh
# ---------------------------------------------------------------------------
PROJECT_ID="${GCP_PROJECT_ID:?Please export GCP_PROJECT_ID}"
KFUSE_NAMESPACE="${KFUSE_NAMESPACE:-kfuse}"
KUBECONTEXT="${KUBECONTEXT:-}"

TOPIC_NAME="kloudfuse-logs"
SUBSCRIPTION_NAME="kloudfuse-gcp-subscription"
SINK_NAME="kloudfuse-logs-sink"
SA_NAME="kloudfuse-gcp"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
CREDENTIALS_FILE="kloudfuse-gcp-credentials.json"
K8S_SECRET_NAME="kfuse-gcp-credentials"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
warn()  { echo "[WARN]  $*"; }

kubectl_cmd() {
  if [[ -n "${KUBECONTEXT}" ]]; then
    kubectl --context="${KUBECONTEXT}" "$@"
  else
    kubectl "$@"
  fi
}

# ---------------------------------------------------------------------------
# Kubernetes secret
# ---------------------------------------------------------------------------
info "Deleting Kubernetes secret '${K8S_SECRET_NAME}'..."
if kubectl_cmd get secret "${K8S_SECRET_NAME}" -n "${KFUSE_NAMESPACE}" >/dev/null 2>&1; then
  kubectl_cmd delete secret "${K8S_SECRET_NAME}" -n "${KFUSE_NAMESPACE}"
  ok "Secret deleted."
else
  warn "Secret '${K8S_SECRET_NAME}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Log sink
# ---------------------------------------------------------------------------
info "Deleting log sink '${SINK_NAME}'..."
if gcloud logging sinks describe "${SINK_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud logging sinks delete "${SINK_NAME}" --project="${PROJECT_ID}" --quiet
  ok "Log sink deleted."
else
  warn "Log sink '${SINK_NAME}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Pub/Sub subscription
# ---------------------------------------------------------------------------
info "Deleting Pub/Sub subscription '${SUBSCRIPTION_NAME}'..."
if gcloud pubsub subscriptions describe "${SUBSCRIPTION_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud pubsub subscriptions delete "${SUBSCRIPTION_NAME}" --project="${PROJECT_ID}" --quiet
  ok "Subscription deleted."
else
  warn "Subscription '${SUBSCRIPTION_NAME}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Pub/Sub topic
# ---------------------------------------------------------------------------
info "Deleting Pub/Sub topic '${TOPIC_NAME}'..."
if gcloud pubsub topics describe "${TOPIC_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud pubsub topics delete "${TOPIC_NAME}" --project="${PROJECT_ID}" --quiet
  ok "Topic deleted."
else
  warn "Topic '${TOPIC_NAME}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Service account
# ---------------------------------------------------------------------------
info "Removing IAM binding for '${SA_EMAIL}'..."
gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.subscriber" \
  --quiet >/dev/null 2>&1 || warn "IAM binding not found — skipping."

info "Deleting service account '${SA_EMAIL}'..."
if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts delete "${SA_EMAIL}" --project="${PROJECT_ID}" --quiet
  ok "Service account deleted."
else
  warn "Service account '${SA_EMAIL}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Local credentials file
# ---------------------------------------------------------------------------
if [[ -f "${CREDENTIALS_FILE}" ]]; then
  info "Removing local credentials file '${CREDENTIALS_FILE}'..."
  rm -f "${CREDENTIALS_FILE}"
  ok "Credentials file removed."
else
  warn "Credentials file '${CREDENTIALS_FILE}' not found — skipping."
fi

echo
ok "Teardown complete for project: ${PROJECT_ID}"
echo
echo "Remember to revert any changes made to custom-values.yaml and"
echo "run a Helm upgrade to disable the GCP log pipeline in Kloudfuse."
