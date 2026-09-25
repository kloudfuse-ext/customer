#!/usr/bin/env bash
#
# kfuse-upgrade.sh -- orchestrated kfuse upgrade.
# This copy (kloudfuse-ext/customer scripts/kfuse-upgrade.sh) is the
# source of truth.
#
# See deploy/UPGRADE-ORCHESTRATOR-DESIGN.md in kloudfuse/charts for the
# full design. Summary:
# a single `helm upgrade` is run with `updateStrategy: OnDelete` injected
# for all stateful tiers (so nothing stateful restarts on its own), then
# this script restarts pods in dependency order:
#   [jobs: pgdb, kafka topics] -> zookeeper -> kafka controller -> kafka broker
#     -> pinot controller -> [job: setup-pinot] -> pinot broker
#     -> pinot server realtime/offline -> pinot minion
# restarting only StatefulSets whose revision actually changed. The pinot
# controller comes up on the new version BEFORE setup-pinot is awaited (new
# table configs may not validate against the old controller); servers restart
# only AFTER setup-pinot completes (so consuming segments open on the new
# schema).
#
# Usage:
#   kfuse-upgrade.sh upgrade  <values.yaml> <version|local> [options]
#   kfuse-upgrade.sh status   [options]
#   kfuse-upgrade.sh restart  <sts-name-or-class-glob> [options]
#   kfuse-upgrade.sh rollback [helm-revision] [options]
#   kfuse-upgrade.sh run-job  <job-name> [options]
#
# Options:
#   -n <namespace>        Kubernetes namespace (default: kfuse)
#   -r <release>          Helm release name (default: kfuse)
#   -f <values.yaml>      Additional values file (repeatable)
#   --set k=v             Extra helm --set (repeatable)
#   --recreate <glob>     Restart matching STS (name or class) by deleting all
#                         pods at once instead of one-by-one (repeatable).
#                         e.g. --recreate 'pinot-server-*' --recreate pinot-minion
#   --force-restart <glob> Restart matching STS even if its revision is
#                         unchanged (repeatable)
#   --chart-dir <path>    Local chart dir for 'local' (default: <repo>/kfuse)
#   --token <token.json>  Registry service-account key (customer installs).
#                         Without it, gcloud is used if available; otherwise
#                         an existing 'helm registry login' session is assumed.
#   --skip-login          Skip helm registry login entirely
#   --skip-deps           Skip 'helm dep update' for local installs
#   --job-timeout <sec>   Timeout waiting for each job (default: 1800)
#   --pod-timeout <sec>   Timeout waiting for each pod (default: 900)
#   --yes                 Don't prompt before the restart phase
#   --dry-run             (upgrade) render with --dry-run=server and diff
#                         against the live release manifest; no changes made
#
# Classes (for --recreate / --force-restart / restart):
#   zookeeper kafka-controller kafka-broker pinot-controller pinot-broker
#   pinot-server-realtime pinot-server-offline pinot-minion

set -euo pipefail
# Disable pathname expansion: user-supplied globs (--recreate '*') and the
# stored glob lists are matched via 'case' and must never expand against
# the caller's working directory. Nothing in this script globs files.
set -f

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

OCI_CHART="oci://us-east1-docker.pkg.dev/mvp-demo-301906/kfuse-helm/kfuse"
REGISTRY_HOST="us-east1-docker.pkg.dev"

# Restart order. Classes are derived from STS labels in discover_sts, so all
# pinot aliases (pinot-logs, pinot-metrics, ...) fall into the same classes.
# The pinot controller restarts BEFORE we wait on setup-pinot: new table
# configs can reference features only the new controller validates (e.g. new
# minion task types), and the job retries (backoffLimit 100) until it's up.
PRE_SETUP_CLASSES="zookeeper kafka-controller kafka-broker pinot-controller"
POST_SETUP_CLASSES="pinot-broker pinot-server-realtime pinot-server-offline pinot-minion"
CLASS_ORDER="$PRE_SETUP_CLASSES $POST_SETUP_CLASSES"

# Static-name jobs recreated by every upgrade (ttlSecondsAfterFinished: 60).
# Leftovers must be deleted pre-upgrade or helm hits immutable-spec errors.
INFRA_JOB_GLOBS="kfuse-create-pgdb-databases kfuse-kafka-topic-creation kfuse-kafka-kraft-topic-creation kfuse-kafka-external-topic-creation"
SETUP_JOB_GLOBS="kfuse-setup-pinot*"
JOB_GLOBS="$SETUP_JOB_GLOBS $INFRA_JOB_GLOBS"

NAMESPACE="kfuse"
RELEASE="kfuse"
CHART_DIR="$REPO_ROOT/kfuse"
VALUES_ARGS=""            # accumulated "-f <file>" args (paths must not contain spaces)
SET_ARGS=""
RECREATE_GLOBS=""
FORCE_GLOBS=""
JOB_TIMEOUT=1800
POD_TIMEOUT=900
TOKEN_FILE=""
SKIP_LOGIN=false
SKIP_DEPS=false
ASSUME_YES=false
DRY_RUN=false

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/kfuse-upgrade.XXXXXX")"
LOCK_HELD=false
cleanup() {
  if [ "$LOCK_HELD" = true ]; then
    kubectl -n "$NAMESPACE" delete configmap "kfuse-upgrade-lock-$RELEASE" --ignore-not-found >/dev/null 2>&1 || true
  fi
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

# Per-release mutation lock: two concurrent upgrade/rollback/restart runs
# would interleave job deletion, pod deletion, and the RollingUpdate revert,
# reintroducing the concurrent rollout this orchestrator exists to prevent.
# ConfigMap creation is atomic (AlreadyExists on contention); released on
# exit via the trap. helm's own pending-operation lock only covers the helm
# step, not the surrounding phases.
acquire_lock() {
  local lock="kfuse-upgrade-lock-$RELEASE"
  if kubectl -n "$NAMESPACE" create configmap "$lock" \
       --from-literal=holder="$(whoami)@$(hostname) pid=$$" \
       --from-literal=started="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       --from-literal=command="$COMMAND" >/dev/null 2>"$WORKDIR/lock.err"; then
    LOCK_HELD=true
    info "acquired orchestrator lock ($lock)"
  elif grep -qi 'already exists' "$WORKDIR/lock.err"; then
    die "another orchestrator run holds the lock: $(kubectl -n "$NAMESPACE" get configmap "$lock" -o jsonpath='{.data.holder} since {.data.started} ({.data.command})' 2>/dev/null). If that run crashed, remove the stale lock: kubectl -n $NAMESPACE delete configmap $lock"
  elif grep -qi 'not found' "$WORKDIR/lock.err"; then
    # Fresh install: create the namespace now (helm --create-namespace
    # would anyway) so the lock is real mutual exclusion from the start,
    # instead of two first-installs both proceeding unlocked.
    kubectl create ns "$NAMESPACE" >/dev/null 2>&1 || true
    if kubectl -n "$NAMESPACE" create configmap "$lock" \
         --from-literal=holder="$(whoami)@$(hostname) pid=$$" \
         --from-literal=started="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
         --from-literal=command="$COMMAND" >/dev/null 2>&1; then
      LOCK_HELD=true
      info "acquired orchestrator lock ($lock) after creating namespace"
    else
      warn "could not create namespace/lock up front -- proceeding unlocked (fresh install)"
    fi
  else
    die "cannot acquire orchestrator lock: $(tail -1 "$WORKDIR/lock.err" 2>/dev/null)"
  fi
}

log()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '    \033[33mWARNING: %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "required tool not found: $1"; }

usage() { sed -n '2,50p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

[ $# -ge 1 ] || usage 1
COMMAND="$1"; shift
POSITIONAL=""

while [ $# -gt 0 ]; do
  case "$1" in
    -n) NAMESPACE="$2"; shift 2 ;;
    -r) RELEASE="$2"; shift 2 ;;
    -f) VALUES_ARGS="$VALUES_ARGS -f $2"; shift 2 ;;
    --set) SET_ARGS="$SET_ARGS --set $2"; shift 2 ;;
    --recreate) RECREATE_GLOBS="$RECREATE_GLOBS $2"; shift 2 ;;
    --force-restart) FORCE_GLOBS="$FORCE_GLOBS $2"; shift 2 ;;
    --chart-dir) CHART_DIR="$2"; shift 2 ;;
    --token) TOKEN_FILE="$2"; shift 2 ;;
    --skip-login) SKIP_LOGIN=true; shift ;;
    --skip-deps) SKIP_DEPS=true; shift ;;
    --job-timeout) JOB_TIMEOUT="$2"; shift 2 ;;
    --pod-timeout) POD_TIMEOUT="$2"; shift 2 ;;
    --yes|-y) ASSUME_YES=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage 0 ;;
    -*) die "unknown option: $1" ;;
    *) POSITIONAL="$POSITIONAL $1"; shift ;;
  esac
