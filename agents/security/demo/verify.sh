#!/usr/bin/env bash
# Verify sensitive-data masking end-to-end against Kloudfuse.
#
# Queries the Loki-compatible API for logs from the security-demo pod and asserts:
#   * every redaction placeholder is present, and
#   * no raw sensitive value (test PAN, CVV, credential, email) survived.
#
# Prerequisites: the security-demo pod (../sensitive-emitter) and one masking agent
# (../dd-agent or ../otel) are deployed and have been running for a minute or two.
#
# Usage:
#   export KLOUDFUSE_HOST=<kloudfuse-hostname>
#   export KLOUDFUSE_TOKEN=<kloudfuse-token>
#   ./verify.sh                      # dd-agent: selector {source="security-demo"}
#   ./verify.sh '{service_name="security-demo"}'   # otel: override the selector
#
# NOTE: -k skips TLS verification, for clusters with a self-signed or expired
#       certificate. Drop it on a cluster with a valid certificate.
set -euo pipefail

HOST="${KLOUDFUSE_HOST:?set KLOUDFUSE_HOST}"
TOKEN="${KLOUDFUSE_TOKEN:?set KLOUDFUSE_TOKEN}"
SELECTOR="${1:-{source=\"security-demo\"}}"
MINUTES="${MINUTES:-15}"

END="$(date +%s)000000000"
START="$(( $(date +%s) - MINUTES*60 ))000000000"

echo "Host     : $HOST"
echo "Selector : $SELECTOR"
echo "Window   : last ${MINUTES}m"
echo

BODY="$(curl -sk -G "https://${HOST}/loki/api/v1/query_range" \
  -H "Authorization: Bearer ${TOKEN}" \
  --data-urlencode "query=${SELECTOR}" \
  --data-urlencode "start=${START}" \
  --data-urlencode "end=${END}" \
  --data-urlencode "limit=1000" \
  --data-urlencode "direction=BACKWARD")"

LINES="$(printf '%s' "$BODY" | grep -o '[0-9]\{13,19\}\|\[CARD REDACTED\]\|\[CSC REDACTED\]\|\[SECRET REDACTED\]\|\*\*\*@\*\*\*\.\*\*\*' | sort | uniq -c || true)"
echo "Interesting tokens returned:"
echo "$LINES"
echo

fail=0

# Placeholders that MUST be present (proves masking ran)
for mark in "[CARD REDACTED]" "[CSC REDACTED]" "[SECRET REDACTED]" "***@***.***"; do
  if printf '%s' "$BODY" | grep -qF "$mark"; then
    echo "PASS  placeholder present: $mark"
  else
    echo "FAIL  placeholder MISSING: $mark"; fail=1
  fi
done

echo

# Raw values that must NOT appear (proves nothing leaked)
for raw in "4111111111111111" "5555 5555 5555 4444" "3782 822463 10005" \
           "6011-0009-9013-9424" "hunter2-s3cret" "jane.doe+test@example.com" \
           "eyJhbGciOiJIUzI1NiJ9"; do
  if printf '%s' "$BODY" | grep -qF "$raw"; then
    echo "FAIL  raw value LEAKED: $raw"; fail=1
  else
    echo "PASS  raw value absent: $raw"
  fi
done

echo

# Decoys that MUST survive unchanged
for keep in "the password was reset by an administrator" "ORD-77"; do
  if printf '%s' "$BODY" | grep -qF "$keep"; then
    echo "PASS  decoy preserved: $keep"
  else
    echo "WARN  decoy not found (may be outside window): $keep"
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS — masking verified, no raw sensitive values reached Kloudfuse."
else
  echo "RESULT: FAIL — see failures above."; exit 1
fi
