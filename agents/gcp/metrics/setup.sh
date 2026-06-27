#!/usr/bin/env bash
# =============================================================================
# GCP Metrics → Kloudfuse Demo — Setup
# =============================================================================
# Creates all GCP-side resources required for the Kloudfuse metrics integration:
#   • Service account with monitoring.viewer (and optionally compute.viewer)
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
KFUSE_NAMESPACE="${KFUSE_NAMESPACE:-kfuse}"
KUBECONTEXT="${KUBECONTEXT:-}"          # leave blank to use current context

# Comma-separated list of GCP metric type prefixes to collect.
# See: https://cloud.google.com/monitoring/api/metrics_gcp
METRIC_PREFIXES="${METRIC_PREFIXES:-compute.googleapis.com,container.googleapis.com,storage.googleapis.com,pubsub.googleapis.com}"

# Set to "true" to also assign roles/compute.viewer for enrichment
ENABLE_ENRICHMENT="${ENABLE_ENRICHMENT:-true}"

# Zones used for enrichment (space-separated)
GCP_ZONES="${GCP_ZONES:-us-central1-a us-central1-b}"

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
gcloud services enable monitoring.googleapis.com compute.googleapis.com \
  --project="${PROJECT_ID}" --quiet
ok "APIs enabled."

# ---------------------------------------------------------------------------
# Step 2 — Service account
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

# ---------------------------------------------------------------------------
# Step 3 — IAM roles
# ---------------------------------------------------------------------------
info "Assigning roles/monitoring.viewer to ${SA_EMAIL}..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/monitoring.viewer" \
  --quiet >/dev/null
ok "roles/monitoring.viewer assigned."

if [[ "${ENABLE_ENRICHMENT}" == "true" ]]; then
  info "Assigning roles/compute.viewer (required for enrichment)..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/compute.viewer" \
    --quiet >/dev/null
  ok "roles/compute.viewer assigned."
fi

# ---------------------------------------------------------------------------
# Step 4 — Service account JSON key
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
# Step 5 — Kubernetes secret
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
# Step 6 — Print Helm values snippet
# ---------------------------------------------------------------------------
ZONES_YAML=$(echo "${GCP_ZONES}" | tr ' ' '\n' | sed 's/^/          - "/' | sed 's/$/"/')

cat <<HELM

=============================================================================
Add the following to your custom-values.yaml, then run a Helm upgrade:
=============================================================================

global:
  cloud-exporter:
    enabled: true
  enrichmentEnabled:
    - gcp
  gcpConfig:
    secretName: "${K8S_SECRET_NAME}"

kfuse-cloud-exporter:
  prometheus-stackdriver-exporter:
    enabled: true
    stackdriver:
      httpTimeout: 30s
      maxRetries: 3
      projectId: "${PROJECT_ID}"
      metrics:
        typePrefixes: "${METRIC_PREFIXES}"

ingester:
  config:
    gcpScrapeIntervalMinutes: 30
    gcpProjectConfigs:
      - projectId: "${PROJECT_ID}"
        zones:
${ZONES_YAML}
        services:
          - "GCE"

=============================================================================
HELM

# ---------------------------------------------------------------------------
# Step 7 — Verify: list available metrics in the project
# ---------------------------------------------------------------------------
info "Verifying Cloud Monitoring API access — listing sample Compute metrics..."
SAMPLE=$(gcloud monitoring metrics list \
  --project="${PROJECT_ID}" \
  --filter="metric.type:compute.googleapis.com" \
  --limit=3 \
  --format='value(name)' 2>/dev/null || true)

if [[ -n "${SAMPLE}" ]]; then
  ok "Cloud Monitoring API is accessible. Sample metrics:"
  echo "${SAMPLE}" | sed 's/^/        /'
else
  warn "No compute metrics returned. The service account may need a few seconds for IAM to propagate."
fi

# ---------------------------------------------------------------------------
# Step 8 — Query Kloudfuse API (after Helm upgrade and first scrape interval)
# ---------------------------------------------------------------------------
info "Checking Kloudfuse metrics API for existing GCP metrics..."
HTTP_STATUS=$(curl -s -o /tmp/kf_metrics_check.json -w "%{http_code}" \
  -H "Authorization: Bearer ${KLOUDFUSE_SA_TOKEN}" \
  "${KLOUDFUSE_URL}/api/v1/label/__name__/values?match%5B%5D=%7B__name__%3D~%22gcp%5C%5C..%2B%22%7D" 2>/dev/null || echo "000")

if [[ "${HTTP_STATUS}" == "200" ]]; then
  GCP_METRICS=$(jq -r '.data[]?' /tmp/kf_metrics_check.json 2>/dev/null | head -5 || true)
  if [[ -n "${GCP_METRICS}" ]]; then
    ok "GCP metrics already present in Kloudfuse:"
    echo "${GCP_METRICS}" | sed 's/^/        /'
  else
    warn "Kloudfuse API is reachable but no gcp.* metrics found yet."
    warn "Apply the Helm values snippet above, run a Helm upgrade, and wait one scrape interval (≈5 min)."
  fi
else
  warn "Kloudfuse API returned HTTP ${HTTP_STATUS}."
  warn "Apply the Helm values snippet, run a Helm upgrade, then re-run this check:"
  echo "  curl -H 'Authorization: Bearer ${KLOUDFUSE_SA_TOKEN}' \\"
  echo "    '${KLOUDFUSE_URL}/api/v1/label/__name__/values?match[]=\{__name__=~\"gcp\\..+\"\}'"
fi

rm -f /tmp/kf_metrics_check.json

echo
ok "Setup complete for project: ${PROJECT_ID}"
echo "  SA:          ${SA_EMAIL}"
echo "  K8s secret:  ${K8S_SECRET_NAME} (namespace: ${KFUSE_NAMESPACE})"
echo "  Credentials: ${CREDENTIALS_FILE}  ← keep this file secure"
echo "  Prefixes:    ${METRIC_PREFIXES}"
