#!/bin/bash

set -x

CONTROLLER=localhost:9000
TABLE=""
DAYS_OLD=15
DRY_RUN=false
SEGMENT_FILE=""
USE_METADATA=false

while :; do
  case "$1" in
    -t|--table)     TABLE="$2"; shift 2 ;;
    -d|--days)      DAYS_OLD="$2"; shift 2 ;;
    -f|--file)      SEGMENT_FILE="$2"; shift 2 ;;
    --dry-run)      DRY_RUN=true; shift ;;
    --use-metadata) USE_METADATA=true; shift ;;
    -h|--help)
      echo "Usage: $0 -t <table_name> [-d <days_old>] [--dry-run] [--use-metadata] [-f <segment_file>]"
      echo ""
      echo "  -t, --table      Table name (required)"
      echo "  -d, --days       Segments older than N days (default: 15)"
      echo "  --dry-run        Only list old segments to file, skip deletion"
      echo "  --use-metadata   Fetch each segment's end time via the metadata API"
      echo "                   instead of parsing the timestamp from the segment name"
      echo "  -f, --file       Skip fetching; read segment names from this file and delete"
      exit 0 ;;
    "") break ;;
    -*) echo "Unknown option: $1"; exit 1 ;;
    *)  echo "Unexpected argument: $1"; exit 1 ;;
  esac
done

if [ -z "$TABLE" ]; then
  echo "Error: Table name is required. Use -t or --table."
  exit 1
fi

OLD_SEGMENTS_FILE="${TABLE}.old_segments.txt"

# Delete every segment listed (one per line) in the given file.
# There is a pinot bulk API that can delete multiple segments in one request,
# but it's not tested yet, so we use the per-segment delete for now. ref -
# https://github.com/apache/pinot/blob/master/pinot-controller/src/main/java/org/apache/pinot/controller/api/resources/PinotSegmentRestletResource.java#L622
delete_segments() {
  local list_file="$1"
  for seg in $(cat "$list_file"); do
    echo "Deleting: $seg"
    body=$(curl -s -w $'\n%{http_code}' -X DELETE "http://${CONTROLLER}/segments/${TABLE}_REALTIME/${seg}")
    curl_rc=$?
    code="${body##*$'\n'}"    # last line: HTTP status code
    body="${body%$'\n'*}"     # everything before it: response body
    echo "Response: $body (HTTP $code)"

    # Stop immediately if curl itself failed or the controller returned non-2xx.
    if [ "$curl_rc" -ne 0 ]; then
      echo "Error: curl failed (exit $curl_rc) while deleting $seg. Stopping."
      exit 1
    fi
    if [ -z "$code" ] || [ "$code" -lt 200 ] 2>/dev/null || [ "$code" -ge 300 ] 2>/dev/null; then
      echo "Error: delete of $seg returned HTTP $code. Stopping."
      exit 1
    fi
    echo "Successfully deleted: $seg"
    echo ""
  done
}

# --- MODE: File provided — skip fetching, go straight to deletion ---
if [ -n "$SEGMENT_FILE" ]; then
  if [ ! -f "$SEGMENT_FILE" ]; then
    echo "Error: File not found: $SEGMENT_FILE"
    exit 1
  fi

  echo "Reading segments from file: $SEGMENT_FILE"
  echo "Total segments to delete: $(wc -l < "$SEGMENT_FILE")"
  cat "$SEGMENT_FILE"

  echo -n "Press enter to proceed with deletion or ^C to cancel: "
  read ans

  delete_segments "$SEGMENT_FILE"

  echo "Done."
  exit 0
fi

# Convert a compact UTC timestamp (YYYYMMDDTHHMMZ) to epoch seconds.
# Works with both GNU date (Linux) and BSD date (macOS).
ts_to_epoch() {
  local ts="${1%Z}"                 # 20260630T0511
  local d="${ts%T*}" t="${ts#*T}"   # 20260630 / 0511
  local iso="${d:0:4}-${d:4:2}-${d:6:2} ${t:0:2}:${t:2:2}:00"
  date -u -d "$iso" +%s 2>/dev/null \
    || date -u -j -f "%Y-%m-%d %H:%M:%S" "$iso" +%s 2>/dev/null
}

# --- MODE: Fetch segments and filter by age ---
CUTOFF=$(( $(date +%s) - DAYS_OLD * 86400 ))
CUTOFF_MS=$(( CUTOFF * 1000 ))

echo "Fetching segments for ${TABLE}_REALTIME..."
curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME" > "${TABLE}.segments.json"

jq -r '.[0].REALTIME[]' "${TABLE}.segments.json" > "${TABLE}.all_segments.txt"
echo "Total segments: $(wc -l < "${TABLE}.all_segments.txt")"

> "$OLD_SEGMENTS_FILE"

if [ "$USE_METADATA" = true ]; then
  # Query each segment's metadata API and read its end time. Metadata is a flat
  # object with dotted keys; end time is "segment.end.time" (millis, per
  # "segment.time.unit"). Slower (one API call per segment) but authoritative.
  echo "Determining segment age via metadata API..."
  for seg in $(cat "${TABLE}.all_segments.txt"); do
    meta=$(curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME/${seg}/metadata")
    end_time=$(echo "$meta" | jq -r '.["segment.end.time"] // empty' 2>/dev/null)
    if [ -n "$end_time" ] && [ "$end_time" -lt "$CUTOFF_MS" ] 2>/dev/null; then
      echo "$seg" >> "$OLD_SEGMENTS_FILE"
    fi
  done
else
  # Segment names embed their timestamp as the last __-delimited field, e.g.
  # kf_logs__0__0__20260630T0511Z -> 20260630T0511Z. Parse it directly instead
  # of making a per-segment metadata API call.
  for seg in $(cat "${TABLE}.all_segments.txt"); do
    ts="${seg##*__}"
    seg_epoch=$(ts_to_epoch "$ts")
    if [ -n "$seg_epoch" ] && [ "$seg_epoch" -lt "$CUTOFF" ] 2>/dev/null; then
      echo "$seg" >> "$OLD_SEGMENTS_FILE"
    fi
  done
fi

echo "Segments older than ${DAYS_OLD} days: $(wc -l < "$OLD_SEGMENTS_FILE")"
cat "$OLD_SEGMENTS_FILE"

# --- DRY RUN: stop here ---
if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "Dry-run mode: no segments deleted."
  echo "Segment list saved to: $OLD_SEGMENTS_FILE"
  echo "To delete, re-run with: $0 -t $TABLE -f $OLD_SEGMENTS_FILE"
  exit 0
fi

# --- LIVE RUN: delete ---
echo -n "Press enter to proceed with deletion or ^C to cancel: "
read ans

delete_segments "$OLD_SEGMENTS_FILE"

echo "Done."