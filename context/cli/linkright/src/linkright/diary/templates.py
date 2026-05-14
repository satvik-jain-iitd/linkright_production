"""Diary memo template — pre-filled frontmatter for $EDITOR mode.

Keeps the cognitive load on the user near zero: open editor, write narrative
under each ``## Atom:`` header, save. Format validation runs on save and
shows specific errors before persisting.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Optional


_TEMPLATE = """\
---
source_type: diary
date: {date_iso}
author_role: {author_role}
default_tags: [{default_tags}]
---

## Atom: {first_topic_placeholder}
date: {date_iso}
role: {author_role}
company: {company_placeholder}
tags: [{atom_tags}]
metric_keys: []

# Write your narrative here. 200-500 words on ONE topic.
# Use first-person "I". Include specific names, numbers, decisions.
# Bullets kill embedding signal — write in full sentences.

## Atom: [add another topic if you covered multiple things today]
date: {date_iso}
role: {author_role}
tags: []

# Each Atom = one topic. If today covered 3 distinct topics, write 3 Atoms.
# Delete this scaffold atom if you only have one topic to capture.
"""


def build_diary_template(
    *,
    today: Optional[_date] = None,
    author_role: str = "",
    default_tags: Optional[list[str]] = None,
) -> str:
    """Build a fresh diary memo template with today's date pre-filled.

    Args:
        today: defaults to today (UTC date).
        author_role: pre-fills author_role + per-atom role. Empty if unknown.
        default_tags: tags applied to every atom in the doc.
    """
    today = today or _date.today()
    tags = default_tags or []
    return _TEMPLATE.format(
        date_iso=today.strftime("%Y-%m-%d"),
        author_role=f'"{author_role}"' if author_role else '""',
        default_tags=", ".join(tags),
        first_topic_placeholder="[topic title — replace this]",
        company_placeholder='""',
        atom_tags="",
    )
