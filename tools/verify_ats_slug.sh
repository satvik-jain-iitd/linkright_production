#!/bin/bash
# Verify which ATS a company uses by testing public API slugs.
# Usage: ./tools/verify_ats_slug.sh <slug>
# Example: ./tools/verify_ats_slug.sh razorpay

SLUG=${1:-razorpay}
echo "=== Testing ATS slug: $SLUG ==="

echo -n "Greenhouse: "
RESULT=$(curl -sf --max-time 8 "https://boards-api.greenhouse.io/v1/boards/$SLUG/jobs" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('jobs',[])),'jobs')" 2>/dev/null)
[ -n "$RESULT" ] && echo "✅ $RESULT" || echo "❌"

echo -n "Lever:      "
RESULT=$(curl -sf --max-time 8 "https://api.lever.co/v0/postings/$SLUG?mode=json" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)),'jobs')" 2>/dev/null)
[ -n "$RESULT" ] && echo "✅ $RESULT" || echo "❌"

echo -n "Ashby:      "
RESULT=$(curl -sf --max-time 8 "https://api.ashbyhq.com/posting-api/job-board/$SLUG" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('jobs',[])),'jobs')" 2>/dev/null)
[ -n "$RESULT" ] && echo "✅ $RESULT" || echo "❌"

echo -n "Workable:   "
RESULT=$(curl -sf --max-time 8 "https://apply.workable.com/api/v1/widget/accounts/$SLUG" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('results',[])),'jobs')" 2>/dev/null)
[ -n "$RESULT" ] && echo "✅ $RESULT" || echo "❌"

echo -n "Recruitee:  "
RESULT=$(curl -sf --max-time 8 "https://$SLUG.recruitee.com/api/offers" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('offers',[])),'jobs')" 2>/dev/null)
[ -n "$RESULT" ] && echo "✅ $RESULT" || echo "❌"

echo ""
echo "Run for a batch:"
echo "  for s in razorpay cred groww meesho phonepe zomato flipkart; do ./tools/verify_ats_slug.sh \$s; done"