done
# shellcheck disable=SC2086
set -- $POSITIONAL

# ---------------------------------------------------------------------------
# OnDelete values injection (script-owned; see design doc section 5.1)
# ---------------------------------------------------------------------------

write_ondelete_values() {
  ONDELETE_FILE="$WORKDIR/ondelete-values.yaml"
  cat > "$ONDELETE_FILE" <<'EOF'
# Generated by kfuse-upgrade.sh. Sets updateStrategy: OnDelete on all
# stateful tiers so the orchestrator controls restart order. Values for
# disabled aliases/subcharts are ignored by helm.
pinot: &pinotOnDelete
  controller:
    updateStrategy:
      type: OnDelete
  broker:
    updateStrategy:
      type: OnDelete
  server:                    # one key covers realtime AND offline
    updateStrategy:
      type: OnDelete
  minion:
    updateStrategy:
      type: OnDelete
  zookeeper:
    updateStrategy: OnDelete # bitnami zookeeper: bare string, not .type
pinot-logs: *pinotOnDelete
pinot-metrics: *pinotOnDelete
pinot-traces: *pinotOnDelete
pinot-llm: *pinotOnDelete
pinot-events: *pinotOnDelete
pinot-rum: *pinotOnDelete
kafka-kraft:                 # no zookeeper subchart in kraft mode
  controller:
    updateStrategy:
      type: OnDelete
  broker:
    updateStrategy:
      type: OnDelete
# Legacy mode (global.kafka.deployLegacy). NOTE: kafka's vendored zookeeper
# is bitnami 13.x, which takes the OBJECT form (updateStrategy.type) --
# unlike pinot's vendored zookeeper 7.6.2 above, which takes a bare string.
kafka:
  controller:
    updateStrategy:
      type: OnDelete
  broker:
    updateStrategy:
      type: OnDelete
  zookeeper:
    updateStrategy:
      type: OnDelete
      # The chart default includes rollingUpdate: {}, which helm would
      # recursively merge alongside type: OnDelete -- an invalid combination
      # the API rejects. null deletes the inherited key.
      rollingUpdate: null
EOF
}

# ---------------------------------------------------------------------------
# Discovery / classification
# ---------------------------------------------------------------------------

