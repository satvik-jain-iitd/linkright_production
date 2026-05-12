#!/bin/bash
# Block Claude from stopping while a PO-QA task is open.
# Exit 2 = block stop. Exit 0 = allow stop.
STATE_FILE="$(dirname "$0")/../state/po-task.json"
if [[ -f "$STATE_FILE" ]]; then
  status=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('status',''))" 2>/dev/null)
  if [[ "$status" == "OPEN" ]]; then
    echo "PO-QA task is OPEN — complete or escalate before stopping." >&2
    exit 2
  fi
fi
exit 0
