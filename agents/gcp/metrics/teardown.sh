#!/usr/bin/env bash
# =============================================================================
# GCP Metrics → Kloudfuse Demo — Teardown
# =============================================================================
# Removes all GCP and Kubernetes resources created by setup.sh:
#   • Kubernetes secret
#   • Service account (and its keys)
#   • IAM role bindings
#   • Local credentials file
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — must match what was used in setup.sh
# ---------------------------------------------------------------------------
PROJECT_ID="${GCP_PROJECT_ID:?Please export GCP_PROJECT_ID}"
KFUSE_NAMESPACE="${KFUSE_NAMESPACE:-kfuse}"
KUBECONTEXT="${KUBECONTEXT:-}"
ENABLE_ENRICHMENT="${ENABLE_ENRICHMENT:-true}"

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
# IAM role bindings
# ---------------------------------------------------------------------------
info "Removing roles/monitoring.viewer from ${SA_EMAIL}..."
gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/monitoring.viewer" \
  --quiet >/dev/null 2>&1 || warn "roles/monitoring.viewer binding not found — skipping."

if [[ "${ENABLE_ENRICHMENT}" == "true" ]]; then
  info "Removing roles/compute.viewer from ${SA_EMAIL}..."
  gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/compute.viewer" \
    --quiet >/dev/null 2>&1 || warn "roles/compute.viewer binding not found — skipping."
fi

# ---------------------------------------------------------------------------
# Service account
# ---------------------------------------------------------------------------
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
echo "run a Helm upgrade to disable the GCP metrics pipeline in Kloudfuse."