# Emits lines: "<sts-name> <class> <replicas>" for every managed StatefulSet.
# Classification (verified against pisco):
#   - zookeeper: metadata.labels.role == zookeeper, or name ends -zookeeper
#     (covers pinot-zookeeper, per-alias zookeepers, legacy kafka-zookeeper)
#   - kafka: metadata.labels "app.kubernetes.io/part-of: kafka", split on
#     app.kubernetes.io/component (controller-eligible vs broker)
#   - pinot: spec.selector.matchLabels.app == pinot (identical across all
#     aliases -- this is why we never target pods by label), class from
#     selector "component" (controller|broker|server-realtime|server-offline|minion)
discover_sts() {
  kubectl -n "$NAMESPACE" get sts -o json | jq -r --arg rel "$RELEASE" '
    .items[]
    | .metadata.name as $n
    | (.metadata.labels // {}) as $ml
    | (.spec.selector.matchLabels // {}) as $sel
    # Scope to this helm release: never touch another release'"'"'s pods in a
    # shared namespace (pinot uses selector "release", bitnami charts use
    # the app.kubernetes.io/instance label).
    | select(($ml["app.kubernetes.io/instance"] == $rel) or ($sel["release"] == $rel) or ($ml["release"] == $rel))
    | ( if ($ml["role"] == "zookeeper") or ($n | endswith("-zookeeper")) then "zookeeper"
        elif $ml["app.kubernetes.io/part-of"] == "kafka" then
          ( if $ml["app.kubernetes.io/component"] == "controller-eligible"
            then "kafka-controller" else "kafka-broker" end )
        elif $sel["app"] == "pinot" then ("pinot-" + ($sel["component"] // "unknown"))
        else empty end ) as $class
    | "\($n) \($class) \(.spec.replicas // 0)"'
}

matches_any() { # <name> <class> <glob list...>
  local name="$1" class="$2" g; shift 2
  for g in "$@"; do
    # shellcheck disable=SC2254
    case "$name" in $g) return 0 ;; esac
    # shellcheck disable=SC2254
    case "$class" in $g) return 0 ;; esac
  done
  return 1
}

# helm upgrade returns when the API server accepts the spec; the StatefulSet
# controller populates status.updateRevision asynchronously. Reading status
# before it reconciles would make every pod look current and silently skip a
# needed restart (OnDelete never converges on its own), so gate staleness
# decisions on the controller having observed the latest generation.
wait_sts_observed() { # <sts>
  local sts="$1" gen obs deadline
  deadline=$(( $(date +%s) + 120 ))
  while :; do
    read -r gen obs <<EOF
$(kubectl -n "$NAMESPACE" get sts "$sts" -o jsonpath='{.metadata.generation} {.status.observedGeneration}')
EOF
    [ -n "${obs:-}" ] && [ "$obs" -ge "$gen" ] 2>/dev/null && return 0
    # Fail closed: judging staleness from a pre-reconcile status could
    # silently skip a required restart.
    [ "$(date +%s)" -ge "$deadline" ] && die "$sts: controller has not observed generation $gen after 2m -- cannot safely judge staleness"
    sleep 2
  done
}

sts_update_revision() { kubectl -n "$NAMESPACE" get sts "$1" -o jsonpath='{.status.updateRevision}'; }

pod_revision() { kubectl -n "$NAMESPACE" get pod "$1" -o jsonpath='{.metadata.labels.controller-revision-hash}' 2>/dev/null || true; }

pod_uid() { kubectl -n "$NAMESPACE" get pod "$1" -o jsonpath='{.metadata.uid}' 2>/dev/null || true; }

pod_ready() {
  [ "$(kubectl -n "$NAMESPACE" get pod "$1" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)" = "True" ]
}

# Pods of <sts> not on the current updateRevision, highest ordinal first.
stale_pods() { # <sts> <replicas>
  local sts="$1" replicas="$2" rev pod i out=""
  rev="$(sts_update_revision "$sts")"
  i=$((replicas - 1))
  while [ "$i" -ge 0 ]; do
    pod="${sts}-${i}"
    if kubectl -n "$NAMESPACE" get pod "$pod" >/dev/null 2>&1; then
      [ "$(pod_revision "$pod")" != "$rev" ] && out="$out $pod"
    fi
    i=$((i - 1))
  done
  echo "$out"
}

wait_pod_ready() { # <pod> [old-uid] -- waits for existence + Ready + current revision
  # With <old-uid>, additionally requires a NEW pod instance (uid changed):
  # a just-deleted pod can linger Terminating-but-still-Ready on the current
  # revision (force-restart case) and must not satisfy the wait.
  local pod="$1" old_uid="${2:-}" sts rev deadline
  sts="${pod%-*}"
  rev="$(sts_update_revision "$sts")"
  deadline=$(( $(date +%s) + POD_TIMEOUT ))
  until kubectl -n "$NAMESPACE" get pod "$pod" >/dev/null 2>&1 \
        && { [ -z "$old_uid" ] || [ "$(pod_uid "$pod")" != "$old_uid" ]; } \
        && [ "$(pod_revision "$pod")" = "$rev" ] \
        && pod_ready "$pod"; do
    [ "$(date +%s)" -ge "$deadline" ] && die "timed out waiting for pod $pod (Ready on revision $rev)"
    sleep 5
  done
  info "$pod is Ready on new revision"
}

# Waits (POD_TIMEOUT) for a pod to exist and be Ready, regardless of
# revision -- used for scale-up ordinals, which are created on the new
# revision but may still be scheduling/starting.
wait_pod_exists_ready() { # <pod>
  local pod="$1" deadline
  deadline=$(( $(date +%s) + POD_TIMEOUT ))
  until kubectl -n "$NAMESPACE" get pod "$pod" >/dev/null 2>&1 && pod_ready "$pod"; do
    [ "$(date +%s)" -ge "$deadline" ] && die "timed out waiting for pod $pod to be Ready"
    sleep 5
  done
}

# Converges every ordinal of a component: waits for existence + Ready +
# current revision (covers missing pods and scale-up ordinals, which the
# stale-pod diff alone would skip) and applies the class health gate to
# each pod (covers replica-only scale-ups that were never restarted).
verify_component() { # <sts> <class> <replicas>
  local sts="$1" class="$2" replicas="$3" i=0
  while [ "$i" -lt "$replicas" ]; do
    wait_pod_ready "${sts}-${i}"
    health_gate "$class" "${sts}-${i}" "$replicas"
    i=$((i + 1))
  done
}

# Live-pin OnDelete on existing managed StatefulSets BEFORE any helm apply.
# Helm's three-way merge only patches fields whose value changed between
# release manifests; after a previous run's RollingUpdate revert, both old
# and new manifests say OnDelete, so helm would NOT reassert it and the
# live RollingUpdate would roll pods concurrently the moment the template
# changes. The pre-patch closes that hole; assert_strategies then verifies
# nothing (e.g. a user --set, which outranks the generated -f) undid it.
pin_strategies() { # <sts-list-file>
  local sts class replicas orig
  [ -s "$1" ] || return 0
  log "Pinning updateStrategy: OnDelete on managed StatefulSets (pre-apply)"
  : > "$WORKDIR/orig-strategies.tsv"
  while read -r sts class replicas; do
    # Snapshot the original strategy so revert_strategies can restore it
    # exactly (e.g. a user-configured rollingUpdate.partition) instead of
    # resetting everything to a bare RollingUpdate.
    orig="$(kubectl -n "$NAMESPACE" get sts "$sts" -o json | jq -c '.spec.updateStrategy // {"type":"RollingUpdate"}')"
    printf '%s\t%s\n' "$sts" "$orig" >> "$WORKDIR/orig-strategies.tsv"
    # rollingUpdate:null is required: the API server defaults
    # rollingUpdate:{partition:0} onto live RollingUpdate StatefulSets, and
    # a merge patch of type alone would leave it behind -- an OnDelete +
    # rollingUpdate combination the API rejects.
    kubectl -n "$NAMESPACE" patch sts "$sts" --type merge \
      -p '{"spec":{"updateStrategy":{"type":"OnDelete","rollingUpdate":null}}}' >/dev/null \
      || die "$sts: failed to pin OnDelete -- aborting before helm can roll it concurrently"
  done < "$1"
}

assert_strategies() { # <sts-list-file>
  local sts class replicas t
  [ -s "$1" ] || return 0
  while read -r sts class replicas; do
    t="$(kubectl -n "$NAMESPACE" get sts "$sts" -o jsonpath='{.spec.updateStrategy.type}')"
    [ "$t" = "OnDelete" ] \
      || die "$sts is on '$t', not OnDelete, after the helm apply -- a values/--set override is defeating orchestration; remove it and re-run"
  done < "$1"
}

# Scale-up ordinals are created by the StatefulSet controller as soon as
# helm bumps spec.replicas (updateStrategy does not gate scaling) and come
# up on the NEW revision. setup-pinot's set-tag initContainer tags the full
# target replica count via the controller API and fails until every
# instance has registered, so wait for scale-up pods to be Ready before
# waiting on the job -- otherwise it just burns retries.
wait_for_scale_up() {
  local sts class replicas i pod any=false
  [ -s "${DISCOVERED:-/dev/null}" ] || return 0
  while read -r sts class replicas; do
    i=0
    while [ "$i" -lt "$replicas" ]; do
      pod="${sts}-${i}"
      if ! kubectl -n "$NAMESPACE" get pod "$pod" >/dev/null 2>&1 || ! pod_ready "$pod"; then
        [ "$any" = false ] && { log "Waiting for scaled-up / not-yet-ready pods"; any=true; }
        info "waiting for $pod"
        wait_pod_exists_ready "$pod"
      fi
      i=$((i + 1))
    done
  done < "$DISCOVERED"
}

# ---------------------------------------------------------------------------
# Health gates
# ---------------------------------------------------------------------------

# Confirm the restarted pod rejoined the ensemble: the "srvr" 4lw command
# (whitelisted by default; same transport as the chart's own probes) reports
# "Mode: leader|follower" only once the node is participating in quorum.
# zkServer.sh is deliberately avoided -- it spawns a second JVM with the
# server's heap flags, which can fail inside the pod's memory limit.
zk_quorum_check() { # <pod> <replicas>
  local pod="$1" replicas="$2" want mode tries=0 max=$(( POD_TIMEOUT / 5 ))
  # standalone is only a healthy state for a single-node "ensemble";
  # on a real ensemble it means the node is serving WITHOUT quorum.
  if [ "$replicas" -le 1 ]; then want='Mode: (leader|follower|standalone)'
  else want='Mode: (leader|follower)'; fi
  while :; do
    mode="$(kubectl -n "$NAMESPACE" exec "$pod" -- bash -c 'echo srvr | timeout 3 nc -w 2 localhost 2181' 2>/dev/null \
              | grep -Eo "$want" || true)"
    [ -n "$mode" ] && { info "$pod: $mode (in quorum)"; return 0; }
    tries=$((tries + 1))
    [ "$tries" -eq 1 ] && info "waiting for $pod to rejoin the ZK ensemble..."
    # Fail closed: deleting the next ordinal without evidence this one
    # rejoined can turn a rolling restart into quorum loss.
    [ "$tries" -ge "$max" ] && die "$pod did not rejoin the ZK ensemble within ${POD_TIMEOUT}s -- investigate before continuing (re-run resumes here)"
    sleep 5
  done
}

# KRaft controller quorum: the chart's controller readiness probe is only a
# TCP check, so Ready does not prove the node rejoined the metadata quorum.
# kafka-metadata-quorum.sh runs in-pod; the controller listener is
# SASL_PLAINTEXT (PLAIN) with credentials in the pod env, with a PLAINTEXT
# fallback attempt for environments that disable SASL.
kafka_quorum_check() { # <pod>
  local pod="$1" out tries=0 max=$(( POD_TIMEOUT / 5 ))
  while :; do
    # The probe supports SASL_PLAINTEXT (kfuse default) and PLAINTEXT. A
    # TLS controller listener (SASL_SSL/SSL) cannot be probed without the
    # deployment's truststore material -- detect it from the pod env and
    # fall back to pod readiness with a warning instead of blocking every
    # upgrade on an unprobeable-but-healthy quorum.
    out="$(kubectl -n "$NAMESPACE" exec "$pod" -- bash -c '
      case "$KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP" in
        *CONTROLLER:SSL*|*CONTROLLER:SASL_SSL*) echo KFUSE_TLS_CONTROLLER_LISTENER; exit 0 ;;
      esac
      cfg=/tmp/kfuse-quorum.properties
      printf "security.protocol=SASL_PLAINTEXT\nsasl.mechanism=PLAIN\nsasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username=\"%s\" password=\"%s\";\n" "$KAFKA_CONTROLLER_USER" "$KAFKA_CONTROLLER_PASSWORD" > "$cfg"
      kafka-metadata-quorum.sh --bootstrap-controller localhost:9093 --command-config "$cfg" describe --status 2>/dev/null \
        || kafka-metadata-quorum.sh --bootstrap-controller localhost:9093 describe --status 2>/dev/null
      rm -f "$cfg"' 2>/dev/null || true)"
    if printf '%s\n' "$out" | grep -q 'KFUSE_TLS_CONTROLLER_LISTENER'; then
      warn "$pod: controller listener uses TLS -- quorum probe unsupported, relying on pod readiness only"
      return 0
    fi
    # LeaderId >= 0 means the quorum has an elected leader (-1 = none).
    if printf '%s\n' "$out" | grep -Eq 'LeaderId:[[:space:]]*[0-9]'; then
      info "$pod: KRaft quorum has a leader"
      return 0
    fi
    tries=$((tries + 1))
    [ "$tries" -eq 1 ] && info "waiting for KRaft quorum after $pod restart..."
    [ "$tries" -ge "$max" ] && die "KRaft quorum not confirmed after ${POD_TIMEOUT}s following $pod restart -- investigate before continuing (re-run resumes here)"
    sleep 5
  done
}

# Pinot health endpoints, checked in-pod. Needed because the kfuse chart
# disables the pinot readiness probes by default (server/broker), so pod
# Ready only proves the container started. Ports are the pinot chart
# defaults (controller.ports.admin/broker.ports.admin/server.ports.admin).
pinot_health() { # <pod> <url-path-with-port>
  local pod="$1" url="$2" tries=0 max=$(( POD_TIMEOUT / 5 ))
  while :; do
    kubectl -n "$NAMESPACE" exec "$pod" -- curl -sf --max-time 5 "http://localhost:$url" >/dev/null 2>&1 \
      && { info "$pod: healthy ($url)"; return 0; }
    tries=$((tries + 1))
    [ "$tries" -eq 1 ] && info "waiting for $pod health ($url)..."
    [ "$tries" -ge "$max" ] && die "$pod not healthy on $url after ${POD_TIMEOUT}s (segment reload can be slow -- raise --pod-timeout if legitimate)"
    sleep 5
  done
}

health_gate() { # <class> <pod> <replicas>
  case "$1" in
    zookeeper)              zk_quorum_check "$2" "$3" ;;
    kafka-controller)       kafka_quorum_check "$2" ;;
    pinot-controller)       pinot_health "$2" "9000/health" ;;
    pinot-broker)           pinot_health "$2" "8099/health" ;;
    pinot-server-realtime|pinot-server-offline)
                            pinot_health "$2" "8097/health/readiness" ;;
    *) : ;;  # kafka broker (URP gate: future work, doc 6.9) + minion rely on pod readiness
  esac
}

