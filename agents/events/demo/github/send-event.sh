#!/usr/bin/env bash
# send-event.sh — Send a synthetic GitHub webhook event to Kloudfuse
#
# Simulates a GitHub push event payload and POSTs it to the Kloudfuse ingestion
# endpoint, validating that the GitHub → Kloudfuse webhook pipeline is working.
#
# Usage:
#   export KFUSE_HOST="kloudfuse.example.com"
#   export KFUSE_API_KEY="<your-api-key>"   # omit if auth is not enabled
#   bash send-event.sh
#
# After running, query Kloudfuse to confirm ingestion:
#   source="github" x_github_event="push"

set -euo pipefail

KFUSE_HOST="${KFUSE_HOST:?Set KFUSE_HOST to the external hostname of your Kloudfuse cluster}"
KFUSE_API_KEY="${KFUSE_API_KEY:-}"
ENDPOINT="https://${KFUSE_HOST}/ingester/github/events"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
COMMIT_SHA="$(openssl rand -hex 20 2>/dev/null || od -An -N20 -tx1 /dev/urandom | tr -d ' \n')"

PAYLOAD=$(cat <<EOF
{
  "ref": "refs/heads/main",
  "before": "0000000000000000000000000000000000000000",
  "after": "${COMMIT_SHA}",
  "repository": {
    "id": 123456789,
    "name": "demo-repo",
    "full_name": "demo-org/demo-repo",
    "private": false,
    "html_url": "https://github.com/demo-org/demo-repo",
    "description": "Kloudfuse GitHub events demo repository"
  },
  "pusher": {
    "name": "demo-user",
    "email": "demo-user@example.com"
  },
  "sender": {
    "login": "demo-user",
    "id": 1000001,
    "type": "User"
  },
  "commits": [
    {
      "id": "${COMMIT_SHA}",
      "message": "Demo commit for Kloudfuse events pipeline test",
      "timestamp": "${TIMESTAMP}",
      "url": "https://github.com/demo-org/demo-repo/commit/${COMMIT_SHA}",
      "author": {
        "name": "Demo User",
        "email": "demo-user@example.com",
        "username": "demo-user"
      },
      "added": ["README.md"],
      "removed": [],
      "modified": []
    }
  ],
  "head_commit": {
    "id": "${COMMIT_SHA}",
    "message": "Demo commit for Kloudfuse events pipeline test",
    "timestamp": "${TIMESTAMP}",
    "url": "https://github.com/demo-org/demo-repo/commit/${COMMIT_SHA}"
  }
}
EOF
)

# Build curl arguments
CURL_ARGS=(
  --silent
  --show-error
  --fail-with-body
  --max-time 15
  --header "Content-Type: application/json"
  --header "X-GitHub-Event: push"
  --header "X-GitHub-Delivery: $(openssl rand -hex 16 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo demo-delivery-id)"
  --data "${PAYLOAD}"
)

if [[ -n "${KFUSE_API_KEY}" ]]; then
  CURL_ARGS+=(--header "Kf-Api-Key: ${KFUSE_API_KEY}")
fi

echo "Sending push event to ${ENDPOINT}"
echo "Commit SHA: ${COMMIT_SHA}"
echo ""

HTTP_STATUS=$(curl "${CURL_ARGS[@]}" --write-out "%{http_code}" --output /tmp/kfuse-response.txt "${ENDPOINT}" || true)
RESPONSE=$(cat /tmp/kfuse-response.txt)

echo "HTTP status: ${HTTP_STATUS}"
[[ -n "${RESPONSE}" ]] && echo "Response:    ${RESPONSE}"
echo ""

if [[ "${HTTP_STATUS}" =~ ^2 ]]; then
  echo "SUCCESS — event delivered."
  echo ""
  echo "Query in Kloudfuse:"
  echo "  source=\"github\" x_github_event=\"push\""
else
  echo "ERROR — delivery failed (HTTP ${HTTP_STATUS})."
  echo ""
  echo "Troubleshooting:"
  echo "  - Confirm KFUSE_HOST resolves and port 443 is reachable."
  echo "  - If HTTP 401, set KFUSE_API_KEY to a valid ingestion API key."
  echo "  - The path must be exactly /ingester/github/events (no trailing slash)."
  exit 1
fi
