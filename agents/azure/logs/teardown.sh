#!/usr/bin/env bash
# =============================================================================
# Azure Logs → Kloudfuse Demo — Teardown
# =============================================================================
# Removes all Azure resources created by setup.sh:
#   • Subscription-level diagnostic settings
#   • Function App, Storage Account, App Service Plan
#   • Event Hub Namespace (and all hubs within it)
#   • Resource Group
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — must match what was used in setup.sh
# ---------------------------------------------------------------------------
AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:?Please export AZURE_SUBSCRIPTION_ID}"
RESOURCE_GROUP="${RESOURCE_GROUP:-kloudfuse-logs-rg}"
EVENTHUB_NAMESPACE="${EVENTHUB_NAMESPACE:-kloudfuse-logs}"
EVENTHUB_NAME="${EVENTHUB_NAME:-kloudfuse}"
DIAG_SETTING_NAME="${DIAG_SETTING_NAME:-kloudfuse-activity-logs}"

# If FUNCTION_APP_NAME is not set, try to find it in the resource group
FUNCTION_APP_NAME="${FUNCTION_APP_NAME:-}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
warn()  { echo "[WARN]  $*"; }

# ---------------------------------------------------------------------------
# Subscription-level diagnostic settings
# ---------------------------------------------------------------------------
info "Removing subscription-level diagnostic setting '${DIAG_SETTING_NAME}'..."
az monitor diagnostic-settings subscription delete \
  --name "${DIAG_SETTING_NAME}" \
  --yes 2>/dev/null && ok "Diagnostic setting removed." || warn "Not found — skipping."

# ---------------------------------------------------------------------------
# Resource Group (deletes all resources within it)
# ---------------------------------------------------------------------------
info "Deleting resource group '${RESOURCE_GROUP}' and all resources within it..."
if az group show --name "${RESOURCE_GROUP}" >/dev/null 2>&1; then
  az group delete \
    --name "${RESOURCE_GROUP}" \
    --yes \
    --no-wait
  ok "Resource group deletion initiated (runs asynchronously)."
else
  warn "Resource group '${RESOURCE_GROUP}' not found — skipping."
fi

echo
ok "Teardown complete."
echo "Note: Resource group deletion runs asynchronously. Check status with:"
echo "  az group show --name ${RESOURCE_GROUP} --query properties.provisioningState -o tsv"
