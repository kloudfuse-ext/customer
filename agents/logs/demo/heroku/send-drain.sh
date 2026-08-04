#!/usr/bin/env bash
# Heroku Log Drain — demo sender
#
# Simulates the HTTPS POST that Heroku Logplex makes to a registered drain.
# Sends a batch of realistic syslog-format log lines to the Kloudfuse ingester
# and prints a LogQL query to verify they arrived.
#
# Usage:
#   ./send-drain.sh <kloudfuse-hostname> [token]
#
# Examples:
#   ./send-drain.sh kloudfuse.example.com                       # no auth
#   ./send-drain.sh kloudfuse.example.com glsa_abc123...        # with auth token
#
# The token is passed as the kf-api-key query parameter, which is how a real
# Heroku drain URL carries the credential.

set -euo pipefail

HOST="${1:?Usage: $0 <kloudfuse-hostname> [token]}"
TOKEN="${2:-}"

URL="https://$HOST/ingester/heroku/logs"
if [[ -n "$TOKEN" ]]; then
  URL="${URL}?kf-api-key=${TOKEN}"
fi

APP="heroku-demo"
DRAIN_TOKEN="d.$(uuidgen | tr '[:upper:]' '[:lower:]')"
TS=$(date -u +%Y-%m-%dT%H:%M:%S.000000+00:00)
MARKER="kf-heroku-demo-$(date +%s)"

# Build syslog frames matching the real Heroku Logplex format:
#   HOSTNAME = Heroku app name
#   APP-NAME = "app" for dyno logs, "heroku" for platform/router logs
#   PROC-ID  = dyno identifier
build_frame() {
  local msg="$1"
  printf '%d %s' "${#msg}" "$msg"
}

MSG1="<190>1 $TS $APP app web.1 - $MARKER: application started on port 3000"
MSG2="<190>1 $TS $APP app web.1 - $MARKER: GET / 200 12ms"
MSG3="<190>1 $TS $APP app worker.1 - $MARKER: processing background job id=42"
MSG4="<158>1 $TS $APP heroku router - $MARKER: at=info method=GET path=/ host=$APP.herokuapp.com status=200 dyno=web.1 connect=1ms service=12ms bytes=1234"
MSG5="<187>1 $TS $APP heroku web.1 - $MARKER: State changed from starting to up"

BODY="$(build_frame "$MSG1")
$(build_frame "$MSG2")
$(build_frame "$MSG3")
$(build_frame "$MSG4")
$(build_frame "$MSG5")"

echo "Sending 5 log frames to $URL ..."
echo "  App:         $APP"
echo "  Drain token: $DRAIN_TOKEN"
echo "  Marker:      $MARKER"
echo ""

HTTP_STATUS=$(printf '%s' "$BODY" | curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$URL" \
  -H "Content-Type: application/logplex-1" \
  -H "Logplex-Drain-Token: $DRAIN_TOKEN" \
  -H "Logplex-Msg-Count: 5" \
  -H "Logplex-Frame-Id: demo-$(date +%s)" \
  --data-binary @-)

echo "HTTP status: $HTTP_STATUS"

if [[ "$HTTP_STATUS" != "200" && "$HTTP_STATUS" != "204" ]]; then
  echo "ERROR: ingester rejected the payload."
  exit 1
fi

echo ""
echo "Waiting 10 s for ingestion ..."
sleep 10

echo "Querying Kloudfuse for marker: $MARKER"

AUTH_HEADER=""
if [[ -n "$TOKEN" ]]; then
  AUTH_HEADER="-H 'Authorization: Bearer $TOKEN'"
fi

RESULT=$(curl -s "https://$HOST/loki/api/v1/query_range" \
  ${TOKEN:+-H "Authorization: Bearer $TOKEN"} \
  --data-urlencode "query={source=\"heroku\"} |= \"$MARKER\"" \
  --data-urlencode 'limit=10' \
  --data-urlencode "start=$(date -v-5M +%s 2>/dev/null || date -d '5 minutes ago' +%s)000000000" \
  --data-urlencode "end=$(date +%s)000000000")

COUNT=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
results = d.get('data', {}).get('result', [])
total = sum(len(r['values']) for r in results)
print(total)
" 2>/dev/null || echo "0")

if [[ "$COUNT" -gt 0 ]]; then
  echo "PASS: $COUNT log line(s) found in Kloudfuse."
  echo ""
  echo "Labels on ingested logs:"
  echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
seen = set()
for r in d.get('data', {}).get('result', []):
    key = json.dumps(r['stream'])
    if key not in seen:
        seen.add(key)
        print(json.dumps(r['stream'], indent=2))
"
else
  echo "WARN: logs not yet visible. Try querying manually:"
  echo "  {source=\"heroku\"} |= \"$MARKER\""
fi