# ---------------------------------------------------------------------------
# Restarts
# ---------------------------------------------------------------------------

restart_one_sts() { # <sts> <class> <replicas>
  local sts="$1" class="$2" replicas="$3" mode="rolling" stale pod old_uid uids spec
  wait_sts_observed "$sts"
  # shellcheck disable=SC2086
  matches_any "$sts" "$class" $RECREATE_GLOBS && mode="recreate"
  [ "$class" = "zookeeper" ] && mode="rolling"   # never mass-delete a quorum

  stale="$(stale_pods "$sts" "$replicas")"
  # Force-restart cycles ALL ordinals, not just stale ones: scale-up pods
  # created in Phase 1 are already on the new revision, but may have opened
  # consuming segments against the old schema before setup-pinot completed,
  # so a schema change must restart them too.
  # shellcheck disable=SC2086
  if matches_any "$sts" "$class" $FORCE_GLOBS; then
    info "$sts: force-restart -- cycling all $replicas pods"
    pod=$((replicas - 1)); stale=""
    while [ "$pod" -ge 0 ]; do stale="$stale ${sts}-${pod}"; pod=$((pod - 1)); done
  fi
  if [ -z "${stale// /}" ]; then
    info "$sts: up to date -- verifying all $replicas ordinals (readiness + health)"
    verify_component "$sts" "$class" "$replicas"
    return 0
  fi

  log "Restarting $sts ($class, mode=$mode):$stale"
  if [ "$mode" = "recreate" ]; then
    # OnDelete + podManagementPolicy: Parallel => all replacements come up
    # at once on the new revision. Pods are always addressed by ordinal
    # name, never by label (pinot aliases share identical labels).
    # NOTE: kubectl delete bypasses PodDisruptionBudgets by design here.
    # --ignore-not-found: a force-listed ordinal may be absent (or vanish
    # between the scan and the delete); the readiness wait converges it.
    # Pre-delete UIDs let the wait distinguish the replacement pod from the
    # old one still Terminating (an absent pod yields "", disabling the check).
    uids=""
    for pod in $stale; do uids="$uids ${pod}=$(pod_uid "$pod")"; done
    # shellcheck disable=SC2086
    kubectl -n "$NAMESPACE" delete pod $stale --wait=false --ignore-not-found
    for spec in $uids; do wait_pod_ready "${spec%%=*}" "${spec#*=}"; done
    for pod in $stale; do health_gate "$class" "$pod" "$replicas"; done
  else
    for pod in $stale; do
      old_uid="$(pod_uid "$pod")"
      # --wait=false: kubectl's foreground delete blocks until it observes
      # the pod gone, but the StatefulSet controller recreates the same-named
      # pod almost immediately -- if kubectl misses that window (or its watch
      # connection stalls) it hangs forever with no timeout, freezing the
      # rolling restart after "pod deleted" with the pod already Running.
      # Replacement is detected by the UID change in wait_pod_ready instead.
      kubectl -n "$NAMESPACE" delete pod "$pod" --wait=false --ignore-not-found
      wait_pod_ready "$pod" "$old_uid"
      health_gate "$class" "$pod" "$replicas"
    done
  fi
  verify_component "$sts" "$class" "$replicas"
  info "$sts: all $replicas replicas Ready and healthy on new revision"
}

# Discovers managed STS, prints the full restart plan, and prompts once.
# Sets PLAN_ANY=true when at least one component needs action.
plan_restarts() {
  local class line sts c replicas any=false
  DISCOVERED="$WORKDIR/sts.list"
  discover_sts > "$DISCOVERED"
  PLAN_ANY=false
  [ -s "$DISCOVERED" ] || { warn "no managed StatefulSets found in namespace $NAMESPACE"; return 0; }

  # Ensure the controller has observed every new spec before computing the
  # plan, so what the operator confirms matches what actually runs.
  while read -r sts c replicas; do wait_sts_observed "$sts"; done < "$DISCOVERED"

  log "Restart plan (namespace=$NAMESPACE)"
  printf '    %-28s %-22s %-9s %s\n' STATEFULSET CLASS REPLICAS ACTION
  for class in $CLASS_ORDER; do
    while read -r sts c replicas; do
      [ "$c" = "$class" ] || continue
      local stale mode="rolling" action
      # shellcheck disable=SC2086
      matches_any "$sts" "$c" $RECREATE_GLOBS && mode="recreate"
      [ "$c" = "zookeeper" ] && mode="rolling"
      stale="$(stale_pods "$sts" "$replicas")"
      # shellcheck disable=SC2086
      if matches_any "$sts" "$c" $FORCE_GLOBS; then action="$mode (forced, all $replicas)"
      elif [ -n "${stale// /}" ]; then action="$mode ($(echo $stale | wc -w | tr -d ' ') pod(s))"
      else action="skip (up to date)"; fi
      printf '    %-28s %-22s %-9s %s\n' "$sts" "$c" "$replicas" "$action"
      [ "$action" != "skip (up to date)" ] && any=true
    done < "$DISCOVERED"
  done

  if [ "$any" = false ]; then log "Nothing to restart."; return 0; fi
  PLAN_ANY=true
  if [ "$ASSUME_YES" = false ] && [ -t 0 ]; then
    printf '\nProceed with restarts? [y/N] '
    read -r reply
    case "$reply" in y|Y|yes) : ;; *) die "aborted by user" ;; esac
  fi
}

