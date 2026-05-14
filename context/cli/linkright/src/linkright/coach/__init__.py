"""linkright interview coach — Layer-5 consumer of the memory-v2 architecture.

Ports the `repeat-after-me` Cloud skill into the CLI. Reads from facts +
signals + evidence atoms + coaching playbook → generates ideal interview
answers grounded in the candidate's real career data, framed by expert
coaching methodology, delivered via TTS in a realistic interview cadence.

Token cost ~$0.005 per session vs ~$0.50-1.00 on Claude Cloud — ~100x
cheaper because RAG injects only the relevant 3-5 facts + 3 playbook
chunks per question instead of loading the full candidate history +
47-doc playbook into Claude's context.

See plan: ~/.claude/plans/okay-what-i-want-elegant-cook.md (Part G)
"""
from __future__ import annotations
