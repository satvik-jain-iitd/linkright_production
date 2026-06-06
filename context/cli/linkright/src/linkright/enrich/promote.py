"""Promote accepted proposals → confirmed Facts → re-derive Signals.

Steps:
  1. Mint stable fact_ids
  2. Append accepted proposals to facts.jsonl with user_confirmed=True
  3. Re-embed facts (delta append, not full rebuild — performance)
  4. Re-derive signals: for any signal whose source_fact_ids overlap the
     new facts, increment recurrence_count + re-embed if changed
  5. Snapshot CareerProfile to profile_history/v00N.json
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from linkright.profile.signal_vocabulary import normalize_signal_name
from linkright.profile.v2_schemas import (
    CareerProfile,
    Fact,
    Signal,
    SignalConfidence,
)
from linkright.profile.v2_store import (
    append_facts,
    load_canonical_profile,
    load_facts,
    load_signals,
    next_fact_id,
    rebuild_facts_embeddings,
    rebuild_signals_embeddings,
    refresh_markdown_export,
    save_canonical_profile,
    write_signals,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def promote_accepted_proposals(
    accepted: list[dict[str, Any]],
    *,
    embed_fn,
) -> dict[str, int]:
    """Convert accepted proposals to confirmed Facts; update signals + history.

    Returns counts: {"facts_added": int, "signals_updated": int}.
    """
    if not accepted:
        return {"facts_added": 0, "signals_updated": 0}

    # 1. Mint Fact objects + persist
    new_facts: list[Fact] = []
    for prop in accepted:
        fact_id = next_fact_id()
        new_fact = Fact(
            id=fact_id,
            text=prop.get("text", ""),
            evidence_atom_ids=list(prop.get("evidence_atom_ids") or []),
            role_id=prop.get("role_id"),
            confidence=float(prop.get("confidence", 0.7)),
            user_confirmed=True,
            confirmation_at=_now_iso(),
            metric_extracted=dict(prop.get("metric_extracted") or {}),
        )
        new_facts.append(new_fact)
        # Persist incrementally so next_fact_id stays monotonic
        append_facts([new_fact])

    # 2. Mirror new fact ids onto CareerProfile.role.fact_ids
    profile = load_canonical_profile()
    profile_changed = False
    if profile:
        role_index = {r.id: r for r in profile.roles}
        for f in new_facts:
            if f.role_id and f.role_id in role_index:
                role = role_index[f.role_id]
                if f.id not in role.fact_ids:
                    role.fact_ids.append(f.id)
                    profile_changed = True

    # 3. Re-embed facts (full rebuild — small enough at personal scale)
    rebuild_facts_embeddings(None, embed_fn)

    # 4. Re-derive signals: for every existing signal, if any new fact has
    #    a role_id matching a fact already supporting that signal, bump
    #    recurrence_count. (A more sophisticated re-cluster is Phase 4 work.)
    signals = load_signals()
    signals_updated = 0
    if signals and new_facts:
        # Build role_id → set of existing signal_ids that draw from this role
        role_to_signals: dict[str, set[str]] = {}
        existing_facts = {f.id: f for f in load_facts()}
        for sig in signals:
            for fid in sig.source_fact_ids:
                fact = existing_facts.get(fid)
                if fact and fact.role_id:
                    role_to_signals.setdefault(fact.role_id, set()).add(sig.id)

        signal_index = {s.id: s for s in signals}
        for new_fact in new_facts:
            if not new_fact.role_id:
                continue
            for sig_id in role_to_signals.get(new_fact.role_id, set()):
                sig = signal_index[sig_id]
                if new_fact.id not in sig.source_fact_ids:
                    sig.source_fact_ids.append(new_fact.id)
                    sig.recurrence_count = len(sig.source_fact_ids)
                    signals_updated += 1

        if signals_updated:
            write_signals(signals)
            rebuild_signals_embeddings(None, embed_fn)

    # 5. Snapshot profile if anything changed
    if profile and (profile_changed or new_facts):
        profile.identity_version += 1 if profile_changed else 0
        save_canonical_profile(profile, snapshot=True)

    # 6. Keep the skills' derived markdown memory in lockstep with this write.
    if new_facts or signals_updated or profile_changed:
        refresh_markdown_export()

    return {
        "facts_added": len(new_facts),
        "signals_updated": signals_updated,
    }
