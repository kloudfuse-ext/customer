#!/usr/bin/env bash
# =============================================================================
# Azure Metrics → Kloudfuse Demo — Setup
# =============================================================================
# Creates all Azure-side resources required for the Kloudfuse metrics integration:
#   • Service Principal with Monitoring Reader role
#   • Kubernetes secret in the Kloudfuse namespace
#
# The Cloud Exporter runs inside the Kloudfuse cluster and polls the Azure
# Monitor Metrics API every 5 minutes using the Service Principal credentials.
# No Azure-side infrastructure beyond the SP is required.
#
# After running this script, apply the printed custom-values.yaml snippet and
# run a Helm upgrade on your Kloudfuse installation to activate the pipeline.
#
# Prerequisites:
#   • az CLI authenticated: az login
#   • kubectl configured for the Kloudfuse cluster
#   • AZURE_SUBSCRIPTION_ID exported
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these or export them before running
# ---------------------------------------------------------------------------
AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:?Please export AZURE_SUBSCRIPTION_ID}"
AZURE_TENANT_ID="${AZURE_TENANT_ID:-}"        # auto-detected if blank
KFUSE_NAMESPACE="${KFUSE_NAMESPACE:-kfuse}"
KUBECONTEXT="${KUBECONTEXT:-}"                # leave blank to use current context

SP_NAME="kloudfuse-cloud-exporter"
K8S_SECRET_NAME="azure-cloud-exporter-credentials"

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
for cmd in az kubectl curl jq; do
  command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' is not installed or not in PATH."
done

info "Verifying az authentication..."
az account show >/dev/null 2>&1 || die "Not authenticated. Run: az login"

info "Setting active subscription to ${AZURE_SUBSCRIPTION_ID}..."
az account set --subscription "${AZURE_SUBSCRIPTION_ID}"
ok "Subscription set."

if [[ -z "${AZURE_TENANT_ID}" ]]; then
  AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)
  info "Auto-detected tenant ID: ${AZURE_TENANT_ID}"
fi

# ---------------------------------------------------------------------------
# Step 1 — Service Principal
# ---------------------------------------------------------------------------
info "Checking for existing Service Principal '${SP_NAME}'..."
EXISTING_SP=$(az ad sp list --display-name "${SP_NAME}" --query "[0].appId" -o tsv 2>/dev/null || true)

if [[ -n "${EXISTING_SP}" && "${EXISTING_SP}" != "None" ]]; then
  warn "Service Principal '${SP_NAME}' already exists (appId: ${EXISTING_SP})."
  warn "Creating a new client secret for the existing SP..."
  SP_JSON=$(az ad app credential reset \
    --id "${EXISTING_SP}" \
    --display-name "kfuse-setup-$(date +%Y%m%d)" \
    --years 1 \
    --output json)
  AZURE_CLIENT_ID=$(echo "${SP_JSON}" | jq -r '.appId')
  AZURE_CLIENT_SECRET=$(echo "${SP_JSON}" | jq -r '.password')
else
  info "Creating Service Principal '${SP_NAME}' with Monitoring Reader role..."
  SP_JSON=$(az ad sp create-for-rbac \
    --name "${SP_NAME}" \
    --role "Monitoring Reader" \
    --scopes "/subscriptions/${AZURE_SUBSCRIPTION_ID}" \
    --output json)
  AZURE_CLIENT_ID=$(echo "${SP_JSON}" | jq -r '.appId')
  AZURE_CLIENT_SECRET=$(echo "${SP_JSON}" | jq -r '.password')
  ok "Service Principal created."
fi

ok "Service Principal: appId=${AZURE_CLIENT_ID}"

# ---------------------------------------------------------------------------
# Step 2 — Kubernetes secret
# ---------------------------------------------------------------------------
info "Creating Kubernetes secret '${K8S_SECRET_NAME}' in namespace '${KFUSE_NAMESPACE}'..."
if kubectl_cmd get secret "${K8S_SECRET_NAME}" -n "${KFUSE_NAMESPACE}" >/dev/null 2>&1; then
  warn "Secret '${K8S_SECRET_NAME}' already exists — deleting and recreating."
  kubectl_cmd delete secret "${K8S_SECRET_NAME}" -n "${KFUSE_NAMESPACE}"
fi