# After a successful run, flip the managed StatefulSets back to
# RollingUpdate. OnDelete is only needed WHILE the orchestrator sequences
# restarts; leaving it active between upgrades makes 'kubectl rollout
# restart' a silent no-op and risks unnoticed staleness. The patch touches
# only spec.updateStrategy (not the pod template), so nothing restarts, and
# all pods are already on the latest revision. The helm release manifest
# still records OnDelete -- harmless: the next upgrade (orchestrated or
# not) overwrites the strategy either way.
revert_strategies() {
  local sts class replicas failed=0
  [ -s "${DISCOVERED:-/dev/null}" ] || return 0
  log "Restoring original updateStrategy on managed StatefulSets"
  local orig
  while read -r sts class replicas; do
    # Restore the exact pre-run strategy when we snapshotted one (preserves
    # user-configured rollingUpdate fields); StatefulSets first seen during
    # this run (new aliases) get the plain RollingUpdate default. A
    # snapshotted OnDelete (stale from an aborted earlier run) is not worth
    # preserving -- restore RollingUpdate for it too.
    orig="$(awk -F'\t' -v s="$sts" '$1==s{print $2}' "$WORKDIR/orig-strategies.tsv" 2>/dev/null | head -1)"
    case "$orig" in *'"OnDelete"'*|"") orig='{"type":"RollingUpdate"}' ;; esac
    if kubectl -n "$NAMESPACE" patch sts "$sts" --type merge \
        -p "{\"spec\":{\"updateStrategy\":$orig}}" >/dev/null; then
      info "$sts: restored $orig"
    else
      warn "$sts: failed to restore updateStrategy"
      failed=$((failed + 1))
    fi
  done < "$DISCOVERED"
  [ "$failed" -eq 0 ] || die "$failed StatefulSet(s) still on OnDelete -- kubectl rollout restart will silently no-op on them; patch manually or re-run"
}

# Executes restarts for the given classes, in the given order, using the
# discovery from plan_restarts. Staleness is recomputed per StatefulSet at
# execution time, so an already-converged component is skipped.
run_restart_classes() { # <class...>
  local class sts c replicas
  [ -s "${DISCOVERED:-/dev/null}" ] || return 0
  for class in "$@"; do
    while read -r sts c replicas; do
      [ "$c" = "$class" ] || continue
      restart_one_sts "$sts" "$c" "$replicas"
    done < "$DISCOVERED"
  done
}

# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

list_managed_jobs() { # [glob list] (default: all managed job globs)
  local globs="${1:-$JOB_GLOBS}" out j g
  if ! out="$(kubectl -n "$NAMESPACE" get jobs -o name 2>"$WORKDIR/jobs.err")"; then
    # Tolerate only a confirmed-missing namespace (fresh install, pre
    # --create-namespace), classified from the original error -- probing
    # 'kubectl get ns' is not a valid discriminator (it can be Forbidden
    # for a namespaced operator while the namespace exists). Anything else
    # must not read as "no jobs to wait for".
    grep -qi 'not found' "$WORKDIR/jobs.err" && return 0
    die "cannot list jobs in $NAMESPACE: $(tail -1 "$WORKDIR/jobs.err" 2>/dev/null)"
  fi
  for j in $(printf '%s\n' "$out" | sed 's#^job.batch/##'); do
    for g in $globs; do
      # shellcheck disable=SC2254
      case "$j" in $g) echo "$j" ;; esac
    done
  done
}

delete_stale_jobs() {
  local jobs
  jobs="$(list_managed_jobs)"
  [ -z "$jobs" ] && { info "no leftover setup jobs"; return 0; }
  log "Deleting leftover setup jobs (static names + immutable spec.template)"
  # shellcheck disable=SC2086
  kubectl -n "$NAMESPACE" delete job $jobs --ignore-not-found --wait=true
}

wait_for_jobs() { # [glob list]
  local jobs j deadline jout
  # Jobs are created by the upgrade itself; give them a moment to appear.
  sleep 10
  jobs="$(list_managed_jobs "${1:-}")"
  [ -z "$jobs" ] && { info "no setup jobs found (nothing enabled?)"; return 0; }
  log "Waiting for setup jobs:"
  for j in $jobs; do info "$j"; done
  local seen
  for j in $jobs; do
    deadline=$(( $(date +%s) + JOB_TIMEOUT ))
    seen=false
    while :; do
      # One API call for existence AND conditions: separate reads could
      # race the TTL controller (job completes and is collected between
      # the existence check and the condition read, misreading success
      # as an external deletion).
      if ! jout="$(kubectl -n "$NAMESPACE" get job "$j" -o jsonpath='{range .status.conditions[*]}{.type}={.status} {end}' 2>"$WORKDIR/jobget.err")"; then
        if grep -qi 'notfound\|not found' "$WORKDIR/jobget.err"; then
          if [ "$seen" = true ]; then
            # We polled this job every 10s and never observed Complete;
            # TTL (60s after finish) cannot outrun that -- something
            # external deleted it, or it failed and was collected.
            die "job $j disappeared without an observed Complete condition -- externally deleted? Re-run '$0 run-job $j' to re-apply it"
          fi
          # Never seen alive: completed and TTL-collected before our
          # first poll (fast job + slow helm return).
          info "$j: gone (completed + TTL-collected)"
          break
        fi
        # Transient API error: keep polling until the deadline, don't
        # mistake it for TTL completion.
        [ "$(date +%s)" -ge "$deadline" ] && die "cannot read job $j: $(tail -1 "$WORKDIR/jobget.err" 2>/dev/null)"
        sleep 10; continue
      fi
      seen=true
      case " $jout " in
        *" Failed=True "*)   die "job $j failed -- inspect with: kubectl -n $NAMESPACE logs job/$j --all-containers" ;;
        *" Complete=True "*) info "$j: complete"; break ;;
      esac
      [ "$(date +%s)" -ge "$deadline" ] && die "timed out waiting for job $j"
      sleep 10
    done
  done
}

# ---------------------------------------------------------------------------
# Pinot schema change detection (schema-only releases don't change server
# pod specs, so revision-diffing alone would skip the needed server restart)
# ---------------------------------------------------------------------------

snapshot_schemas() { # <outfile>
  local out
  if ! out="$(kubectl -n "$NAMESPACE" get cm -o json 2>"$WORKDIR/cm.err")"; then
    # Only a confirmed-missing namespace (fresh install) yields an empty
    # snapshot; any other error must not hide a schema change.
    grep -qi 'not found' "$WORKDIR/cm.err" && { : > "$1"; return 0; }
    die "cannot snapshot schema ConfigMaps: $(tail -1 "$WORKDIR/cm.err" 2>/dev/null)"
  fi
  # Only the pinot schema ConfigMaps (kfuse-<pinot-fullname>-<table>-schema);
  # a broader match could force server restarts on unrelated ConfigMaps.
  printf '%s\n' "$out" | jq -r '
    .items[] | select(.metadata.name | test("^kfuse-pinot.*-schema$"))
    | "\(.metadata.name)\t\(.data | tojson | @base64)"' | sort > "$1"
}

# ---------------------------------------------------------------------------
# Helm
# ---------------------------------------------------------------------------

