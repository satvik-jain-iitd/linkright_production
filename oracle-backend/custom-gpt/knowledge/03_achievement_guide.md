# Achievement Extraction Guide
# How to turn a user's story into a well-formed career atom.
# Update this file to change the extraction methodology.

---

## THE STAR-M FRAMEWORK
Every atom must capture:
- **S** — Situation/Context: background, stakes, what was going on
- **T** — Task/Challenge: what needed to be solved or built
- **A** — Action: what the user PERSONALLY did (not "we")
- **R** — Result: measurable outcome
- **M** — Metrics: structured numbers (separate from result_text for indexing)

---

## MAPPING CONVERSATION → ATOM FIELDS

| What user says | → Atom field |
|---|---|
| "I built X" | action_verb="Built", action_detail="X..." |
| "We reduced costs by 30%" | result_text, metrics[{value:30, unit:"%", direction:decreased}] |
| "I was the tech lead" | team_role="lead" |
| "It was just me" | team_role="solo" |
| "I used Python and AWS" | tools_used=["Python","AWS"], skills_demonstrated=[...] |
| "It took 3 months" | timeframe (estimate Q if no exact date) |
| "It was really hard because..." | challenge, difficulty="hard" |
| "The business impact was..." | stakes or result_text |
| "My key decision was..." | your_decision |

---

## CHOOSING THE RIGHT ACTION VERB
The action_verb is the most visible part of a resume bullet. Choose carefully.

| Category | Verbs |
|---|---|
| **Built / Created** | Built, Designed, Architected, Developed, Created, Launched, Shipped |
| **Improved** | Reduced, Improved, Optimized, Accelerated, Streamlined, Simplified |
| **Led / Managed** | Led, Managed, Directed, Coordinated, Oversaw, Mentored, Coached |
| **Grew** | Scaled, Grew, Expanded, Increased, Doubled, Tripled |
| **Delivered** | Delivered, Completed, Executed, Implemented, Deployed |
| **Analyzed** | Analyzed, Identified, Diagnosed, Audited, Evaluated, Modeled |
| **Negotiated** | Negotiated, Secured, Closed, Won, Influenced, Persuaded |
| **Saved** | Saved, Cut, Eliminated, Automated, Replaced |

---

## MINIMUM VIABLE ATOM
If the user is running out of time or detail, this is the minimum to save an atom:

```json
{
  "action_verb": "Built",
  "action_detail": "real-time inventory tracking dashboard for warehouse ops",
  "company": "Flipkart",
  "role": "Product Manager",
  "result_text": "Reduced stockouts by 25% in first quarter after launch"
}
```

This is a valid atom. Fill in other fields if available, but don't block ingestion waiting for perfect data.

---

## ENRICHMENT PRIORITY ORDER
When you have extra time or the user is forthcoming:
1. **metrics** — structured numbers always improve resume relevance
2. **skills_demonstrated** — critical for JD matching
3. **tools_used** — keyword matching for ATS systems
4. **you_specifically** — separates individual from team credit
5. **context / stakes** — makes the achievement resonate
6. **timeframe** — allows chronological resume ordering
7. **behavioral_tags** — powers behavioral interview prep

---

## WHAT NOT TO SAVE
- "I attended team meetings and contributed ideas" — too vague, not an achievement
- "I was responsible for the marketing strategy" — responsibility, not result
- "I worked on improving customer satisfaction" — no action, no metric
- Anything the user hasn't confirmed as an achievement (they said "sort of" or "kind of")

Ask yourself: Could this be a bullet point on a resume that would impress a hiring manager?
If no → probe for specifics or skip.

---

## HANDLING MULTIPLE ACHIEVEMENTS FROM ONE STORY
Users often bundle two achievements in one story:
"I built the data pipeline AND redesigned the reporting dashboard, which saved 10 hours/week"

→ Split into two atoms if each has a distinct action. Ask: "That sounds like two separate achievements — the pipeline and the dashboard. Should I capture them separately?"

If user says yes → ingest two atoms.
If user says no → pick the stronger one and save it.
