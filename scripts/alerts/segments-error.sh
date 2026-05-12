#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# segments-error.sh — Diagnose and recover unavailable/errored Pinot segments
#
# Usage:
#   ./segments-error.sh status   [table]           — identify affected tables/segments
#   ./segments-error.sh diagnose <table>            — diagnose root cause for a table
#   ./segments-error.sh reload   <table> [segment]  — reload all or one segment
#   ./segments-error.sh reset    <table> <segment>  — reset a REALTIME consuming segment
#   ./segments-error.sh verify   <table>            — post-recovery verification
#
# All commands require kubectl access to the kfuse namespace (or set NAMESPACE).
# ---------------------------------------------------------------------------

NAMESPACE="${NAMESPACE:-kfuse}"
CONTROLLER_PORT="${CONTROLLER_PORT:-9000}"
BROKER_PORT="${BROKER_PORT:-8099}"

CMD="${1:-}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

die() { echo "ERROR: $*" >&2; exit 1; }

get_controller_pod() {
  local pod
  pod=$(kubectl get pods -n "$NAMESPACE" -l app=pinot-controller \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  [[ -n "$pod" ]] || die "No pinot-controller pod found in namespace '${NAMESPACE}'."
  echo "$pod"
}

get_broker_pod() {
  local pod
  pod=$(kubectl get pods -n "$NAMESPACE" -l app=pinot-broker \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  [[ -n "$pod" ]] || die "No pinot-broker pod found in namespace '${NAMESPACE}'."
  echo "$pod"
}

controller_api() {
  local path="$1"
  local method="${2:-GET}"
  local controller_pod
  controller_pod=$(get_controller_pod)
  kubectl exec -n "$NAMESPACE" "$controller_pod" -- \
    curl -s -X "$method" "http://localhost:${CONTROLLER_PORT}${path}"
}

print_usage() {
  cat <<EOF
Usage: NAMESPACE=<ns> $0 <command> [args]

Commands:
  status   [table]           List all tables with non-ONLINE segments, or check a specific table
  diagnose <table>           Show segment states and server assignments to identify root cause
  reload   <table> [segment] Reload all segments for a table, or a single named segment
  reset    <table> <segment> Reset a REALTIME consuming segment stuck in ERROR
  verify   <table>           Post-recovery check: segment counts, metrics query, broker test

Environment:
  NAMESPACE       Kubernetes namespace (default: kfuse)
  CONTROLLER_PORT Pinot controller port (default: 9000)
  BROKER_PORT     Pinot broker port (default: 8099)

Examples:
  $0 status
  $0 status kf_logs_REALTIME
  $0 diagnose kf_logs_REALTIME
  $0 reload kf_logs_REALTIME
  $0 reload kf_logs_REALTIME kf_logs_REALTIME_0__0__20250101T0000Z__20250101T0100Z
  $0 reset kf_logs_REALTIME kf_logs_REALTIME_consuming_0
  $0 verify kf_logs_REALTIME
EOF
}

# ---------------------------------------------------------------------------
# status — identify affected tables and segments
# ---------------------------------------------------------------------------

cmd_status() {
  local target_table="${1:-}"

  if [[ -n "$target_table" ]]; then
    echo "=== Segment states for table: ${target_table} ==="
    controller_api "/tables/${target_table}/segments" \
      | python3 -c "
import sys, json
data = json.load(sys.stdin)
total, online, errors = 0, 0, []
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        total += 1
        if state == 'ONLINE':
            online += 1
        else:
            errors.append((state, seg))
print(f'Total: {total}  ONLINE: {online}  Non-ONLINE: {len(errors)}')
if errors:
    print()
    for state, seg in sorted(errors):
        print(f'  {state:10s}  {seg}')
else:
    print('All segments ONLINE.')
"
  else
    echo "=== Listing all tables ==="
    local tables
    tables=$(controller_api "/tables" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('tables', []):
    print(t)
")
    [[ -n "$tables" ]] || die "No tables found."

    local found_issues=0
    while IFS= read -r table; do
      local result
      result=$(controller_api "/tables/${table}/segments" \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
errors = []
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        if state != 'ONLINE':
            errors.append((state, seg))
if errors:
    print(f'  {len(errors)} non-ONLINE segment(s)')
    for state, seg in sorted(errors)[:5]:
        print(f'    {state:10s}  {seg}')
    if len(errors) > 5:
        print(f'    ... and {len(errors)-5} more')
" 2>/dev/null)
      if [[ -n "$result" ]]; then
        echo ""
        echo "TABLE: ${table}"
        echo "$result"
        found_issues=1
      fi
    done <<< "$tables"

    if [[ "$found_issues" -eq 0 ]]; then
      echo "All segments are ONLINE across all tables."
    fi
  fi
}

# ---------------------------------------------------------------------------
# diagnose — show external view (server assignments) to identify root cause
# ---------------------------------------------------------------------------

cmd_diagnose() {
  local table="${1:-}"
  [[ -n "$table" ]] || { print_usage; die "diagnose requires a table name."; }

  echo "=== Segment states for table: ${table} ==="
  controller_api "/tables/${table}/segments" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
total, online, errors = 0, 0, []
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        total += 1
        if state == 'ONLINE':
            online += 1
        else:
            errors.append((state, seg))
print(f'Total: {total}  ONLINE: {online}  Non-ONLINE: {len(errors)}')
for state, seg in sorted(errors):
    print(f'  {state:10s}  {seg}')
"

  echo ""
  echo "=== Server assignments (ExternalView) ==="
  controller_api "/tables/${table}/externalview" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
server_issues = {}
for table_type in ('OFFLINE', 'REALTIME'):
    segments = data.get(table_type, {})
    for seg, assignments in segments.items():
        for server, state in assignments.items():
            if state != 'ONLINE':
                server_issues.setdefault(server, []).append((seg, state))
if not server_issues:
    print('All server assignments are ONLINE.')
else:
    for server in sorted(server_issues):
        issues = server_issues[server]
        print(f'{server}: {len(issues)} segment(s) not ONLINE')
        for seg, state in issues[:5]:
            print(f'  {state:10s}  {seg}')
        if len(issues) > 5:
            print(f'  ... and {len(issues)-5} more')
"
}

# ---------------------------------------------------------------------------
# reload — reload one or all segments for a table
# ---------------------------------------------------------------------------

cmd_reload() {
  local table="${1:-}"
  local segment="${2:-}"
  [[ -n "$table" ]] || { print_usage; die "reload requires a table name."; }

  if [[ -n "$segment" ]]; then
    echo "Reloading segment '${segment}' for table '${table}'..."
    controller_api "/tables/${table}/segments/${segment}/reload" "POST" \
      | python3 -m json.tool
  else
    echo "Reloading ALL segments for table '${table}'..."
    read -r -p "Confirm reload of all segments for '${table}'? Type 'YES' to proceed: " CONFIRM
    [[ "$CONFIRM" == "YES" ]] || { echo "Aborted."; exit 0; }
    controller_api "/tables/${table}/segments/reload" "POST" \
      | python3 -m json.tool
  fi

  echo ""
  echo "Waiting 10 seconds then checking segment states..."
  sleep 10
  cmd_status "$table"
}

# ---------------------------------------------------------------------------
# reset — reset a REALTIME consuming segment stuck in ERROR
# ---------------------------------------------------------------------------

cmd_reset() {
  local table="${1:-}"
  local segment="${2:-}"
  [[ -n "$table" ]] || { print_usage; die "reset requires a table name."; }
  [[ -n "$segment" ]] || { print_usage; die "reset requires a segment name."; }

  echo "WARNING: Resetting a consuming segment may cause data duplication or loss."
  echo "Only proceed if you have confirmed Kafka still has data for this segment's time range."
  echo ""
  read -r -p "Type 'YES' to reset segment '${segment}' on table '${table}': " CONFIRM
  [[ "$CONFIRM" == "YES" ]] || { echo "Aborted."; exit 0; }

  echo "Resetting segment '${segment}' on table '${table}'..."
  controller_api "/segments/${table}/${segment}/reset" "POST" \
    | python3 -m json.tool

  echo ""
  echo "Segment reset triggered. Monitor Pinot server logs in Kloudfuse to confirm consumption resumes:"
  echo ""
  echo "  FuseQL: kube_pod*~\"pinot-server\" and \"${segment}\""
}

# ---------------------------------------------------------------------------
# verify — post-recovery verification
# ---------------------------------------------------------------------------

cmd_verify() {
  local table="${1:-}"
  [[ -n "$table" ]] || { print_usage; die "verify requires a table name."; }

  echo "=== Segment health for table: ${table} ==="
  controller_api "/tables/${table}/segments" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
total, online, errors = 0, 0, []
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        total += 1
        if state == 'ONLINE':
            online += 1
        else:
            errors.append((state, seg))
pct = (online / total * 100) if total > 0 else 0
status = 'OK' if not errors else 'DEGRADED'
print(f'[{status}] Total: {total}  ONLINE: {online}  ({pct:.1f}%)  Non-ONLINE: {len(errors)}')
for state, seg in sorted(errors):
    print(f'  {state:10s}  {seg}')
"

  echo ""
  echo "=== Broker query test ==="
  local broker_pod
  broker_pod=$(get_broker_pod)
  kubectl exec -n "$NAMESPACE" "$broker_pod" -- \
    curl -s -X POST "http://localhost:${BROKER_PORT}/query/sql" \
    -H "Content-Type: application/json" \
    -d "{\"sql\": \"SELECT COUNT(*) FROM ${table} LIMIT 1\"}" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
queried = data.get('numServersQueried', '?')
responded = data.get('numServersResponded', '?')
exceptions = data.get('exceptions', [])
status = 'OK' if not exceptions and queried == responded else 'DEGRADED'
print(f'[{status}] numServersQueried={queried}  numServersResponded={responded}')
if exceptions:
    for ex in exceptions:
        print(f'  Exception: {ex}')
"

  echo ""
  echo "=== PromQL queries to verify in Kloudfuse Metrics ==="
  echo ""
  echo "  # Segments in error (should be 0):"
  echo "  pinot_controller_numSegmentsWithError{kube_cluster_name=\"<KUBE_CLUSTER_NAME>\"}"
  echo ""
  echo "  # Broker unavailable segments (should be 0):"
  echo "  pinot_broker_numUnavailableSegments{kube_cluster_name=\"<KUBE_CLUSTER_NAME>\"}"
  echo ""
  echo "  # Percent segments available (should be 100):"
  echo "  pinot_controller_percentSegmentsAvailable_Value{table=\"${table}\"}"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

case "$CMD" in
  status)   cmd_status   "${2:-}" ;;
  diagnose) cmd_diagnose "${2:-}" ;;
  reload)   cmd_reload   "${2:-}" "${3:-}" ;;
  reset)    cmd_reset    "${2:-}" "${3:-}" ;;
  verify)   cmd_verify   "${2:-}" ;;
  *)        print_usage; exit 1 ;;
esac