kubectl_cmd create secret generic "${K8S_SECRET_NAME}" \
  --namespace "${KFUSE_NAMESPACE}" \
  --from-literal=AZURE_CLIENT_ID="${AZURE_CLIENT_ID}" \
  --from-literal=AZURE_TENANT_ID="${AZURE_TENANT_ID}" \
  --from-literal=AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET}"
ok "Kubernetes secret created."

# ---------------------------------------------------------------------------
# Step 3 — Print Helm values snippet
# ---------------------------------------------------------------------------
cat <<HELM

=============================================================================
Add the following to your custom-values.yaml, then run a Helm upgrade:
=============================================================================

global:
  cloud-exporter:
    enabled: true

kfuse-cloud-exporter:
  azure-metrics-exporter:
    enabled: true
    subscriptions:
      - ${AZURE_SUBSCRIPTION_ID}
    extraEnv:
      - name: AZURE_CLIENT_ID
        valueFrom:
          secretKeyRef:
            name: ${K8S_SECRET_NAME}
            key: AZURE_CLIENT_ID
      - name: AZURE_TENANT_ID
        valueFrom:
          secretKeyRef:
            name: ${K8S_SECRET_NAME}
            key: AZURE_TENANT_ID
      - name: AZURE_CLIENT_SECRET
        valueFrom:
          secretKeyRef:
            name: ${K8S_SECRET_NAME}
            key: AZURE_CLIENT_SECRET

=============================================================================
HELM

# ---------------------------------------------------------------------------
# Step 4 — Verify: confirm Service Principal can read Azure Monitor metrics
# ---------------------------------------------------------------------------
info "Verifying Service Principal can authenticate and list metrics..."
# Allow a few seconds for IAM to propagate
sleep 10

TOKEN=$(az account get-access-token \
  --resource https://management.azure.com/ \
  --query accessToken -o tsv 2>/dev/null || true)

if [[ -n "${TOKEN}" ]]; then
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    "https://management.azure.com/subscriptions/${AZURE_SUBSCRIPTION_ID}/providers/microsoft.insights/metricDefinitions?api-version=2018-01-01&top=1" 2>/dev/null || echo "000")

  if [[ "${HTTP_STATUS}" == "200" ]]; then
    ok "Azure Monitor Metrics API is accessible."
  else
    warn "Azure Monitor API returned HTTP ${HTTP_STATUS}. IAM may still be propagating — wait 30s and retry."
  fi
fi

# ---------------------------------------------------------------------------
# Step 5 — Query Kloudfuse API for existing Azure metrics
# ---------------------------------------------------------------------------
info "Checking Kloudfuse for existing Azure metrics (after Helm upgrade and first scrape)..."
HTTP_STATUS=$(curl -s -o /tmp/kf_azure_check.json -w "%{http_code}" \
  -H "Authorization: Bearer ${KLOUDFUSE_SA_TOKEN}" \
  "${KLOUDFUSE_URL}/api/v1/label/__name__/values?match%5B%5D=%7B__name__%3D~%22azure%5C%5C..%2B%22%7D" 2>/dev/null || echo "000")

if [[ "${HTTP_STATUS}" == "200" ]]; then
  AZURE_METRICS=$(jq -r '.data[]?' /tmp/kf_azure_check.json 2>/dev/null | head -5 || true)
  if [[ -n "${AZURE_METRICS}" ]]; then
    ok "Azure metrics already present in Kloudfuse:"
    echo "${AZURE_METRICS}" | sed 's/^/        /'
  else
    warn "No azure.* metrics found yet. Apply the Helm values above, run a Helm upgrade, and wait one scrape interval (~5 min)."
  fi
else
  warn "Kloudfuse API returned HTTP ${HTTP_STATUS}."
fi

rm -f /tmp/kf_azure_check.json

echo
ok "Setup complete."
echo "  Subscription:  ${AZURE_SUBSCRIPTION_ID}"
echo "  Tenant:        ${AZURE_TENANT_ID}"
echo "  SP appId:      ${AZURE_CLIENT_ID}"
echo "  K8s secret:    ${K8S_SECRET_NAME} (namespace: ${KFUSE_NAMESPACE})"
echo
echo "Next steps:"
echo "  1. Apply the Helm values snippet above to your custom-values.yaml"
echo "  2. Run a Helm upgrade to enable the Cloud Exporter"
echo "  3. Wait ~5 minutes for the first scrape"
echo "  4. In Kloudfuse Metrics Explorer, search for 'azure.' to confirm ingestion"
