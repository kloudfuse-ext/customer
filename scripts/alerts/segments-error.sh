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
#   ./segments-error.sh remove   <table> [segment]  — remove missing segments from ideal state
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
  pod=$(kubectl get pods -n "$NAMESPACE" -l component=controller \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  [[ -n "$pod" ]] || die "No pinot-controller pod found in namespace '${NAMESPACE}'."
  echo "$pod"
}

get_broker_pod() {
  local pod
  pod=$(kubectl get pods -n "$NAMESPACE" -l component=broker \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  [[ -n "$pod" ]] || die "No pinot-broker pod found in namespace '${NAMESPACE}'."
  echo "$pod"
}

# Cached pod name and container flag — resolved once on first call
_CONTROLLER_POD=""
_CONTROLLER_CONTAINER_FLAG=""

init_controller() {
  if [[ -n "$_CONTROLLER_POD" ]]; then return; fi
  _CONTROLLER_POD=$(get_controller_pod)
  local containers
  containers=$(kubectl get pod -n "$NAMESPACE" "$_CONTROLLER_POD" \
    -o jsonpath='{.spec.containers[*].name}' 2>/dev/null)
  if echo "$containers" | grep -qw controller; then
    _CONTROLLER_CONTAINER_FLAG="-c controller"
  fi
}

controller_api() {
  local path="$1"
  local method="${2:-GET}"
  init_controller
  # shellcheck disable=SC2086
  kubectl exec -n "$NAMESPACE" "$_CONTROLLER_POD" $_CONTROLLER_CONTAINER_FLAG -- \
    curl -s -X "$method" "http://localhost:${CONTROLLER_PORT}${path}"
}

print_usage() {
  cat <<EOF
Usage: NAMESPACE=<ns> $0 <command> [args]

Commands:
  status   [table]           List all tables with non-ONLINE segments, or check a specific table
  diagnose <table>           Show segment states and server assignments to identify root cause
  reload    <table> [segment] Reload all segments for a table, or a single named segment
  rebalance <table>           Reassign segments whose ideal state is OFFLINE back to ONLINE
  watch     <table> [job_id]  Tail controller logs for rebalance activity (optionally by job ID)
  reset     <table> <segment> Reset a REALTIME consuming segment stuck in ERROR
  remove    <table> [segment]   Remove a named segment from ideal state
  remove    <table> --orphaned  Remove segments whose Kafka partition no longer exists
  remove    <table>             Remove segments confirmed missing from deep store
  verify    <table>           Post-recovery check: segment counts, metrics query, broker test

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
    local tmpdir
    tmpdir=$(mktemp -d)

    # Strip suffix for size/rebalance APIs which use base name + type param
    local base_table="${target_table%_REALTIME}"
    base_table="${base_table%_OFFLINE}"
    local table_type="realtime"
    [[ "$target_table" == *_OFFLINE ]] && table_type="offline"

    controller_api "/tables/${target_table}/externalview"  > "${tmpdir}/externalview.json"
    controller_api "/tables/${target_table}/idealstate"    > "${tmpdir}/idealstate.json"
    controller_api "/tables/${base_table}/size"            > "${tmpdir}/size.json"
    controller_api "/tables/${base_table}/rebalance?dryRun=true&type=${table_type}&reassignInstances=false&includeConsuming=false&bootstrap=false&downtime=false" "POST" \
                                                           > "${tmpdir}/rebalance.json"

    python3 - "${tmpdir}/externalview.json" "${tmpdir}/idealstate.json" "${tmpdir}/size.json" "${tmpdir}/rebalance.json" <<'PYEOF'
import sys, json
from collections import defaultdict

with open(sys.argv[1]) as f: ev        = json.load(f)
with open(sys.argv[2]) as f: is_       = json.load(f)
with open(sys.argv[3]) as f: size_data = json.load(f)
with open(sys.argv[4]) as f: rebalance = json.load(f)

if 'error' in ev:
    print('ERROR: ' + ev.get('error', 'unknown'))
    sys.exit(1)

HEALTHY = {'ONLINE', 'CONSUMING'}

# Active Kafka partitions = any partition with at least one CONSUMING segment
active_partitions = set()
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (ev.get(table_type) or {}).items():
        parts = seg.split('__')
        if len(parts) == 4:
            for state in assignments.values():
                if state == 'CONSUMING':
                    active_partitions.add(parts[1])

def is_orphaned(seg):
    parts = seg.split('__')
    return len(parts) == 4 and parts[1] not in active_partitions

# Segment sizes from size report (only available for served segments)
seg_sizes = {}
for table_type_key in ('realtimeSegments', 'offlineSegments'):
    for seg, info in (size_data.get(table_type_key) or {}).get('segments', {}).items():
        seg_sizes[seg] = info.get('reportedSizeInBytes', 0)

# Estimated average size from rebalance dry-run (used for unserved segments)
seg_info = (rebalance.get('rebalanceSummaryResult') or {}).get('segmentInfo', {})
avg_size  = seg_info.get('estimatedAverageSegmentSizeInBytes', 0)

def resolve(ideal, current, orphaned):
    if orphaned:                                                     return 'remove'
    if ideal == 'OFFLINE' and current == 'OFFLINE':                 return 'rebalance'
    if ideal in ('ONLINE', 'CONSUMING') and current not in HEALTHY: return 'reload'
    if ideal == 'CONSUMING' and current == 'OFFLINE':               return 'reset'
    return 'investigate'

def fmt_size(b):
    if b >= 1024**3: return f'{b/1024**3:.1f} GB'
    if b >= 1024**2: return f'{b/1024**2:.1f} MB'
    return f'{b/1024:.1f} KB'

total, healthy = 0, 0
groups = defaultdict(lambda: {'count': 0, 'oldest': None, 'newest': None,
                               'total_size': 0, 'orphaned_partitions': set()})

for table_type in ('OFFLINE', 'REALTIME'):
    ev_segs = ev.get(table_type) or {}
    is_segs = is_.get(table_type) or {}
    for seg, assignments in ev_segs.items():
        for current_state in assignments.values():
            total += 1
            if current_state in HEALTHY:
                healthy += 1
            else:
                ideal_state = list((is_segs.get(seg) or {}).values())[0] \
                    if is_segs.get(seg) else 'unknown'
                orphaned = is_orphaned(seg)
                action   = resolve(ideal_state, current_state, orphaned)
                key = (current_state, ideal_state, action)
                groups[key]['count'] += 1
                size = seg_sizes.get(seg, avg_size)
                groups[key]['total_size'] += size
                parts = seg.split('__')
                if orphaned and len(parts) == 4:
                    groups[key]['orphaned_partitions'].add(parts[1])
                ts = parts[3] if len(parts) == 4 else None
                if ts:
                    if groups[key]['oldest'] is None or ts < groups[key]['oldest']:
                        groups[key]['oldest'] = ts
                    if groups[key]['newest'] is None or ts > groups[key]['newest']:
                        groups[key]['newest'] = ts

print(f'Total: {total}  Healthy: {healthy}  Non-healthy: {total - healthy}')
if active_partitions:
    print(f'Active Kafka partitions: {sorted(active_partitions, key=int)}')
if groups:
    print()
    print(f'  {"Current":<10}  {"Ideal":<10}  {"Count":<8}  {"Est. size":<12}  {"Resolve":<12}  {"Notes":<40}  Date range')
    print(f'  {"-"*10}  {"-"*10}  {"-"*8}  {"-"*12}  {"-"*12}  {"-"*40}  {"-"*30}')
    for (current, ideal, action), info in sorted(groups.items()):
        date_range = f"{info['oldest']}  →  {info['newest']}" if info['oldest'] else ''
        size_str   = fmt_size(info['total_size']) if info['total_size'] else 'unknown'
        notes = ''
        if info['orphaned_partitions']:
            parts_str = ','.join(sorted(info['orphaned_partitions'], key=int))
            notes = f'orphaned partitions (no active Kafka): {parts_str}'
        print(f'  {current:<10}  {ideal:<10}  {info["count"]:<8}  {size_str:<12}  {action:<12}  {notes:<40}  {date_range}')
else:
    print('All segments healthy.')
PYEOF
    rm -rf "$tmpdir"
  else
    echo "=== Listing all tables ==="
    local tables
    tables=$(controller_api "/tables" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('tables', []):
    for suffix in ('_REALTIME', '_OFFLINE'):
        print(t + suffix)
")
    [[ -n "$tables" ]] || die "No tables found."

    local found_issues=0
    while IFS= read -r table; do
      local result
      result=$(controller_api "/tables/${table}/externalview" \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'error' in data:
    sys.exit(0)
HEALTHY = {'ONLINE', 'CONSUMING'}
errors = []
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (data.get(table_type) or {}).items():
        for server, state in assignments.items():
            if state not in HEALTHY:
                errors.append((state, seg))
if errors:
    print(f'  {len(errors)} non-healthy segment(s)')
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
      echo "All segments are healthy across all tables."
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
  controller_api "/tables/${table}/externalview" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'error' in data:
    print('ERROR: ' + data.get('error', 'unknown'))
    sys.exit(1)
HEALTHY = {'ONLINE', 'CONSUMING'}
total, healthy, errors = 0, 0, []
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (data.get(table_type) or {}).items():
        for server, state in assignments.items():
            total += 1
            if state in HEALTHY:
                healthy += 1
            else:
                errors.append((state, seg))
print(f'Total: {total}  Healthy: {healthy}  Non-healthy: {len(errors)}')
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
    echo ""
    echo "Waiting 10 seconds then checking segment state..."
    sleep 10
    cmd_status "$table"
  else
    # Collect non-healthy segments from externalview
    local offline_segments
    offline_segments=$(controller_api "/tables/${table}/externalview" \
      | python3 -c "
import sys, json
data = json.load(sys.stdin)
HEALTHY = {'ONLINE', 'CONSUMING'}
seen = set()
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (data.get(table_type) or {}).items():
        for state in assignments.values():
            if state not in HEALTHY and seg not in seen:
                seen.add(seg)
                print(seg)
")

    local total
    total=$(echo "$offline_segments" | grep -c . || true)
    [[ "$total" -gt 0 ]] || { echo "No non-healthy segments found for '${table}'."; return; }

    echo "Found ${total} non-healthy segment(s) for table '${table}'."
    echo "They will be reloaded one at a time with a 5-second pause between each."
    echo ""
    read -r -p "Type 'YES' to proceed: " CONFIRM
    [[ "$CONFIRM" == "YES" ]] || { echo "Aborted."; exit 0; }

    local count=0
    while IFS= read -r seg; do
      [[ -n "$seg" ]] || continue
      count=$((count + 1))
      echo "[${count}/${total}] Reloading ${seg}..."
      controller_api "/tables/${table}/segments/${seg}/reload" "POST" \
        | python3 -c "
import sys, json
d = json.load(sys.stdin)
status = d.get('status', str(d))
print('  -> ' + status)
"
      sleep 2
    done <<< "$offline_segments"

    echo ""
    echo "All ${total} segments submitted. Waiting 15 seconds then checking overall state..."
    sleep 10
    cmd_status "$table"
  fi
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
  controller_api "/tables/${table}/externalview" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'error' in data:
    print('ERROR: ' + data.get('error', 'unknown'))
    sys.exit(1)
HEALTHY = {'ONLINE', 'CONSUMING'}
total, healthy, errors = 0, 0, []
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (data.get(table_type) or {}).items():
        for server, state in assignments.items():
            total += 1
            if state in HEALTHY:
                healthy += 1
            else:
                errors.append((state, seg))
pct = (healthy / total * 100) if total > 0 else 0
status = 'OK' if not errors else 'DEGRADED'
print(f'[{status}] Total: {total}  Healthy: {healthy}  ({pct:.1f}%)  Non-healthy: {len(errors)}')
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
# remove — delete a segment or all missing segments from ideal state
# ---------------------------------------------------------------------------

cmd_remove() {
  local table="${1:-}"
  local segment="${2:-}"
  local dry_run="${DRY_RUN:-}"
  [[ -n "$table" ]] || { print_usage; die "remove requires a table name."; }

  if [[ "$segment" == "--orphaned" ]]; then
    # Remove only segments whose Kafka partition is no longer active
    echo "Finding orphaned segments for table '${table}'..."
    local tmpdir
    tmpdir=$(mktemp -d)
    controller_api "/tables/${table}/externalview" > "${tmpdir}/externalview.json"

    local to_delete_str
    to_delete_str=$(python3 - "${tmpdir}/externalview.json" <<'PYEOF'
import sys, json

with open(sys.argv[1]) as f:
    ev = json.load(f)

HEALTHY = {'ONLINE', 'CONSUMING'}

# Active partitions = any partition with a CONSUMING segment
active_partitions = set()
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (ev.get(table_type) or {}).items():
        parts = seg.split('__')
        if len(parts) == 4:
            for state in assignments.values():
                if state == 'CONSUMING':
                    active_partitions.add(parts[1])

orphaned = []
seen = set()
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (ev.get(table_type) or {}).items():
        parts = seg.split('__')
        if len(parts) != 4 or seg in seen:
            continue
        for state in assignments.values():
            if state not in HEALTHY and parts[1] not in active_partitions:
                seen.add(seg)
                orphaned.append((parts[1], seg))

print(f'Active Kafka partitions: {sorted(active_partitions, key=int)}', file=sys.stderr)
orphaned_parts = sorted(set(p for p, _ in orphaned), key=int)
print(f'Orphaned partitions:     {orphaned_parts}', file=sys.stderr)
for _, seg in sorted(orphaned):
    print(seg)
PYEOF
)
    rm -rf "$tmpdir"

    local to_delete=()
    if [[ -n "$to_delete_str" ]]; then
      while IFS= read -r seg; do
        to_delete+=("$seg")
      done <<< "$to_delete_str"
    fi

    if [[ "${#to_delete[@]}" -eq 0 ]]; then
      echo "No orphaned segments found."
      return
    fi

    echo "Found ${#to_delete[@]} orphaned segment(s) (partitions with no active Kafka consumer)."
    echo ""

    if [[ -n "$dry_run" ]]; then
      echo "[DRY RUN] Would delete the ${#to_delete[@]} orphaned segment(s)."
      return
    fi

    echo "WARNING: This permanently removes orphaned segments from Pinot ideal state and ZooKeeper."
    echo "These segments belong to Kafka partitions that no longer exist — data cannot be re-ingested."
    echo ""
    read -r -p "Type 'YES' to delete all ${#to_delete[@]} orphaned segment(s) from '${table}': " CONFIRM
    [[ "$CONFIRM" == "YES" ]] || { echo "Aborted."; exit 0; }

    local count=0
    for seg in "${to_delete[@]}"; do
      count=$((count + 1))
      echo "[${count}/${#to_delete[@]}] Deleting ${seg}..."
      controller_api "/segments/${table}/${seg}" "DELETE" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print('  -> ' + d.get('status', str(d)))"
      sleep 2
    done

    echo ""
    echo "Done. Running status check..."
    cmd_status "$table"
    return
  fi

  if [[ -n "$segment" ]]; then
    # Remove a single named segment
    if [[ -n "$dry_run" ]]; then
      echo "[DRY RUN] Would delete segment '${segment}' from table '${table}'."
      return
    fi
    echo "WARNING: This permanently removes '${segment}' from Pinot ideal state and ZooKeeper."
    echo "Only use this for segments confirmed missing from deep store."
    echo ""
    read -r -p "Type 'YES' to delete segment '${segment}' from table '${table}': " CONFIRM
    [[ "$CONFIRM" == "YES" ]] || { echo "Aborted."; exit 0; }
    echo "Deleting segment '${segment}'..."
    controller_api "/segments/${table}/${segment}" "DELETE" | python3 -m json.tool
  else
    # Find all non-healthy segments missing from deep store and remove them
    echo "Checking deep store for missing segments in table '${table}'..."
    local missing
    missing=$(controller_api "/tables/${table}/size" \
      | python3 -c "
import sys, json
data = json.load(sys.stdin)
rt = data.get('realtimeSegments') or {}
missing = rt.get('missingSegments', 0)
print(missing)
")
    if [[ "$missing" -eq 0 ]]; then
      echo "No missing segments reported by the controller for '${table}'."
      return
    fi

    # Fetch externalview and bulk segment metadata in two API calls, then cross-reference
    echo "Fetching segment states and metadata..."
    local tmpdir
    tmpdir=$(mktemp -d)
    controller_api "/tables/${table}/externalview" > "${tmpdir}/externalview.json"
    controller_api "/segments/${table}/metadata"   > "${tmpdir}/metadata.json"

    local to_delete_str
    to_delete_str=$(python3 - "${tmpdir}/externalview.json" "${tmpdir}/metadata.json" <<'PYEOF'
import sys, json

with open(sys.argv[1]) as f:
    externalview = json.load(f)
with open(sys.argv[2]) as f:
    metadata_raw = json.load(f)

# Build map of segment -> realtime status from bulk metadata
seg_status = {}
for entry in (metadata_raw if isinstance(metadata_raw, list) else []):
    name = entry.get('segmentName', '')
    status = entry.get('segmentMetadata', {}).get('segment.realtime.status', 'DONE')
    if name:
        seg_status[name] = status

HEALTHY = {'ONLINE', 'CONSUMING'}
to_delete = []
seen = set()
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (externalview.get(table_type) or {}).items():
        for state in assignments.values():
            if state not in HEALTHY and seg not in seen:
                seen.add(seg)
                if seg_status.get(seg, 'DONE') == 'IN_PROGRESS':
                    to_delete.append(seg)

for s in sorted(to_delete):
    print(s)
PYEOF
)

    local to_delete=()
    if [[ -n "$to_delete_str" ]]; then
      while IFS= read -r seg; do
        to_delete+=("$seg")
      done <<< "$to_delete_str"
    fi

    rm -rf "$tmpdir"

    if [[ "${#to_delete[@]}" -eq 0 ]]; then
      echo "All non-healthy segments were found in deep store — nothing to remove."
      echo "Run 'reload' to recover them."
      return
    fi

    echo ""
    echo "Found ${#to_delete[@]} segment(s) missing from deep store:"
    for seg in "${to_delete[@]}"; do
      echo "  $seg"
    done
    echo ""

    if [[ -n "$dry_run" ]]; then
      echo "[DRY RUN] Would delete the ${#to_delete[@]} segment(s) listed above."
      return
    fi

    echo "WARNING: This permanently removes these segments from Pinot ideal state and ZooKeeper."
    echo "Data for their time ranges will be unqueryable unless rebuilt via 'reset'."
    echo ""
    read -r -p "Type 'YES' to delete all ${#to_delete[@]} missing segment(s) from '${table}': " CONFIRM
    [[ "$CONFIRM" == "YES" ]] || { echo "Aborted."; exit 0; }

    local count=0
    for seg in "${to_delete[@]}"; do
      count=$((count + 1))
      echo "[${count}/${#to_delete[@]}] Deleting ${seg}..."
      controller_api "/segments/${table}/${seg}" "DELETE" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print('  -> ' + d.get('status', str(d)))"
      sleep 2
    done

    echo ""
    echo "Done. Running status check..."
    cmd_status "$table"
  fi
}

# ---------------------------------------------------------------------------
# rebalance — fix segments whose ideal state is OFFLINE by reassigning them
# ---------------------------------------------------------------------------

cmd_rebalance() {
  local table="${1:-}"
  local dry_run="${DRY_RUN:-}"
  [[ -n "$table" ]] || { print_usage; die "rebalance requires a table name."; }

  # Strip _REALTIME/_OFFLINE suffix if provided — API uses base name + type param
  local base_table="${table%_REALTIME}"
  base_table="${base_table%_OFFLINE}"
  local table_type="realtime"
  [[ "$table" == *_OFFLINE ]] && table_type="offline"

  local params="type=${table_type}&reassignInstances=false&includeConsuming=false&bootstrap=false&downtime=false"

  if [[ -n "$dry_run" ]]; then
    echo "=== Rebalance dry-run for table: ${base_table} (${table_type}) ==="
    controller_api "/tables/${base_table}/rebalance?dryRun=true&${params}" "POST" \
      | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'error' in d:
    print('ERROR: ' + d.get('error', str(d)))
    sys.exit(1)
print(f'Status: {d.get(\"status\", \"unknown\")}')
summary  = d.get('rebalanceSummaryResult', {})
seg_info = summary.get('segmentInfo', {})
print(f'Segments to be moved:   {seg_info.get(\"totalSegmentsToBeMoved\", 0)}')
print(f'Segments to be deleted: {seg_info.get(\"totalSegmentsToBeDeleted\", 0)}')
est_bytes = seg_info.get('totalEstimatedDataToBeMovedInBytes', 0)
print(f'Estimated data to move: {est_bytes / 1024**3:.1f} GB')
srv_info = summary.get('serverInfo', {})
print(f'Servers receiving segments: {srv_info.get(\"numServersGettingNewSegments\", 0)}')
"
    return
  fi

  echo "=== Rebalancing table: ${base_table} (${table_type}) ==="
  echo "This will reassign OFFLINE segments back to servers and update the ideal state to ONLINE."
  echo ""
  read -r -p "Type 'YES' to rebalance '${base_table}': " CONFIRM
  [[ "$CONFIRM" == "YES" ]] || { echo "Aborted."; exit 0; }

  controller_api "/tables/${base_table}/rebalance?${params}" "POST" \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'error' in d:
    print('ERROR: ' + d.get('error', str(d)))
    sys.exit(1)
print('Rebalance triggered. Status: ' + d.get('status', str(d)))
job_id = d.get('jobId', '')
if job_id:
    print(f'Job ID: {job_id}')
    print(f'To monitor: ./segments-error.sh watch {sys.argv[1]} {job_id}')
" - "$base_table"

  echo ""
  echo "Rebalance is running asynchronously. Polling every 30s until segment counts stabilize..."
  local prev_unhealthy=-1
  local unchanged_rounds=0
  while true; do
    sleep 30
    local unhealthy
    unhealthy=$(controller_api "/tables/${base_table}/externalview" \
      | python3 -c "
import sys, json
HEALTHY = {'ONLINE', 'CONSUMING'}
d = json.load(sys.stdin)
if 'error' in d: sys.exit(1)
count = 0
for tt in ('OFFLINE', 'REALTIME'):
    for seg, assignments in (d.get(tt) or {}).items():
        for state in assignments.values():
            if state not in HEALTHY:
                count += 1
print(count)
" 2>/dev/null) || true
    if [[ -z "$unhealthy" ]]; then
      echo "  (controller unreachable — retrying...)"
      continue
    fi
    echo "  Non-healthy segments: ${unhealthy}"
    if [[ "$unhealthy" -eq 0 ]]; then
      echo "All segments healthy."
      break
    fi
    if [[ "$prev_unhealthy" -gt 0 && "$unhealthy" -eq "$prev_unhealthy" ]]; then
      unchanged_rounds=$((unchanged_rounds + 1))
      if [[ "$unchanged_rounds" -ge 3 ]]; then
        echo "Count unchanged for 90s — rebalance may have completed its pass. Run status to review."
        break
      fi
    else
      unchanged_rounds=0
    fi
    prev_unhealthy="$unhealthy"
  done
  echo ""
  cmd_status "$table"
}

# ---------------------------------------------------------------------------
# watch — tail controller logs filtered to rebalance activity for a table
# ---------------------------------------------------------------------------

cmd_watch() {
  local table="${1:-}"
  local job_id="${2:-}"
  [[ -n "$table" ]] || { print_usage; die "watch requires a table name."; }

  local base_table="${table%_REALTIME}"
  base_table="${base_table%_OFFLINE}"

  local controller_pod
  controller_pod=$(get_controller_pod)

  if [[ -n "$job_id" ]]; then
    echo "=== Watching rebalance job ${job_id} for table: ${base_table} ==="
    echo "(Ctrl-C to stop)"
    kubectl logs -n "$NAMESPACE" "$controller_pod" -c controller -f 2>/dev/null \
      | grep --line-buffered -i "${job_id}"
  else
    echo "=== Watching rebalance activity for table: ${base_table}_REALTIME ==="
    echo "(Shows segment state transitions and rebalance progress. Ctrl-C to stop.)"
    kubectl logs -n "$NAMESPACE" "$controller_pod" -c controller -f 2>/dev/null \
      | grep --line-buffered -iE "TableRebalancer-${base_table}|RebalanceChecker.*${base_table}|${base_table}.*rebalanc|rebalanc.*${base_table}" \
      | python3 -u -c "
import sys, re
for line in sys.stdin:
    # Shorten log line: strip date prefix, extract thread and message
    m = re.match(r'(\S+)\s+(\S+)\s+\[(\S+)\]\s+\[([^\]]+)\]\s+(.*)', line.strip())
    if m:
        level, ts, logger, thread, msg = m.groups()
        short_logger = logger.split('.')[-1]
        print(f'{ts}  {level}  {short_logger}: {msg}')
    else:
        print(line.rstrip())
" 2>/dev/null
  fi
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

case "$CMD" in
  status)    cmd_status    "${2:-}" ;;
  diagnose)  cmd_diagnose  "${2:-}" ;;
  reload)    cmd_reload    "${2:-}" "${3:-}" ;;
  reset)     cmd_reset     "${2:-}" "${3:-}" ;;
  remove)    cmd_remove    "${2:-}" "${3:-}" ;;
  rebalance) cmd_rebalance "${2:-}" ;;
  watch)     cmd_watch     "${2:-}" "${3:-}" ;;
  verify)    cmd_verify    "${2:-}" ;;
  *)         print_usage; exit 1 ;;
esac
