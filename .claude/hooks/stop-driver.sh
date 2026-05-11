#!/usr/bin/env bash
# Stop hook — fires when Claude tries to end its turn.
# Purpose: keep the autonomous PO-QA loop driving until SHIP or ESCALATE.
#
# Reads the JSON event on stdin. If a "task in flight" marker file exists,
# blocks the stop and instructs Claude to resume the loop.
#
# Marker file: .claude/state/po-task.json
#   {"task": "<title>", "status": "OPEN" | "SHIPPED" | "ESCALATED",
#    "started_at": "<iso>", "last_check": "<iso>"}
#
# The product-owner-qa agent is responsible for writing/updating this marker.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE="$REPO_ROOT/.claude/state/po-task.json"

# No marker → no autonomous task in flight → allow stop.
if [[ ! -f "$STATE" ]]; then
  exit 0
fi

STATUS="$(jq -r '.status // "OPEN"' "$STATE" 2>/dev/null || echo "OPEN")"
TASK="$(jq -r '.task // "unknown"' "$STATE" 2>/dev/null || echo "unknown")"

if [[ "$STATUS" == "SHIPPED" || "$STATUS" == "ESCALATED" ]]; then
  # Loop is closed — allow stop.
  exit 0
fi

# Update last_check timestamp.
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
tmp="$(mktemp)"
jq --arg now "$NOW" '.last_check = $now' "$STATE" > "$tmp" && mv "$tmp" "$STATE"

# Block the stop and tell Claude to continue driving.
cat <<EOF
{
  "decision": "block",
  "reason": "Autonomous PO-QA loop is OPEN for task: ${TASK}. Status is ${STATUS}. Resume the loop — dispatch the next agent or run QA. Do not stop until status is SHIPPED or ESCALATED. If you are blocked, write the blocker into .claude/state/po-task.json with status=ESCALATED and a specific question for the human."
}
EOF
