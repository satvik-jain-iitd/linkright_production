"""`linkright onboard` — first-run pipeline: resume → CareerProfile.

Replaces the broken `profile create` flow. Resume-only at onboarding
prevents markdown misclassification. Roles confirmed BEFORE facts ensures
every fact carries role_id from creation (no attribution loss).

Pipeline (per plan Part B.2):
  1. Ingest resume PDF as Evidence  → reuses Phase 0 ingest_file()
  2. LLM Pass 1: extract roles      → user batch-confirms
  3. LLM Pass 2: facts per role     → user confirms top facts per role
  4. Cluster confirmed facts        → Signals (controlled vocab)
  5. Write CareerProfile + facts/   → snapshot to profile_history/v001.json
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import click

from linkright.evidence.ingest import ingest_file
from linkright.evidence.schemas import Atom, EvidenceTier
from linkright.evidence.store import EvidenceStore

from .batch_review import confirm_facts_per_role, confirm_roles_batch
from .extractors import (
    derive_signals_from_facts,
    extract_facts_for_role,
    extract_roles_from_evidence,
)
from ..profile.signal_vocabulary import normalize_signal_name
from ..profile.v2_schemas import (
    CareerProfile,
    Fact,
    Role,
    Signal,
    SignalConfidence,
)
from ..profile.v2_store import (
    append_facts,
    ensure_profile_dirs,
    next_fact_id,
    rebuild_facts_embeddings,
    rebuild_signals_embeddings,
    save_canonical_profile,
    write_metadata,
    write_signals,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@click.command("onboard")
@click.option(
    "-r", "--resume",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Resume PDF (canonical evidence — interviewer-visible boundary).",
)
@click.option(
    "--archetype",
    default="",
    help="Optional target PM archetype to bias signal derivation (e.g. ai_native_pm).",
)
@click.option(
    "--top-facts",
    type=int,
    default=8,
    show_default=True,
    help="Number of facts surfaced per role for batch confirmation.",
)
def onboard(resume: Path, archetype: str, top_facts: int) -> None:
    """First-run resume → CareerProfile pipeline.

    \b
    Resume-only at onboarding by design — markdown misclassification was the
    root cause of v1 attribution loss. Roles are confirmed BEFORE facts so
    every fact carries role_id from creation.
    """
    from linkright.ui import console as _ui_console, pip as _pip

    if _pip.is_tty_capable():
        _ui_console.print(_pip.pip_note(
            "tell me where you want to be seen.",
            pose="pointing",
            sub=f"resume: {resume.name}" + (f"  ·  archetype: {archetype}" if archetype else ""),
        ))
        _ui_console.print()
    else:
        click.echo("━━━ LinkRight Onboarding ━━━")
        click.echo(f"  Resume: {resume.name}")
        if archetype:
            click.echo(f"  Target archetype: {archetype}")
        click.echo()

    # Step 1 — Ingest resume as Evidence
    click.echo("→ Step 1: Ingesting resume as Evidence (tier=resume_canonical)...")
    try:
        ingest_result = ingest_file(resume, tier=EvidenceTier.RESUME_CANONICAL)
    except Exception as e:
        click.echo(f"✖ Resume ingest failed: {type(e).__name__}: {e}", err=True)
        sys.exit(1)

    click.echo(f"  ✓ {ingest_result.evidence.id} — {ingest_result.atom_count} atom(s)")

    # Load atoms back for extraction
    store = EvidenceStore()
    resume_atoms = store.list_atoms(ingest_result.evidence.id)

    # Step 2 — Extract + confirm roles
    click.echo()
    click.echo("→ Step 2: Extracting roles via LLM...")
    try:
        roles_raw = extract_roles_from_evidence(resume_atoms)
    except RuntimeError as e:
        click.echo(f"✖ {e}", err=True)
        sys.exit(1)
    click.echo(f"  ✓ LLM proposed {len(roles_raw)} role(s)")

    confirmed_roles = confirm_roles_batch(roles_raw)
    if not confirmed_roles:
        click.echo("✖ No roles confirmed — onboarding cannot continue.", err=True)
        sys.exit(1)

    # Step 3 — Map confirmed roles → role_id + atoms-per-role
    role_objects: list[Role] = []
    role_atom_map: dict[str, list[Atom]] = {}
    for r in confirmed_roles:
        role_id = _mint_role_id(r)
        role_objects.append(Role(
            id=role_id,
            company=r.get("company", ""),
            title=r.get("title", ""),
            start_date=r.get("start_date", ""),
            end_date=r.get("end_date", "") if r.get("end_date") != "present" else "",
            is_current=(r.get("end_date") == "present"),
            employment_type=r.get("employment_type", "full_time"),
            description=r.get("summary", ""),
        ))
        # Crude attribution: send ALL resume atoms for fact extraction. The
        # LLM in Pass 2 sees the role context + atom IDs and grounds facts.
        # A future heuristic could pre-filter atoms by company-name match.
        role_atom_map[role_id] = resume_atoms

    # Step 4 — Extract + confirm facts per role
    click.echo()
    click.echo("→ Step 4: Extracting facts per role via LLM...")
    confirmed_facts: list[Fact] = []
    for role in role_objects:
        role_dict = {
            "company": role.company, "title": role.title,
            "start_date": role.start_date, "end_date": role.end_date or "present",
        }
        try:
            facts_raw = extract_facts_for_role(
                role_dict, role_atom_map[role.id], max_facts=top_facts
            )
        except RuntimeError as e:
            click.echo(f"  ⚠ Skipping facts for {role.company}: {e}", err=True)
            continue

        chosen = confirm_facts_per_role(role_dict, facts_raw, top_n=top_facts)
        for proto in chosen:
            fact_id = next_fact_id()
            f = Fact(
                id=fact_id,
                text=proto.get("text", ""),
                evidence_atom_ids=list(proto.get("supporting_atom_ids") or []),
                role_id=role.id,
                confidence=float(proto.get("confidence", 0.0)),
                user_confirmed=True,
                confirmation_at=_now_iso(),
                metric_extracted=dict(proto.get("metric_extracted") or {}),
            )
            confirmed_facts.append(f)
            role.fact_ids.append(fact_id)
            # Persist incrementally so next_fact_id sees the latest counter
            append_facts([f])

    click.echo()
    click.echo(f"  ✓ {len(confirmed_facts)} fact(s) confirmed across {len(role_objects)} role(s)")

    # Step 5 — Derive Signals from confirmed facts
    click.echo()
    click.echo("→ Step 5: Deriving signals from confirmed facts...")
    facts_payload = [
        {"id": f.id, "text": f.text, "role_id": f.role_id} for f in confirmed_facts
    ]
    try:
        signals_raw = derive_signals_from_facts(
            facts_payload, target_archetype=archetype or None,
        )
    except RuntimeError as e:
        click.echo(f"  ⚠ Signal derivation failed: {e}", err=True)
        signals_raw = []

    signal_objects: list[Signal] = []
    for proto in signals_raw:
        canonical = normalize_signal_name(proto.get("canonical_name", ""))
        if not canonical:
            continue
        sig = Signal(
            id=f"sig_{canonical}",
            canonical_name=canonical,
            definition=proto.get("definition", ""),
            source_fact_ids=list(proto.get("supporting_fact_ids") or []),
            archetype_alignment=list(proto.get("archetype_alignment") or []),
            confidence=SignalConfidence.from_dict(proto.get("confidence") or {}),
            recurrence_count=len(proto.get("supporting_fact_ids") or []),
        )
        signal_objects.append(sig)
        # Mirror onto role.signal_ids if any sig fact belongs to that role
        for role in role_objects:
            if any(fid in role.fact_ids for fid in sig.source_fact_ids):
                role.signal_ids.append(sig.id)

    click.echo(f"  ✓ {len(signal_objects)} signal(s) derived")

    # Step 6 — Persist Signals + CareerProfile + embeddings
    write_signals(signal_objects)

    profile = CareerProfile(
        id=f"profile_{uuid.uuid4().hex[:8]}",
        roles=role_objects,
        current_archetype=archetype,
    )
    save_canonical_profile(profile, snapshot=True)
    write_metadata(
        ensure_profile_dirs(),
        schema_version=2,
        identity_version=1,
        embedder_tier="fastembed",
        onboarded_at=_now_iso(),
    )

    # Embeddings — facts + signals
    click.echo()
    click.echo("→ Step 6: Embedding facts + signals...")
    from linkright.resume.lib.embedder import embed as _embed
    n_facts, dim_facts = rebuild_facts_embeddings(None, _embed)
    n_signals, dim_signals = rebuild_signals_embeddings(None, _embed)
    click.echo(f"  ✓ {n_facts} fact(s) embedded (dim={dim_facts})")
    click.echo(f"  ✓ {n_signals} signal(s) embedded (dim={dim_signals})")

    # Done
    click.echo()
    click.echo("━━━ Onboarding complete ━━━")
    click.echo(f"  Roles:    {len(role_objects)}")
    click.echo(f"  Facts:    {len(confirmed_facts)}")
    click.echo(f"  Signals:  {len(signal_objects)}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  linkright evidence add <doc>     — add additional context")
    click.echo("  linkright diary add              — daily journaling")
    click.echo("  linkright signals list            — inspect derived signals")


def _mint_role_id(role: dict[str, Any]) -> str:
    """Generate a stable, human-readable role_id from company + start_date."""
    company = (role.get("company") or "unknown").lower().replace(" ", "_")
    company = "".join(ch for ch in company if ch.isalnum() or ch == "_")
    start = (role.get("start_date") or "").replace("-", "")[:6]  # YYYYMM
    return f"role_{company}_{start}" if start else f"role_{company}"