registry_login() {
  [ "$SKIP_LOGIN" = true ] && return 0
  if [ -n "$TOKEN_FILE" ]; then
    # Customer flow: service-account key from the Kloudfuse trial/license
    # (see docs: setup/install/helm.adoc).
    [ -f "$TOKEN_FILE" ] || die "token file not found: $TOKEN_FILE"
    log "Logging in to $REGISTRY_HOST with $TOKEN_FILE"
    helm registry login -u _json_key --password-stdin "$REGISTRY_HOST" < "$TOKEN_FILE"
  elif command -v gcloud >/dev/null 2>&1; then
    log "Logging in to $REGISTRY_HOST via gcloud"
    gcloud auth print-access-token | helm registry login -u oauth2accesstoken --password-stdin "$REGISTRY_HOST"
  else
    # helm caches registry credentials from any earlier 'helm registry login'
    info "no gcloud and no --token given; relying on an existing helm registry login session"
  fi
}

version_guard() { # <target-version>
  local current cur_base tgt_base
  if ! current="$(kubectl -n "$NAMESPACE" get cm kfuse-version -o jsonpath='{.data.version}' 2>"$WORKDIR/ver.err")"; then
    # Only a confirmed NotFound (ConfigMap or namespace) means fresh
    # install; an API/RBAC error must not bypass the downgrade check.
    if grep -qi 'not found' "$WORKDIR/ver.err"; then
      current=""
    else
      die "cannot read kfuse-version ConfigMap: $(tail -1 "$WORKDIR/ver.err" 2>/dev/null)"
    fi
  fi
  [ -z "$current" ] && { info "no kfuse-version ConfigMap (fresh install?)"; return 0; }
  info "current version: $current, target: $1"
  # Mirror the chart's guard (validation.yaml): compare major.minor.patch
  # only, so prerelease hops like 4.3.0-rc2 -> 4.3.0 are allowed.
  cur_base="${current%%-*}"; tgt_base="${1%%-*}"
  [ "$tgt_base" = "$cur_base" ] && return 0
  if sort -V </dev/null >/dev/null 2>&1; then
    if [ "$(printf '%s\n%s\n' "$tgt_base" "$cur_base" | sort -V | tail -1)" = "$cur_base" ]; then
      die "target $1 is older than installed $current -- the chart's downgrade guard will reject this; use '$0 rollback' instead"
    fi
  else
    warn "sort -V unavailable; skipping downgrade pre-check (the chart's own guard still applies)"
  fi
}

helm_chart_args() { # sets CHART_ARGS_STR
  if [ "$TARGET" = "local" ]; then
    [ -d "$CHART_DIR" ] || die "chart dir not found: $CHART_DIR"
    if [ "$SKIP_DEPS" = false ]; then
      log "Updating chart dependencies in $CHART_DIR"
      registry_login
      helm dep update "$CHART_DIR"
    fi
    CHART_ARGS_STR="$CHART_DIR"
  else
    registry_login
    version_guard "$TARGET"
    CHART_ARGS_STR="$OCI_CHART --version $TARGET"
  fi
}

split_manifest() { # <infile> <outdir>
  mkdir -p "$2"
  awk -v dir="$2" '
    function flush(   n, L, i, kind, nm, f) {
      if (doc == "") return
      n = split(doc, L, "\n")
      kind = ""; nm = ""
      for (i = 1; i <= n; i++) {
        if (L[i] ~ /^kind: /) kind = substr(L[i], 7)
        else if (L[i] ~ /^  name: / && nm == "") nm = substr(L[i], 9)
      }
      if (kind != "" && nm != "") {
        gsub(/[^A-Za-z0-9._-]/, "_", kind); gsub(/[^A-Za-z0-9._-]/, "_", nm)
        f = dir "/" kind "." nm ".yaml"
        printf "%s", doc > f
        close(f)
      }
      doc = ""
    }
    /^---[[:space:]]*$/ { flush(); next }
    { doc = doc $0 "\n" }
    END { flush() }
  ' "$1"
}

dry_run_diff() {
  if [ "$IS_INSTALL" = true ]; then
    log "Release $RELEASE not found -- rendering fresh-install manifest (no diff)"
    # No live objects to look up yet, so plain client-side render.
    # shellcheck disable=SC2086
    helm template "$RELEASE" $CHART_ARGS_STR -n "$NAMESPACE" \
      -f "$VALUES_FILE" $VALUES_ARGS -f "$ONDELETE_FILE" $SET_ARGS > "$WORKDIR/new.yaml"
    grep -E '^(kind|  name):' "$WORKDIR/new.yaml" | paste - - | sed 's/^/    /'
    return 0
  fi
  log "Rendering target manifest (helm template --dry-run=server --is-upgrade)"
  # shellcheck disable=SC2086
  helm template "$RELEASE" $CHART_ARGS_STR -n "$NAMESPACE" \
    -f "$VALUES_FILE" $VALUES_ARGS -f "$ONDELETE_FILE" $SET_ARGS \
    --dry-run=server --is-upgrade > "$WORKDIR/new.yaml"
  log "Fetching live release manifest"
  helm get manifest "$RELEASE" -n "$NAMESPACE" > "$WORKDIR/cur.yaml"
  split_manifest "$WORKDIR/cur.yaml" "$WORKDIR/cur"
  split_manifest "$WORKDIR/new.yaml" "$WORKDIR/new"
  # Redact Secret contents before any diff output persists: the rendered
  # manifests include live credential material (kafka SASL/TLS, PG, ...).
  # The resource-level listing still shows WHICH secrets changed.
  local d f
  for d in "$WORKDIR/cur" "$WORKDIR/new"; do
    find "$d" -name 'Secret.*.yaml' | while read -r f; do
      printf 'REDACTED Secret (content sha256: %s)\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" > "$f"
    done
  done
  log "Resources that would change:"
  diff -rq "$WORKDIR/cur" "$WORKDIR/new" | sed 's/^/    /' || true
  log "Dry run complete -- no changes applied."
  ( umask 077; diff -r "$WORKDIR/cur" "$WORKDIR/new" > "./kfuse-upgrade-dry-run.diff" || true )
  info "full diff (secrets redacted) written to ./kfuse-upgrade-dry-run.diff (mode 600)"
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

cmd_upgrade() {
  VALUES_FILE="${1:-}"; TARGET="${2:-}"
  [ -n "$VALUES_FILE" ] && [ -n "$TARGET" ] || die "usage: $0 upgrade <values.yaml> <version|local> [options]"
  [ -f "$VALUES_FILE" ] || die "values file not found: $VALUES_FILE"
  need kubectl; need helm; need jq

  # Fresh install vs upgrade: on install there is nothing to restart --
  # StatefulSets create their pods normally regardless of OnDelete, and the
  # setup jobs run for the first time, so phases 0/3 mostly no-op.
  IS_INSTALL=false
  if ! helm status "$RELEASE" -n "$NAMESPACE" >/dev/null 2>"$WORKDIR/helm.err"; then
    # Only a confirmed missing release means fresh install; an API/RBAC/
    # context error must not silently switch to install-mode behavior.
    grep -qi "not found" "$WORKDIR/helm.err" && IS_INSTALL=true \
      || die "helm status failed: $(tail -1 "$WORKDIR/helm.err" 2>/dev/null)"
  fi

  write_ondelete_values
  helm_chart_args

  if [ "$DRY_RUN" = true ]; then
    dry_run_diff
    return 0
  fi

  # The generated OnDelete file is a -f layer, and helm gives ANY --set
  # higher precedence than every -f -- so a strategy override would defeat
  # orchestration before assert_strategies could catch it. Reject up front.
  case "$SET_ARGS" in *updateStrategy*) die "--set must not override updateStrategy keys -- the orchestrator owns them" ;; esac

  acquire_lock

  log "Phase 0: preflight (namespace=$NAMESPACE release=$RELEASE target=$TARGET install=$IS_INSTALL)"
  delete_stale_jobs
  snapshot_schemas "$WORKDIR/schemas.pre"
  if [ "$IS_INSTALL" = false ]; then
    # Discovery failure OR an empty result must abort: an empty pin list
    # would reopen the three-way-merge hole (live RollingUpdate surviving
    # the upgrade). An existing kfuse release always has managed
    # StatefulSets; none found means the label contract broke.
    discover_sts > "$WORKDIR/pre-sts.list"
    [ -s "$WORKDIR/pre-sts.list" ] || die "no managed StatefulSets discovered for existing release '$RELEASE' -- refusing to proceed (discovery/label contract changed?)"
    pin_strategies "$WORKDIR/pre-sts.list"
  fi

  log "Phase 1: helm upgrade (stateful tiers pinned via OnDelete)"
  # shellcheck disable=SC2086
  helm upgrade --install --create-namespace "$RELEASE" $CHART_ARGS_STR -n "$NAMESPACE" \
    -f "$VALUES_FILE" $VALUES_ARGS -f "$ONDELETE_FILE" $SET_ARGS
  discover_sts > "$WORKDIR/post-sts.list"
  assert_strategies "$WORKDIR/post-sts.list"

  log "Phase 2a: waiting for infra jobs (pgdb, kafka topics)"
  wait_for_jobs "$INFRA_JOB_GLOBS"

  # Restart the control plane BEFORE waiting on setup-pinot: new table
  # configs may only validate against the new controller (e.g. new minion
  # task types like KfMergeTask); the job retries until the controller is up.
  log "Phase 3a: control-plane restarts (zookeeper -> kafka -> pinot controller)"
  plan_restarts
  # shellcheck disable=SC2086
  run_restart_classes $PRE_SETUP_CLASSES

  wait_for_scale_up

  log "Phase 2b: waiting for setup-pinot jobs (schemas/table configs land BEFORE data-plane restarts)"
  wait_for_jobs "$SETUP_JOB_GLOBS"

  snapshot_schemas "$WORKDIR/schemas.post"
  # Schema diff only means "force server restart" on an upgrade; on a fresh
  # install the pre-snapshot is empty and the pods are already current.
  if [ "$IS_INSTALL" = false ] && ! cmp -s "$WORKDIR/schemas.pre" "$WORKDIR/schemas.post"; then
    log "Pinot schema ConfigMaps changed -- forcing server restart"
    FORCE_GLOBS="$FORCE_GLOBS pinot-server-realtime pinot-server-offline"
  fi

  log "Phase 3b: data-plane restarts (pinot broker -> servers -> minion)"
  # shellcheck disable=SC2086
  run_restart_classes $POST_SETUP_CLASSES

  log "Phase 4: verify"
  cmd_status || die "verification failed -- see stale components above"
  revert_strategies
  log "Upgrade complete."
}

