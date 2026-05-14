"""The Memo Helper Prompt — given to the user to paste into ChatGPT/Claude/Gemini.

The output of this prompt, fed back to ``linkright evidence add``, gives the
strongest possible RAG retrieval quality because every chunk is one topic by
construction (one ``## Atom:`` section per topic).

This prompt is also used internally by ``linkright evidence add --from-raw``
(via groq_chat) to auto-format raw text → memo.
"""

MEMO_HELPER_PROMPT = """\
You are converting raw professional thoughts into LinkRight Evidence Memo format.
The output is a Markdown file with strict structure that LinkRight will chunk + embed.

INPUT: I will paste raw text — diary entry, work reflection, project notes, or
brain-dump. May be unstructured.

OUTPUT: Reformatted Markdown with:

1. Frontmatter block (---) with: source_type, date, author_role, default_tags
2. One or more "## Atom: <one-line-topic-title>" sections

CRITICAL RULES:
- Each Atom MUST be ONE topic only. If raw text covers 3 topics, output 3 Atoms.
- Each Atom: 200-500 words of natural narrative prose (NOT bullets).
- Each Atom must include: date, role, company (if known), tags (3-6),
  metric_keys (which numerical outcomes matter).
- Preserve specific names, numbers, dates, outcomes, decisions —
  these are retrieval anchors. Never abstract them away.
- Use first-person "I" not "we" wherever the user owned the action.
- If a topic is partially described, prefix it with `[partial]` in the title
  so LinkRight knows to ask the user for completion later.

NEVER:
- Invent details not in the source
- Combine multiple topics into one Atom
- Use bullet points (kills embedding signal)
- Drop specific numbers or names

OUTPUT FORMAT EXAMPLE:

---
source_type: diary
date: 2026-05-15
author_role: "AmEx Senior PM"
default_tags: [pm, amex, 2024]
---

## Atom: Walmart partnership negotiation
date: 2024-03-12
role: "AmEx Senior PM"
company: AmEx
project: "Card-on-File Initiative"
tags: [stakeholder, partnership, negotiation, walmart]
metric_keys: [headcount, weeks_to_close, arr_impact]

In Q1 2024 I personally led the partnership conversation with Walmart's
VP of Payments to swap 3 of their senior payment engineers into my pod
for the card-on-file initiative. The original plan had me wait 8 weeks
for AmEx internal hiring; instead I closed the swap in 2 weeks by
offering reciprocal access to our merchant analytics dashboards. The
3-engineer swap unblocked the integration sprint and the feature shipped
6 weeks early, contributing $4M ARR in the first quarter post-launch.

## Atom: Decision to deprioritize the SMB tier
date: 2024-05-08
role: "AmEx Senior PM"
company: AmEx
tags: [prioritization, tradeoff, sequencing]
metric_keys: [arr_at_risk, dev_cycles_saved]

Mid-2024 I made the call to deprioritize the SMB merchant tier from
our Q3 roadmap despite a $1.2M ARR pipeline depending on it. The
calculus: SMB integration would consume 7 dev cycles for a tier whose
LTV was 1/4th our enterprise tier. I sold this to my VP using a
3-quarter ARR-per-dev-cycle model. Decision held — Q4 enterprise wins
delivered $11M ARR, validating the sequencing.

INPUT:
<<<paste raw text below this line>>>
"""


USAGE_HINT = """\

How to use this prompt:

1. Copy the prompt above (everything between the lines).
2. Open ChatGPT / Claude / Gemini / any free chat tool.
3. Paste the prompt, then paste your raw text below the marker.
4. Copy the LLM's output, save as a .md file (e.g. memo_2026-05-15.md).
5. Run: linkright evidence add memo_2026-05-15.md

Power-user shortcut (uses your Groq key — auto-formats):
  linkright evidence add --from-raw raw-thoughts.txt
"""
