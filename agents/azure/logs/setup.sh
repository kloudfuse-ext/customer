#!/usr/bin/env bash
# =============================================================================
# Azure Logs → Kloudfuse Demo — Setup
# =============================================================================
# Creates all Azure-side resources required for the Kloudfuse log integration:
#   • Event Hub Namespace and Hub
#   • Shared Access Policy with Listen + Send rights
#   • Storage Account and Function App
#   • Deploys the kloudfuse-log-forwarder function (from scripts/azure/index.js)
#   • Subscription-level Diagnostic Settings routing activity logs to the hub
#
# Logs flow: Azure resources → Event Hub → Function App → Kloudfuse /api/v2/logs
#
# Prerequisites:
#   • az CLI authenticated: az login
#   • Azure Functions Core Tools: npm install -g azure-functions-core-tools@4
#   • Node.js 18+
#   • AZURE_SUBSCRIPTION_ID, KLOUDFUSE_URL, KLOUDFUSE_SA_TOKEN exported
#   • The index.js forwarder at: ../../scripts/azure/index.js (relative to this script)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these or export them before running
# ---------------------------------------------------------------------------
AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:?Please export AZURE_SUBSCRIPTION_ID}"
RESOURCE_GROUP="${RESOURCE_GROUP:-kloudfuse-logs-rg}"
LOCATION="${LOCATION:-westus2}"

# Names — storage account must be globally unique (3-24 lowercase alphanumeric)
EVENTHUB_NAMESPACE="${EVENTHUB_NAMESPACE:-kloudfuse-logs}"
EVENTHUB_NAME="${EVENTHUB_NAME:-kloudfuse}"
EVENTHUB_POLICY="${EVENTHUB_POLICY:-kloudfuse-policy}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-kloudfuselogs$(openssl rand -hex 3)}"
FUNCTION_APP_NAME="${FUNCTION_APP_NAME:-kloudfuse-logs-$(openssl rand -hex 3)}"
FUNCTION_NAME="kloudfuse-log-forwarder"
DIAG_SETTING_NAME="kloudfuse-activity-logs"

KLOUDFUSE_URL="${KLOUDFUSE_URL:?Please export KLOUDFUSE_URL (e.g. https://<kloudfuse-hostname>)}"
KLOUDFUSE_SA_TOKEN="${KLOUDFUSE_SA_TOKEN:?Please export KLOUDFUSE_SA_TOKEN}"

# Derive hostname from URL for KF_URL (the forwarder expects hostname only, not full URL)
KF_HOSTNAME=$(echo "${KLOUDFUSE_URL}" | sed 's|https://||' | sed 's|/.*||')