cmd_status() {
  need kubectl; need jq
  local line sts class replicas stale ready strat lock_absent=true bad=0 nstale=0 total=0 jobs j jf jc
  # Namespaced probe only: 'kubectl get ns' is cluster-scoped and may be
  # Forbidden for an operator Role that can do everything else it needs.
  discover_sts > "$WORKDIR/status.list" \
    || die "cannot list StatefulSets in namespace '$NAMESPACE'"
  kubectl -n "$NAMESPACE" get configmap "kfuse-upgrade-lock-$RELEASE" >/dev/null 2>&1 && lock_absent=false
  log "StatefulSet status (namespace=$NAMESPACE)"
  printf '    %-28s %-22s %-9s %-7s %-6s %s\n' STATEFULSET CLASS REPLICAS READY STALE STRATEGY
  while read -r sts class replicas; do
    wait_sts_observed "$sts"
    stale="$(stale_pods "$sts" "$replicas")"
    ready="$(kubectl -n "$NAMESPACE" get sts "$sts" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)"
    ready="${ready:-0}"
    strat="$(kubectl -n "$NAMESPACE" get sts "$sts" -o jsonpath='{.spec.updateStrategy.type}' 2>/dev/null)"
    # shellcheck disable=SC2086
    local n; n=$(echo $stale | wc -w | tr -d ' ')
    printf '    %-28s %-22s %-9s %-7s %-6s %s\n' "$sts" "$class" "$replicas" "$ready/$replicas" "${n:-0}" "$strat"
    total=$((total + 1)); nstale=$((nstale + n))
    [ "$ready" -lt "$replicas" ] && bad=$((bad + 1))
    # OnDelete with no orchestrator lock present = drift from an aborted
    # run: kubectl rollout restart silently no-ops on this tier. A present
    # lock might itself be stale (SIGKILL'd run never runs the trap), so
    # never stay silent about OnDelete -- warn either way, fail only when
    # no run can plausibly be in progress.
    if [ "$strat" = "OnDelete" ] && [ "$LOCK_HELD" = false ]; then
      if [ "$lock_absent" = true ]; then
        warn "$sts: stale OnDelete strategy (no orchestrator run in progress) -- re-run upgrade or restore RollingUpdate"
        bad=$((bad + 1))
      else
        warn "$sts: OnDelete while an orchestrator lock exists -- fine if a run is in progress; if not, the lock is stale (kubectl -n $NAMESPACE delete configmap kfuse-upgrade-lock-$RELEASE) and this tier needs attention"
      fi
    fi
  done < "$WORKDIR/status.list"
  jobs="$(list_managed_jobs)"
  if [ -n "$jobs" ]; then
    log "Setup jobs present (not yet TTL-collected):"
    for j in $jobs; do
      jf="$(kubectl -n "$NAMESPACE" get job "$j" -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' 2>/dev/null || true)"
      jc="$(kubectl -n "$NAMESPACE" get job "$j" -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null || true)"
      if [ "$jf" = "True" ]; then
        warn "$j: FAILED"; bad=$((bad + 1))
      elif [ "$jc" = "True" ]; then
        info "$j: complete"
      else
        warn "$j: still running/pending"; bad=$((bad + 1))
      fi
    done
  fi
  [ "$nstale" -eq 0 ] || { warn "$nstale stale pod(s) across $total StatefulSets -- run '$0 restart \"<sts-or-class-glob>\" -n $NAMESPACE' (e.g. restart \"pinot-*\") to converge"; return 1; }
  [ "$bad" -eq 0 ] || { warn "$bad component(s) not fully ready / failed jobs"; return 1; }
  info "all $total managed StatefulSets are up to date and fully ready"
}

cmd_restart() {
  local pattern="${1:-}"
  [ -n "$pattern" ] || die "usage: $0 restart <sts-name-or-class-glob> [options]"
  need kubectl; need jq
  # Limit the plan to matching STS by treating everything else as up to date:
  # reuse restart_phase but filter via a wrapper around discover_sts output.
  discover_sts > "$WORKDIR/all.list"
  : > "$WORKDIR/sel.list"
  while read -r sts class replicas; do
    # shellcheck disable=SC2254
    case "$sts" in $pattern) echo "$sts $class $replicas" >> "$WORKDIR/sel.list"; continue ;; esac
    # shellcheck disable=SC2254
    case "$class" in $pattern) echo "$sts $class $replicas" >> "$WORKDIR/sel.list" ;; esac
  done < "$WORKDIR/all.list"
  [ -s "$WORKDIR/sel.list" ] || die "no managed StatefulSet matches '$pattern'"
  acquire_lock
  # 'restart' implies the user wants a restart even if revisions are current.
  FORCE_GLOBS="$FORCE_GLOBS $pattern"
  local class sts c replicas
  for class in $CLASS_ORDER; do
    while read -r sts c replicas; do
      [ "$c" = "$class" ] || continue
      restart_one_sts "$sts" "$c" "$replicas"
    done < "$WORKDIR/sel.list"
  done
}

