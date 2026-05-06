#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# resize_pvc.sh — Resize PVCs for a Kloudfuse StatefulSet
#
# Usage: ./resize_pvc.sh <statefulset-name> <new-size> [namespace]
#
# Example: ./resize_pvc.sh pinot-server-offline 281Gi kfuse
# ---------------------------------------------------------------------------

STS_NAME="${1:-}"
SIZE="${2:-}"
NAMESPACE="${3:-kfuse}"

# --- Validation ------------------------------------------------------------

if [[ -z "$STS_NAME" || -z "$SIZE" ]]; then
  echo "Usage: $0 <statefulset-name> <new-size> [namespace]"
  echo "Example: $0 pinot-server-offline 281Gi kfuse"
  exit 1
fi

if [[ ! "$SIZE" =~ ^[0-9]+(\.[0-9]+)?(Ki|Mi|Gi|Ti|Pi|Ei|K|M|G|T|P|E)?$ ]]; then
  echo "ERROR: Invalid size format '${SIZE}'. Expected a Kubernetes quantity (e.g. 281Gi, 500G, 1Ti)."
  exit 1
fi

if ! kubectl get statefulset "$STS_NAME" -n "$NAMESPACE" &>/dev/null; then
  echo "ERROR: StatefulSet '${STS_NAME}' not found in namespace '${NAMESPACE}'."
  exit 1
fi

# --- Confirmation ----------------------------------------------------------

echo ""
echo "This will resize all PVCs for StatefulSet '${STS_NAME}' in namespace '${NAMESPACE}' to ${SIZE}."
echo "The StatefulSet will be deleted (with --cascade=orphan) and recreated. Pods will keep running."
echo ""
read -r -p "Type 'YES' to confirm: " CONFIRM
if [[ "${CONFIRM}" != "YES" ]]; then
  echo "Aborted."
  exit 1
fi

# --- Temp file setup -------------------------------------------------------

TMPDIR_WORK=$(mktemp -d)
trap 'rm -rf "$TMPDIR_WORK"' EXIT

OLD_YAML="${TMPDIR_WORK}/old_${STS_NAME}.yaml"
UPDATED_YAML="${TMPDIR_WORK}/updated_${STS_NAME}.yaml"

# --- Patch PVCs ------------------------------------------------------------

PODS=$(kubectl get pods -n "$NAMESPACE" \
  -o 'custom-columns=NAME:.metadata.name,CONTROLLER:.metadata.ownerReferences[].name' \
  --no-headers | awk -v sts="$STS_NAME" '$2 == sts {print $1}')

if [[ -z "$PODS" ]]; then
  echo "ERROR: No pods found for StatefulSet '${STS_NAME}' in namespace '${NAMESPACE}'."
  exit 1
fi

for POD in $PODS; do
  PVCS=$(kubectl get pod "$POD" -n "$NAMESPACE" \
    -o 'custom-columns=PVC:.spec.volumes[*].persistentVolumeClaim.claimName' \
    --no-headers | tr ',' '\n' | grep -v '^<none>$' | grep -v '^$')

  for PVC in $PVCS; do
    echo "Patching PVC: ${PVC}"
    kubectl patch pvc "$PVC" -n "$NAMESPACE" \
      --patch "{\"spec\": {\"resources\": {\"requests\": {\"storage\": \"${SIZE}\"}}}}"
  done
done

# --- Recreate StatefulSet with updated storage -----------------------------

echo "Saving StatefulSet '${STS_NAME}' YAML to ${OLD_YAML}"
kubectl get sts "$STS_NAME" -n "$NAMESPACE" -o yaml > "$OLD_YAML"

echo "Generating updated StatefulSet YAML"
# Only replace storage values within the volumeClaimTemplates section
awk -v size="$SIZE" '
  /^  volumeClaimTemplates:/ { in_vct=1 }
  in_vct && /storage:/ { sub(/storage:.*/, "storage: " size) }
  { print }
' "$OLD_YAML" > "$UPDATED_YAML"

echo "Deleting StatefulSet '${STS_NAME}' (cascade=orphan — pods will keep running)"
kubectl delete sts "$STS_NAME" -n "$NAMESPACE" --cascade=orphan

echo "Applying updated StatefulSet"
kubectl apply -f "$UPDATED_YAML"

echo "Restarting StatefulSet rollout"
kubectl rollout restart sts "$STS_NAME" -n "$NAMESPACE"

kubectl rollout status sts "$STS_NAME" -n "$NAMESPACE" --timeout=300s

# --- Done ------------------------------------------------------------------

echo ""
echo "Done. PVCs for '${STS_NAME}' have been resized to ${SIZE}."
echo "IMPORTANT: Update your values.yaml to reflect the new size, or the next helm upgrade will fail."
