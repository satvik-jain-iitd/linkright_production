# Conflict Handling Guide
# What to do when Oracle returns conflict=true on ingestAtom.
# Update this file to change how conflicts are presented to users.

---

## WHAT A CONFLICT MEANS
When `ingestAtom` returns `{ "ok": false, "conflict": true, "similarity": 0.93 }`,
it means the user's knowledge graph already contains an achievement with >85% cosine
similarity to the one being ingested. The system detected a near-duplicate.

This happens when:
- The user is describing the same achievement from a different angle
- They're updating an existing highlight with new details
- Two genuinely separate achievements happen to sound similar

---

## HOW TO PRESENT A CONFLICT

### Template response:
"This sounds very similar to something already in your profile. The system flagged it as a possible duplicate. What would you like to do?

A) Save this as a separate, new entry
B) Skip it — the existing entry already covers this
C) Describe it differently so I can save a distinct version"

### Simplified version (for casual users):
"I think you may have shared something similar before. Is this the same achievement you mentioned earlier, or a different one?"

---

## DECISION TREE

```
User says "same achievement" or "B" or "skip"
  → Do NOT ingest. Say "Got it — skipping this one."
  → Continue to next topic.

User says "different achievement" or "A" or "new entry"
  → Ask: "What makes this one distinct from the earlier one? 
     For example, different outcome, different company, or different scale?"
  → Capture the differentiating detail (e.g., different timeframe, company, metric)
  → Retry ingestAtom — the clarifying detail changes the embedding enough to avoid conflict
  → If conflict persists after retry → tell user: 
     "The system still sees these as very similar. I'll note this topic for your dashboard — you can review and merge them there."

User says "update" or "C"
  → Explain: "To update an existing entry, you can do that from your LinkRight dashboard.
     For now, I'll save the new version alongside the original."
  → Re-ingest with differentiating detail added
```

---

## SIMILARITY SCORE GUIDANCE
The `similarity` field in the conflict response indicates how close the match is:

| Similarity | What it means | Recommended action |
|---|---|---|
| 0.95+ | Almost certainly the same achievement | Ask user to confirm; likely skip |
| 0.87–0.94 | Same theme, possibly different angle | Ask the differentiating question |
| 0.85–0.86 | Threshold hit, may be distinct | Clarify first before deciding |

---

## EDGE CASES

**Multiple conflicts:** Oracle only returns the single closest match. If the user has many similar atoms, the closest one is shown. Tell the user: "Your profile has a few similar entries — this one is the closest match."

**Conflict on first session (0 existing atoms shown but conflict returned):** This shouldn't happen, but if it does: "There seems to be a data inconsistency. Let me save this as a new entry." Then re-ingest.

**API error on ingest:** Not a conflict, just a failure. Retry once with same data. If it fails again: "I'm having trouble saving that one right now — I'll note it and you can add it manually from your dashboard later."