cmd_rollback() {
  local revision="${1:-}" target_rev orchestrated=true
  need kubectl; need helm; need jq
  # Resolve the target revision (helm defaults to previous) and check
  # whether its manifest carries OnDelete. Rolling back to a revision from
  # the pre-orchestrator era re-applies RollingUpdate strategies AND new
  # pod templates in one shot -- kubernetes rolls everything concurrently
  # (plain helm behavior) and the ordered-restart phases have nothing to do.
  # Lock BEFORE resolving the implicit target: a concurrent upgrade could
  # commit a new revision between the history read and the rollback,
  # silently changing which revision "previous" refers to.
  acquire_lock
  if [ -n "$revision" ]; then target_rev="$revision"
  else target_rev="$(helm history "$RELEASE" -n "$NAMESPACE" -o json | jq -r '.[-2].revision // empty')"
  fi
  [ -n "$target_rev" ] || die "no previous revision to roll back to (helm history shows a single revision)"
  # Capture to a file: piping into grep -q under pipefail can SIGPIPE
  # helm and misclassify the target; a read error must abort, not
  # silently downgrade to unorchestrated behavior.
  helm get manifest "$RELEASE" -n "$NAMESPACE" --revision "$target_rev" \
    > "$WORKDIR/target-manifest.yaml" 2>"$WORKDIR/manifest.err" \
    || die "cannot read manifest for revision $target_rev: $(tail -1 "$WORKDIR/manifest.err" 2>/dev/null)"
  # Classify per managed StatefulSet, not by a manifest-wide grep: a mixed
  # target (some tiers OnDelete, some not) or a stray OnDelete string in an
  # unrelated resource must not count as orchestrated. Ambiguity is treated
  # conservatively as unorchestrated.
  discover_sts > "$WORKDIR/pre-sts.list"
  [ -s "$WORKDIR/pre-sts.list" ] || die "no managed StatefulSets discovered for release '$RELEASE' -- refusing to roll back (discovery/label contract changed?)"
  split_manifest "$WORKDIR/target-manifest.yaml" "$WORKDIR/target"
  local msts found=false
  orchestrated=true
  while read -r msts class replicas; do
    if [ -f "$WORKDIR/target/StatefulSet.$msts.yaml" ]; then
      found=true
      grep -q 'type: OnDelete' "$WORKDIR/target/StatefulSet.$msts.yaml" || orchestrated=false
    fi
  done < "$WORKDIR/pre-sts.list"
  [ "$found" = true ] || orchestrated=false
  if [ "$orchestrated" = false ]; then
    warn "revision $target_rev predates the orchestrator (managed StatefulSets not uniformly OnDelete):"
    warn "helm will roll all components concurrently, like a plain 'helm rollback'"
  fi
  log "Rolling back release $RELEASE (revision: $target_rev)"
  delete_stale_jobs
  snapshot_schemas "$WORKDIR/schemas.pre"
  if [ "$orchestrated" = true ]; then
    pin_strategies "$WORKDIR/pre-sts.list"   # helm won't reassert an unchanged field
  fi
  # Pass the resolved revision explicitly: it was determined under the
  # lock, so helm cannot re-resolve "previous" to something newer.
  helm rollback "$RELEASE" "$target_rev" -n "$NAMESPACE"
  wait_for_jobs "$INFRA_JOB_GLOBS"
  if [ "$orchestrated" = false ]; then
    wait_for_jobs "$SETUP_JOB_GLOBS"
    # Kubernetes is rolling everything itself; wait for convergence and
    # propagate failure so automation cannot mistake a stuck rollback
    # for success.
    log "Waiting for RollingUpdate convergence (unorchestrated rollback)"
    local sdeadline=$(( $(date +%s) + POD_TIMEOUT ))
    until cmd_status >/dev/null 2>&1; do
      [ "$(date +%s)" -ge "$sdeadline" ] && { cmd_status || true; die "rollback did not converge within ${POD_TIMEOUT}s"; }
      sleep 15
    done
    # Schema parity with the orchestrated path: a schema-only rollback
    # leaves server pod templates unchanged, so RollingUpdate never cycles
    # them and consuming segments keep the pre-rollback schema. Deleting
    # the pods under RollingUpdate recreates them on the same (rolled-back)
    # spec, which is exactly the restart needed.
    snapshot_schemas "$WORKDIR/schemas.post"
    if ! cmp -s "$WORKDIR/schemas.pre" "$WORKDIR/schemas.post"; then
      log "Pinot schema ConfigMaps changed by rollback -- restarting servers"
      DISCOVERED="$WORKDIR/pre-sts.list"
      FORCE_GLOBS="$FORCE_GLOBS pinot-server-realtime pinot-server-offline"
      run_restart_classes pinot-server-realtime pinot-server-offline
    fi
    cmd_status
    return 0
  fi
  log "Restarting components onto rolled-back revision"
  plan_restarts
  # shellcheck disable=SC2086
  run_restart_classes $PRE_SETUP_CLASSES
  wait_for_scale_up
  wait_for_jobs "$SETUP_JOB_GLOBS"
  snapshot_schemas "$WORKDIR/schemas.post"
  if ! cmp -s "$WORKDIR/schemas.pre" "$WORKDIR/schemas.post"; then
    log "Pinot schema ConfigMaps changed by rollback -- forcing server restart"
    FORCE_GLOBS="$FORCE_GLOBS pinot-server-realtime pinot-server-offline"
  fi
  # shellcheck disable=SC2086
  run_restart_classes $POST_SETUP_CLASSES
  cmd_status
  revert_strategies
}

cmd_run_job() {
  local job="${1:-}"
  [ -n "$job" ] || die "usage: $0 run-job <job-name> [options]"
  need kubectl; need helm
  acquire_lock
  log "Extracting job $job from the live release manifest (helm get manifest)"
  # Capture first: awk exits at the first match, and under pipefail the
  # resulting SIGPIPE to helm would abort the command spuriously.
  helm get manifest "$RELEASE" -n "$NAMESPACE" > "$WORKDIR/release-manifest.yaml"
  awk -v job="$job" '
    function flush() {
      if (doc ~ /(^|\n)kind: Job(\n|$)/ && doc ~ ("(^|\n)  name: " job "(\n|$)")) { printf "%s", doc; found = 1; exit }
      doc = ""
    }
    /^---[[:space:]]*$/ { flush(); next }
    { doc = doc $0 "\n" }
    END { if (!found) flush() }
  ' "$WORKDIR/release-manifest.yaml" > "$WORKDIR/job.yaml"
  [ -s "$WORKDIR/job.yaml" ] || die "job $job not found in release manifest"
  kubectl -n "$NAMESPACE" delete job "$job" --ignore-not-found --wait=true
  kubectl -n "$NAMESPACE" apply -f "$WORKDIR/job.yaml"
  local deadline jout; deadline=$(( $(date +%s) + JOB_TIMEOUT ))
  while :; do
    # Single call for existence + conditions; we just created this job, so
    # NotFound here means it completed and hit ttlSecondsAfterFinished
    # between polls -- success, not failure.
    if ! jout="$(kubectl -n "$NAMESPACE" get job "$job" -o jsonpath='{range .status.conditions[*]}{.type}={.status} {end}' 2>"$WORKDIR/jobget.err")"; then
      grep -qi 'notfound\|not found' "$WORKDIR/jobget.err" && { info "$job: gone (completed + TTL-collected)"; break; }
      [ "$(date +%s)" -ge "$deadline" ] && die "cannot read job $job: $(tail -1 "$WORKDIR/jobget.err" 2>/dev/null)"
      sleep 10; continue
    fi
    case " $jout " in
      *" Failed=True "*)   die "job $job failed -- kubectl -n $NAMESPACE logs job/$job --all-containers" ;;
      *" Complete=True "*) break ;;
    esac
    [ "$(date +%s)" -ge "$deadline" ] && die "timed out waiting for job $job"
    sleep 10
  done
  info "$job complete"
  # shellcheck disable=SC2254
  case "$job" in kfuse-setup-pinot*)
    warn "setup-pinot applies schemas/table configs; if schemas changed, restart the servers so consuming segments pick them up:"
    warn "  $0 restart 'pinot-server-*' -n $NAMESPACE"
  ;; esac
}

case "$COMMAND" in
  upgrade)  cmd_upgrade "$@" ;;
  status)   cmd_status "$@" ;;
  restart)  cmd_restart "$@" ;;
  rollback) cmd_rollback "$@" ;;
  run-job)  cmd_run_job "$@" ;;
  -h|--help|help) usage 0 ;;
  *) die "unknown command: $COMMAND (see --help)" ;;
esac
