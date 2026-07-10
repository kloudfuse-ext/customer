#!/bin/bash

set -x

CONTROLLER=localhost:9000
TABLE=""
DAYS_OLD=15
DRY_RUN=false
SEGMENT_FILE=""

while :; do
  case "$1" in
    -t|--table)    TABLE="$2"; shift 2 ;;
    -d|--days)     DAYS_OLD="$2"; shift 2 ;;
    -f|--file)     SEGMENT_FILE="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    -h|--help)
      echo "Usage: $0 -t <table_name> [-d <days_old>] [--dry-run] [-f <segment_file>]"
      echo ""
      echo "  -t, --table   Table name (required)"
      echo "  -d, --days    Segments older than N days (default: 15)"
      echo "  --dry-run     Only list old segments to file, skip deletion"
      echo "  -f, --file    Skip fetching; read segment names from this file and delete"
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

  for seg in $(cat "$SEGMENT_FILE"); do
    echo "Deleting: $seg"
    curl -s -X DELETE "http://${CONTROLLER}/segments/${TABLE}_REALTIME/${seg}"
    echo ""
  done

  echo "Done."
  exit 0
fi

# --- MODE: Fetch segments and filter by age ---
CUTOFF_MS=$(( ($(date +%s) - DAYS_OLD * 86400) * 1000 ))

echo "Fetching segments for ${TABLE}_REALTIME..."
curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME" > "${TABLE}.segments.json"

jq -r '.[0].REALTIME[]' "${TABLE}.segments.json" > "${TABLE}.all_segments.txt"
echo "Total segments: $(wc -l < "${TABLE}.all_segments.txt")"

> "$OLD_SEGMENTS_FILE"

for seg in $(cat "${TABLE}.all_segments.txt"); do
  meta=$(curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME/${seg}/metadata")
  end_time=$(echo "$meta" | jq -r '.segmentMetadata.endTimeMs // .segmentMetadata.segment.end.time // empty' 2>/dev/null)

  if [ -n "$end_time" ] && [ "$end_time" -lt "$CUTOFF_MS" ] 2>/dev/null; then
    echo "$seg" >> "$OLD_SEGMENTS_FILE"
  fi
done

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

for seg in $(cat "$OLD_SEGMENTS_FILE"); do
  echo "Deleting: $seg"
  curl -s -X DELETE "http://${CONTROLLER}/segments/${TABLE}_REALTIME/${seg}"
  echo ""
done

echo "Done."