# Path to the maintained index.js forwarder (relative to this script's directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDEX_JS="${SCRIPT_DIR}/../../scripts/azure/index.js"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
warn()  { echo "[WARN]  $*"; }
die()   { echo "[ERROR] $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
info "Checking required tools..."
for cmd in az func node curl jq; do
  command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' is not installed. Install with: npm install -g azure-functions-core-tools@4"
done

[[ -f "${INDEX_JS}" ]] || die "Forwarder not found at: ${INDEX_JS}"

info "Verifying az authentication..."
az account show >/dev/null 2>&1 || die "Not authenticated. Run: az login"

az account set --subscription "${AZURE_SUBSCRIPTION_ID}"
ok "Subscription set to ${AZURE_SUBSCRIPTION_ID}."

# ---------------------------------------------------------------------------
# Step 1 — Resource Group
# ---------------------------------------------------------------------------
info "Creating resource group '${RESOURCE_GROUP}' in ${LOCATION}..."
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --output none
ok "Resource group ready."

# ---------------------------------------------------------------------------
# Step 2 — Event Hub Namespace and Hub
# ---------------------------------------------------------------------------
info "Creating Event Hub Namespace '${EVENTHUB_NAMESPACE}'..."
if az eventhubs namespace show --name "${EVENTHUB_NAMESPACE}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
  warn "Namespace '${EVENTHUB_NAMESPACE}' already exists — skipping."
else
  az eventhubs namespace create \
    --name "${EVENTHUB_NAMESPACE}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --sku Standard \
    --output none
  ok "Namespace created."
fi

info "Creating Event Hub '${EVENTHUB_NAME}'..."
if az eventhubs eventhub show --name "${EVENTHUB_NAME}" --namespace-name "${EVENTHUB_NAMESPACE}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
  warn "Event Hub '${EVENTHUB_NAME}' already exists — skipping."
else
  az eventhubs eventhub create \
    --name "${EVENTHUB_NAME}" \
    --namespace-name "${EVENTHUB_NAMESPACE}" \
    --resource-group "${RESOURCE_GROUP}" \
    --partition-count 4 \
    --message-retention-in-days 1 \
    --output none
  ok "Event Hub created."
fi

info "Creating authorization rule '${EVENTHUB_POLICY}'..."
if az eventhubs namespace authorization-rule show --name "${EVENTHUB_POLICY}" --namespace-name "${EVENTHUB_NAMESPACE}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
  warn "Policy '${EVENTHUB_POLICY}' already exists — skipping."
else
  az eventhubs namespace authorization-rule create \
    --name "${EVENTHUB_POLICY}" \
    --namespace-name "${EVENTHUB_NAMESPACE}" \
    --resource-group "${RESOURCE_GROUP}" \
    --rights Listen Send \
    --output none
  ok "Authorization rule created."
fi

EVENT_HUB_CONNECTION_STRING=$(az eventhubs namespace authorization-rule keys list \
  --name "${EVENTHUB_POLICY}" \
  --namespace-name "${EVENTHUB_NAMESPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query primaryConnectionString -o tsv)

EVENT_HUB_AUTH_RULE_ID=$(az eventhubs namespace authorization-rule show \
  --name "${EVENTHUB_POLICY}" \
  --namespace-name "${EVENTHUB_NAMESPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query id -o tsv)

ok "Event Hub connection string retrieved."

# ---------------------------------------------------------------------------
# Step 3 — Storage Account and Function App
# ---------------------------------------------------------------------------
info "Creating storage account '${STORAGE_ACCOUNT}'..."
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --output none
ok "Storage account created."

info "Creating Function App '${FUNCTION_APP_NAME}'..."
az functionapp create \
  --name "${FUNCTION_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --storage-account "${STORAGE_ACCOUNT}" \
  --consumption-plan-location "${LOCATION}" \
  --runtime node \
  --runtime-version 18 \
  --functions-version 4 \
  --os-type Linux \
  --output none
ok "Function App created."

info "Configuring Function App settings..."
az functionapp config appsettings set \
  --name "${FUNCTION_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --settings \
    "EventHubConnection=${EVENT_HUB_CONNECTION_STRING}" \
    "KF_API_KEY=${KLOUDFUSE_SA_TOKEN}" \
    "KF_URL=${KF_HOSTNAME}" \
  --output none
ok "Settings configured. KF_URL=${KF_HOSTNAME}"

# ---------------------------------------------------------------------------
# Step 4 — Deploy the Function Code
# ---------------------------------------------------------------------------
info "Preparing function deployment package..."
DEPLOY_DIR=$(mktemp -d)
trap "rm -rf ${DEPLOY_DIR}" EXIT

mkdir -p "${DEPLOY_DIR}/${FUNCTION_NAME}"

# host.json
cat > "${DEPLOY_DIR}/host.json" <<'HOST'
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  }
}
HOST

# function.json (EventHub trigger bound to Kfuse-Azure connection)
cat > "${DEPLOY_DIR}/${FUNCTION_NAME}/function.json" <<FUNCJSON
{
  "bindings": [
    {
      "type": "eventHubTrigger",
      "name": "eventHubMessages",
      "direction": "in",
      "eventHubName": "${EVENTHUB_NAME}",
      "connection": "EventHubConnection",
      "cardinality": "many",
      "dataType": "string"
    }
  ]
}
FUNCJSON

# Copy the maintained forwarder
cp "${INDEX_JS}" "${DEPLOY_DIR}/${FUNCTION_NAME}/index.js"

info "Deploying function to '${FUNCTION_APP_NAME}'..."
(cd "${DEPLOY_DIR}" && func azure functionapp publish "${FUNCTION_APP_NAME}" --node)
ok "Function deployed."

# ---------------------------------------------------------------------------
# Step 5 — Subscription-level Diagnostic Settings (activity logs)
# ---------------------------------------------------------------------------
info "Configuring subscription-level diagnostic settings..."
az monitor diagnostic-settings subscription create \
  --name "${DIAG_SETTING_NAME}" \
  --event-hub-name "${EVENTHUB_NAME}" \
  --event-hub-auth-rule "${EVENT_HUB_AUTH_RULE_ID}" \
  --logs '[
    {"category": "Administrative", "enabled": true},
    {"category": "Security",       "enabled": true},
    {"category": "ServiceHealth",  "enabled": true},
    {"category": "Alert",          "enabled": true},
    {"category": "Policy",         "enabled": true}
  ]' \
  --output none 2>/dev/null || warn "Diagnostic setting may already exist — skipping."
