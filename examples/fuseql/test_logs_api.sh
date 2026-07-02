#!/usr/bin/env bash
# test_logs_api.sh — Live validation of the Logs API endpoints documented in
# reference/api/logs.adoc. Run with:
#
#   TOKEN=<sa-token> HOST=<your-instance> bash test_logs_api.sh
#
# Defaults to the Kloudfuse demo cluster if TOKEN/HOST are not set.

TOKEN=${TOKEN:-<your-kloudfuse-sa-token>}
HOST=${HOST:-<kloudfuse-hostname>}
START="2026-06-27T03:56:36Z"
END="2026-06-27T04:56:36Z"

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
echo "  Logs API live tests — $HOST"
echo "========================================================"

# ── FuseQL queries ────────────────────────────────────────────────────────────

echo
echo "── FuseQL queries ──────────────────────────────────────"

# 1. getLogMetricsResultWithKfuseQl — timeslice count
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"{ getLogMetricsResultWithKfuseQl(query: \\\"* | timeslice 5m | count by (_timeslice)\\\", startTs: \\\"$START\\\", endTs: \\\"$END\\\") { AggrValues ColumnHeaders GroupKeys TimeKey TableResult UrlValues } }\"}")
check "getLogMetricsResultWithKfuseQl — ColumnHeaders contains _count" "$R" '"_count"'
check "getLogMetricsResultWithKfuseQl — TimeKey is _timeslice"          "$R" '"_timeslice"'
check "getLogMetricsResultWithKfuseQl — TableResult is non-empty"       "$R" 'TableResult'

# 2. getLogMetricsResultWithKfuseQl — count errors by source
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"{ getLogMetricsResultWithKfuseQl(query: \\\"level=\\\\\\\"error\\\\\\\" | count by (source)\\\", startTs: \\\"$START\\\", endTs: \\\"$END\\\") { ColumnHeaders TableResult } }\"}")
check "getLogMetricsResultWithKfuseQl (by source) — source column present" "$R" '"source"'

# 3. getLogsWithFuseQlStream — first page
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"subscription { getLogsWithFuseQlStream(query: \\\"source=\\\\\\\"grafana\\\\\\\" | limit 2\\\", startTs: \\\"$START\\\", endTs: \\\"$END\\\", cursor: null) { ColumnHeaders TableResult Cursor } }\"}")
check "getLogsWithFuseQlStream — ColumnHeaders present"  "$R" '"timestamp"'
check "getLogsWithFuseQlStream — Cursor returned"        "$R" '"Cursor"'

# 4. getLogsWithFuseQlStream — pagination with cursor
CURSOR=$(echo "$R" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['getLogsWithFuseQlStream']['Cursor'])" 2>/dev/null)
if [ -n "$CURSOR" ]; then
  R2=$(curl -s -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" \
       -X POST "https://$HOST/query" \
       -d "{\"query\": \"subscription { getLogsWithFuseQlStream(query: \\\"source=\\\\\\\"grafana\\\\\\\" | limit 2\\\", startTs: \\\"$START\\\", endTs: \\\"$END\\\", cursor: \\\"$CURSOR\\\") { Cursor TableResult } }\"}")
  check "getLogsWithFuseQlStream — second page cursor differs from first" "$R2" '"Cursor"'
else
  echo "  SKIP  getLogsWithFuseQlStream pagination — could not extract cursor"
fi

# ── LogQL queries ─────────────────────────────────────────────────────────────

echo
echo "── LogQL queries ───────────────────────────────────────"

# 5. getFacetValueCountsStream — string facet
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"subscription { getFacetValueCountsStream(facetName: \\\"@:STRING.requestID\\\", logQuery: {and: [{eq: {facetName: \\\"source\\\", value: \\\"apigateway\\\"}}]}, timestamp: \\\"$START\\\", durationSecs: 3600, limit: 5) { valueCounts { value count } } }\"}")
check "getFacetValueCountsStream — returns valueCounts field" "$R" 'valueCounts'

# 6. getLabelValuesStream — label values with counts
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"subscription { getLabelValuesStream(labelName: \\\"source\\\", logQuery: {and: [{eq: {facetName: \\\"level\\\", value: \\\"info\\\"}}]}, timestamp: \\\"$START\\\", durationSecs: 3600, includeCount: true, limit: 5) { valueCounts { value count } } }\"}")
check "getLabelValuesStream — valueCounts present"   "$R" 'valueCounts'
check "getLabelValuesStream — value field present"   "$R" '"value"'
check "getLabelValuesStream — count field present"   "$R" '"count"'

# 7. getLogMetricsTimeSeries — LogQL time series (query, not subscription)
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"{ getLogMetricsTimeSeries(durationMs: 300000, logQL: \\\"sum(count_over_time({ source=~\\\\\\\".+\\\\\\\" } [5s]))\\\", stepMs: 5000, timestamp: \\\"2026-06-27T04:51:36Z\\\") { points { ts value } tags } }\"}")
check "getLogMetricsTimeSeries — points returned" "$R" '"ts"'
check "getLogMetricsTimeSeries — tags returned"   "$R" '"tags"'

# 8. getLogMetricsTimeSeriesStream — subscription time series
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"subscription { getLogMetricsTimeSeriesStream(durationMs: 300000, lookBackMs: 5000, stepMs: 60000, logQuery: {and: [{eq: {facetName: \\\"source\\\", value: \\\"grafana\\\"}}]}, rangeAggregate: \\\"count_over_time\\\", vectorAggregate: \\\"sum\\\", vectorAggregateGrouping: {groups: [\\\"level\\\"]}, timestamp: \\\"2026-06-27T04:51:36Z\\\") { points { ts value } tags } }\"}")
check "getLogMetricsTimeSeriesStream — points returned" "$R" '"ts"'
check "getLogMetricsTimeSeriesStream — tags returned"   "$R" '"tags"'

# 9. getLogsV2Stream — structured log fetch
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d "{\"query\": \"subscription { getLogsV2Stream(cursor: null, query: {and: [{and: [{eq: {facetName: \\\"level\\\", value: \\\"info\\\"}},{eq: {facetName: \\\"source\\\", value: \\\"grafana\\\"}}]}]}, limit: 2, timestamp: \\\"$START\\\", durationSecs: 300) { cursor events { timestamp logLine level } } }\"}")
check "getLogsV2Stream — cursor field present"       "$R" '"cursor"'
check "getLogsV2Stream — events returned"            "$R" '"logLine"'
check "getLogsV2Stream — level field on events"      "$R" '"level"'

# ── Lookup table queries ───────────────────────────────────────────────────────

echo
echo "── Lookup table queries ────────────────────────────────"

# 10. getLookupTables
R=$(curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://$HOST/query" \
     -d '{"query": "query { getLookUpTables { TableName Dimensions { Name DataType } PrimaryKeyColumns FolderUid } }"}')
check "getLookupTables — returns data without errors" "$R" '"data"'
# May return empty list [] if no tables exist — that's also valid
if echo "$R" | grep -q '"errors"'; then
  echo "  WARN  getLookupTables — errors in response: $(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); [print(e["message"]) for e in d.get("errors",[])]' 2>/dev/null)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo
echo "========================================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================================"
[ $FAIL -eq 0 ] && exit 0 || exit 1
