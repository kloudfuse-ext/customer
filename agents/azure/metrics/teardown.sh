#!/usr/bin/env bash
# =============================================================================
# Azure Metrics → Kloudfuse Demo — Teardown
# =============================================================================
# Removes all Azure and Kubernetes resources created by setup.sh:
#   • Kubernetes secret
#   • Service Principal and its role assignment
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — must match what was used in setup.sh
# ---------------------------------------------------------------------------
AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:?Please export AZURE_SUBSCRIPTION_ID}"
KFUSE_NAMESPACE="${KFUSE_NAMESPACE:-kfuse}"
KUBECONTEXT="${KUBECONTEXT:-}"

SP_NAME="kloudfuse-cloud-exporter"
K8S_SECRET_NAME="azure-cloud-exporter-credentials"

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
# Role assignment
# ---------------------------------------------------------------------------
SP_APP_ID=$(az ad sp list --display-name "${SP_NAME}" --query "[0].appId" -o tsv 2>/dev/null || true)

if [[ -n "${SP_APP_ID}" && "${SP_APP_ID}" != "None" ]]; then
  info "Removing Monitoring Reader role from ${SP_NAME}..."
  az role assignment delete \
    --assignee "${SP_APP_ID}" \
    --role "Monitoring Reader" \
    --scope "/subscriptions/${AZURE_SUBSCRIPTION_ID}" \
    --yes 2>/dev/null || warn "Role assignment not found — skipping."
  ok "Role assignment removed."

  # ---------------------------------------------------------------------------
  # Service Principal
  # ---------------------------------------------------------------------------
  info "Deleting Service Principal '${SP_NAME}'..."
  az ad sp delete --id "${SP_APP_ID}" 2>/dev/null || warn "SP not found — skipping."
  ok "Service Principal deleted."
else
  warn "Service Principal '${SP_NAME}' not found — skipping."
fi

echo
ok "Teardown complete."
echo
echo "Remember to revert the azure-metrics-exporter section in custom-values.yaml and"
echo "run a Helm upgrade to disable the Cloud Exporter in Kloudfuse."