ok "Activity log diagnostic settings configured."

# ---------------------------------------------------------------------------
# Step 6 — Smoke test: verify logs reach Kloudfuse
# ---------------------------------------------------------------------------
info "Waiting 60 seconds for the first events to flow..."
sleep 60

info "Querying Kloudfuse for Azure logs..."
HTTP_STATUS=$(curl -s -o /tmp/kf_azure_logs.json -w "%{http_code}" \
  -H "Authorization: Bearer ${KLOUDFUSE_SA_TOKEN}" \
  "${KLOUDFUSE_URL}/loki/api/v1/query?query=%7Bsource%3D%22azure%22%7D&limit=1" 2>/dev/null || echo "000")

if [[ "${HTTP_STATUS}" == "200" ]]; then
  RESULT_COUNT=$(jq '.data.result | length' /tmp/kf_azure_logs.json 2>/dev/null || echo "0")
  if [[ "${RESULT_COUNT}" -gt "0" ]]; then
    ok "Azure logs are flowing into Kloudfuse."
  else
    warn "Kloudfuse API is reachable but no azure logs found yet. Give it another minute."
    warn "Then check the Function App Monitor in the Azure Portal for invocation status."
  fi
else
  warn "Kloudfuse API returned HTTP ${HTTP_STATUS}. Check KLOUDFUSE_URL and KLOUDFUSE_SA_TOKEN."
fi

rm -f /tmp/kf_azure_logs.json

echo
ok "Setup complete."
echo "  Resource group:  ${RESOURCE_GROUP}"
echo "  Event Hub:       ${EVENTHUB_NAMESPACE}/${EVENTHUB_NAME}"
echo "  Function App:    ${FUNCTION_APP_NAME}"
echo "  Diag setting:    ${DIAG_SETTING_NAME} (subscription-level activity logs)"
echo "  Kloudfuse URL:   ${KLOUDFUSE_URL}"
echo
echo "To verify in Kloudfuse Logs UI, run the FuseQL query:"
echo '  source="azure"'
echo
echo "To add resource-level logs for a specific Azure resource, run:"
echo "  az monitor diagnostic-settings create \\"
echo "    --name kloudfuse \\"
echo "    --resource <resource-id> \\"
echo "    --event-hub-name ${EVENTHUB_NAME} \\"
echo "    --event-hub-rule ${EVENT_HUB_AUTH_RULE_ID} \\"
echo "    --logs '[{\"categoryGroup\": \"allLogs\", \"enabled\": true}]' \\"
echo "    --metrics '[{\"category\": \"AllMetrics\", \"enabled\": false}]'"
