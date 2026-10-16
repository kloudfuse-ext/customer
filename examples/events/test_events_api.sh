#!/usr/bin/env bash
# test_events_api.sh — Live validation of the Events API endpoints documented in
# reference/api/events.adoc. Run with:
#
#   TOKEN=<sa-token> HOST=<your-instance> bash test_events_api.sh
#
# Defaults to the Kloudfuse demo cluster if TOKEN/HOST are not set.

TOKEN=${TOKEN:-<your-kloudfuse-sa-token>}
HOST=${HOST:-<kloudfuse-hostname>}
DURATION_SECS=3600

PASS=0
FAIL=0

check() {
  local name="$1"
  local result="$2"
  local expect="$3"
  if echo "$result" | grep -q "$expect"; then
    echo "  PASS  $name"
    PASS=$((PASS+1))
  else
    echo "  FAIL  $name"
    echo "        Expected to find: $expect"
    echo "        Got: $(echo "$result" | head -5)"
    FAIL=$((FAIL+1))
  fi
}

echo "========================================================"
echo "  Events API live tests — $HOST"
echo "========================================================"

# ── events ──────────────────────────────────────────────────────────────────

echo
echo "── events ──────────────────────────────────────────────"

# 1. events — unfiltered, small limit
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d "{\"query\": \"{ events(durationSecs: $DURATION_SECS, limit: 3) { id title severity source eventType timestamp } }\"}")
check "events — id field present"       "$R" '"id"'
check "events — severity field present" "$R" '"severity"'
check "events — source field present"   "$R" '"source"'

# 2. events — filtered on a facet (note the required @ prefix)
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d "{\"query\": \"{ events(durationSecs: $DURATION_SECS, limit: 3, filter: { eq: { name: \\\"@source\\\", value: \\\"kubernetes\\\" } }) { id source } }\"}")
check "events (filtered by @source) — returns kubernetes events" "$R" '"kubernetes"'

# 3. events — combined filter (and)
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d "{\"query\": \"{ events(durationSecs: $DURATION_SECS, limit: 3, filter: { and: [{ eq: { name: \\\"@severity\\\", value: \\\"info\\\" } }, { eq: { name: \\\"@source\\\", value: \\\"kubernetes\\\" } }] }) { id severity source } }\"}")
check "events (and filter) — returns data without errors" "$R" '"data"'

# ── eventCounts ─────────────────────────────────────────────────────────────

echo
echo "── eventCounts ─────────────────────────────────────────"

# 4. eventCounts — grouped by facet
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d "{\"query\": \"{ eventCounts(durationSecs: $DURATION_SECS, groupBys: [\\\"@severity\\\"]) { timestamp count keys values } }\"}")
check "eventCounts — count field present" "$R" '"count"'
check "eventCounts — keys field present"  "$R" '"keys"'
check "eventCounts — values field present" "$R" '"values"'

# 5. eventCounts — time-bucketed
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d "{\"query\": \"{ eventCounts(durationSecs: $DURATION_SECS, roundSecs: 300, groupBys: [\\\"@source\\\"]) { timestamp count keys values } }\"}")
check "eventCounts (bucketed) — timestamp field present" "$R" '"timestamp"'

# ── facetValues / facetNames ────────────────────────────────────────────────

echo
echo "── facetValues / facetNames ────────────────────────────"

# 6. facetValues
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d "{\"query\": \"{ facetValues(durationSecs: $DURATION_SECS, facetName: \\\"@source\\\") { value count } }\"}")
check "facetValues — value field present" "$R" '"value"'
check "facetValues — count field present" "$R" '"count"'

# 7. facetNames
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d '{"query": "{ facetNames }"}')
check "facetNames — returns data without errors" "$R" '"data"'

# ── labelValues / labelNames ────────────────────────────────────────────────

echo
echo "── labelValues / labelNames ────────────────────────────"

# 8. labelNames — scoped to Kubernetes events
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/events-query" \
     -d "{\"query\": \"{ labelNames(durationSecs: $DURATION_SECS, filter: { eq: { name: \\\"@source\\\", value: \\\"kubernetes\\\" } }) }\"}")
check "labelNames — returns data without errors" "$R" '"data"'

# 9. labelValues — for one discovered label
LABEL=$(echo "$R" | python3 -c "import sys,json; d=json.load(sys.stdin); names=d.get('data',{}).get('labelNames') or []; print(names[0] if names else '')" 2>/dev/null)
if [ -n "$LABEL" ]; then
  R2=$(curl -s -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" \
       -X POST "https://$HOST/events-query" \
       -d "{\"query\": \"{ labelValues(durationSecs: $DURATION_SECS, labelName: \\\"$LABEL\\\") { value count } }\"}")
  check "labelValues ($LABEL) — value field present" "$R2" '"value"'
else
  echo "  SKIP  labelValues — could not extract a label name from labelNames"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo
echo "========================================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================================"
[ $FAIL -eq 0 ] && exit 0 || exit 1
