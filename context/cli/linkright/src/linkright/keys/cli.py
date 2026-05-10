"""Click commands for `linkright keys` — list / add / remove / test API keys."""
from __future__ import annotations

import sys
from typing import Optional

import click
import questionary

from linkright.keys.catalogue import PROVIDERS, PROVIDER_MAP, resilience_score
from linkright.keys.env_writer import read_all_managed, write_keys, remove_key, mask_key


GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RST    = "\033[0m"


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    """Return singular or plural form based on count."""
    if plural is None:
        plural = singular + "s"
    return f"{count} {singular if count == 1 else plural}"


def _count_keys(managed: dict[str, str]) -> tuple[int, int]:
    """Return (total_key_count, provider_count_with_at_least_one_key)."""
    total = 0
    providers_with_keys = 0
    for p in PROVIDERS:
        count = sum(1 for var in p.all_env_vars if managed.get(var))
        if count:
            total += count
            providers_with_keys += 1
    return total, providers_with_keys



def _ping_and_report(spec: "ProviderSpec", api_key: str, updates: dict[str, str]) -> None:  # noqa: F821
    """K-7: fire a 1-token live ping and print ✓/✗ result. Best-effort — never raises."""
    try:
        from linkright.keys.liveness import probe_key, LivenessStatus
        # Cloudflare needs paired account_id
        paired_val = None
        if spec.paired_env:
            paired_val = updates.get(spec.paired_env) or updates.get(f"{spec.paired_env}_1")
        click.echo(f"  {DIM}Verifying key with a live API ping…{RST}", nl=False)
        status = probe_key(spec, api_key, paired_value=paired_val)
        if status == LivenessStatus.ALIVE:
            click.echo(f"\r  {GREEN}✓ Key valid{RST}                          ")
        elif status == LivenessStatus.RATE_LIMITED:
            click.echo(f"\r  {YELLOW}⚠ Rate-limited — key is valid but quota exhausted{RST}  ")
        elif status == LivenessStatus.INVALID:
            click.echo(f"\r  {RED}✗ Key rejected by {spec.name} — check and re-enter{RST}  ")
        else:
            click.echo(f"\r  {YELLOW}? Could not verify (network error) — key saved, test later with `linkright keys test`{RST}  ")
    except Exception:
        pass  # liveness check is advisory — never block key save


def _offer_more_providers(completed_spec: "ProviderSpec") -> None:  # noqa: F821
    """K-12: after finishing one provider, ask if user wants to add keys for another."""
    managed = read_all_managed()
    # Only show providers that have at least one unconfigured slot
    unconfigured = [
        p for p in PROVIDERS
        if p.key != completed_spec.key and p.next_available_slot(managed) is not None
    ]
    if not unconfigured:
        return  # all providers filled

    add_more = questionary.confirm(
        "  Add keys for another provider?", default=False
    ).ask()
    if not add_more:
        return

    choices = [f"{p.key:<12}  {p.name}" for p in unconfigured]
    selected = questionary.select(
        "Which provider?",
        choices=choices,
        instruction="(↑/↓ to navigate, enter to confirm)",
    ).ask()
    if selected is None:
        return
    next_provider_key = selected.split()[0].strip()
    next_spec = PROVIDER_MAP.get(next_provider_key)
    if not next_spec:
        return

    # Recurse into the add flow for the selected provider
    click.echo(f"\n  Adding key(s) for {BOLD}{next_spec.name}{RST}")
    click.echo(f"  Get keys at: {DIM}{next_spec.signup_url}{RST}")
    click.echo(f"  Free tier: {next_spec.free_tier}")
    if len(next_spec.all_env_vars) > 1:
        click.echo(f"  Supports up to {len(next_spec.all_env_vars)} rotation keys for rate-limit resilience.")
    click.echo("")

    added = 0
    while True:
        managed = read_all_managed()
        slot = next_spec.next_available_slot(managed)
        if slot is None:
            click.echo(f"{YELLOW}All {len(next_spec.all_env_vars)} slot(s) for {next_spec.name} are filled.{RST}")
            break
        key_num = added + 1
        label = "primary key" if slot == next_spec.primary_env else f"key #{key_num} (rotation slot)"
        key_val = questionary.password(f"Paste {next_spec.name} {label}:").ask()
        if key_val is None:
            click.echo("  Aborted.")
            break
        key_val = key_val.strip()
        if not key_val:
            click.echo("  Empty — skipped.")
            break
        ok, msg = _validate_key_format(next_spec, key_val)
        if not ok:
            click.echo(f"\n  {RED}Format warning: {msg}{RST}")
            proceed = questionary.confirm("Save anyway?", default=False).ask()
            if not proceed:
                click.echo("  Key not saved.")
                break
        updates: dict[str, str] = {slot: key_val}
        if next_spec.paired_env and slot == next_spec.primary_env:
            account_id = questionary.text(
                "Cloudflare Account ID (find at dash.cloudflare.com → profile):").ask()
            if account_id:
                updates[next_spec.paired_env] = account_id.strip()
        elif next_spec.paired_env and slot in next_spec.extra_envs:
            slot_idx = next_spec.extra_envs.index(slot) + 1
            pair_var = f"{next_spec.paired_env}_{slot_idx}"
            account_id = questionary.text(f"Cloudflare Account ID for this key ({pair_var}):").ask()
            if account_id:
                updates[pair_var] = account_id.strip()
        write_keys(updates)
        click.echo(f"  {GREEN}✓ Saved → {slot}{RST}")
        _ping_and_report(next_spec, key_val, updates)
        added += 1
        managed = read_all_managed()
        next_slot = next_spec.next_available_slot(managed)
        if next_slot is None:
            click.echo(f"  All {len(next_spec.all_env_vars)} slot(s) for {next_spec.name} filled.")
            break
        add_another = questionary.confirm(
            f"  Add another key for {next_spec.name}? ({next_slot} is next open slot)",
            default=False,
        ).ask()
        if not add_another:
            break

    if added > 0:
        click.echo(f"\n  {GREEN}✓ {added} key(s) saved → {next_spec.name}{RST}")
        new_managed = read_all_managed()
        total, pcount = _count_keys(new_managed)
        score = resilience_score(total, pcount)
        click.echo(f"  Cascade resilience: {total} key(s) across {pcount} provider(s) — {score}")
        click.echo("")

    # Offer yet another provider (tail call — avoids deep recursion on user spree)
    _offer_more_providers(next_spec)


@click.group("keys")
def keys_group() -> None:
    """Manage API keys for LinkRight's LLM cascade (list / add / remove / test)."""


@keys_group.command("list")
def keys_list() -> None:
    """List all configured LR-managed keys, masked. Shows cascade resilience."""
    managed = read_all_managed()
    total_keys, provider_count = _count_keys(managed)

    click.echo("")
    click.echo(f"{BOLD}LinkRight API Keys{RST}")
    click.echo("─" * 48)
    click.echo(f"  {DIM}\u2b50 = recommended (fastest free tier){RST}")

    for p in PROVIDERS:
        has_any = any(managed.get(v) for v in p.all_env_vars)
        if has_any:
            badge = "⭐ " if p.recommended else "   "
            click.echo(f"\n  {badge}{BOLD}{p.name}{RST}")
            for var in p.all_env_vars:
                val = managed.get(var)
                if val:
                    masked = mask_key(val)
                    click.echo(f"    {GREEN}✓{RST}  {var:<30}  {DIM}{masked}{RST}")
            # Cloudflare paired account IDs
            if p.paired_env:
                for i in range(5):
                    pair_var = p.paired_env if i == 0 else f"{p.paired_env}_{i}"
                    val = managed.get(pair_var)
                    if val:
                        masked = mask_key(val)
                        click.echo(f"    {GREEN}✓{RST}  {pair_var:<30}  {DIM}{masked}{RST}")
        else:
            click.echo(f"\n  {DIM}   {p.name:<20}  (not configured){RST}")

    click.echo("")
    click.echo("─" * 48)
    score = resilience_score(total_keys, provider_count)
    color = GREEN if score in ("EXCELLENT", "GOOD") else (YELLOW if score == "FAIR" else RED)
    click.echo(f"  {_plural(total_keys, "key")} across {_plural(provider_count, "provider")}  |  "
               f"Resilience: {color}{score}{RST}")
    click.echo("")
    if total_keys == 0:
        click.echo(f"  {YELLOW}No keys configured.{RST} Run `linkright keys add groq` to add your first key.")
    elif score == "FAIR":
        click.echo(f"  {YELLOW}Tip:{RST} Add keys from a 2nd provider for rate-limit resilience.")

    # K-10: warn about duplicate keys (same last-4 chars for same provider)
    for p in PROVIDERS:
        p_vals = [managed[v] for v in p.all_env_vars if managed.get(v)]
        if len(p_vals) > 1:
            suffixes = [v[-4:] if len(v) >= 4 else v for v in p_vals]
            if len(suffixes) != len(set(suffixes)):
                click.echo(f"  {YELLOW}\u26a0 Duplicate keys detected in {p.name} \u2014 "
                           f"run `linkright keys remove {p.key}` to clean up.{RST}")
    click.echo("")


def _detect_env_keys(spec: "ProviderSpec") -> list[str]:  # noqa: F821
    """Scan os.environ for keys matching this provider.

    Checks:
    1. Each standard slot var (GROQ_API_KEY, GROQ_API_KEY_1..4)
    2. Plural aggregate var (e.g. CEREBRAS_API_KEYS=k1,k2,k3,k4)
    Returns list of raw key strings not already in managed store.
    """
    import os
    found: list[str] = []
    seen: set[str] = set()

    # 1. Standard slot vars
    for var in spec.all_env_vars:
        val = os.environ.get(var, "").strip()
        if val and val not in seen:
            found.append(val)
            seen.add(val)

    # 2. Plural aggregate (CEREBRAS_API_KEYS, GROQ_API_KEYS, CLOUDFLARE_API_TOKENS, etc.)
    if spec.primary_env.endswith(("_KEY", "_TOKEN")):
        plural_var: Optional[str] = spec.primary_env + "S"
    else:
        plural_var = None
    aggregate = os.environ.get(plural_var, "").strip() if plural_var else ""
    if aggregate:
        for k in aggregate.split(","):
            k = k.strip()
            if k and k not in seen:
                found.append(k)
                seen.add(k)

    return found


@keys_group.command("add")
@click.argument("provider", default="")
@click.option("--key", "-k", "key_value", default="", help="Key value (non-interactive / scripting).")
@click.option("--bulk", is_flag=True, help="Paste multiple keys at once (newline or comma separated).")
def keys_add(provider: str, key_value: str, bulk: bool) -> None:
    """Add one or more keys for PROVIDER (groq, cerebras, gemini, sambanova, cloudflare, zai, openrouter).

    Picks the next available slot automatically. After each key, offers to add
    another — useful for loading 4 Cerebras / 3 Gemini rotation keys at once.

    \b
    Examples:
      linkright keys add cerebras            # interactive, prompts for each key
      linkright keys add cerebras --bulk     # paste all keys at once
      linkright keys add groq --key gsk_...  # non-interactive (scripts / CI)
    """
    if not provider:
        choices = [f"{p.key:<12}  {p.name}" for p in PROVIDERS]
        selected = questionary.select(
            "Which provider?",
            choices=choices,
            instruction="(↑/↓ to navigate, enter to confirm)",
        ).ask()
        if selected is None:
            sys.exit(1)
        provider = selected.split()[0].strip()

    spec = PROVIDER_MAP.get(provider.lower())
    if not spec:
        valid = ", ".join(p.key for p in PROVIDERS)
        click.echo(f"{RED}Unknown provider: {provider!r}{RST}. Valid: {valid}")
        sys.exit(1)

    click.echo(f"\n  Adding key(s) for {BOLD}{spec.name}{RST}")
    click.echo(f"  Get keys at: {DIM}{spec.signup_url}{RST}")
    click.echo(f"  Free tier: {spec.free_tier}")
    if len(spec.all_env_vars) > 1:
        click.echo(f"  Supports up to {len(spec.all_env_vars)} rotation keys for rate-limit resilience.")
    click.echo("")

    # ── Non-interactive: --key flag ─────────────────────────────────────────
    if key_value:
        key_value = key_value.strip()
        managed = read_all_managed()
        slot = spec.next_available_slot(managed)
        if slot is None:
            click.echo(f"{YELLOW}All slots filled for {spec.name}.{RST} Use `linkright keys remove` first.")
            sys.exit(1)
        ok, msg = _validate_key_format(spec, key_value)
        if not ok:
            click.echo(f"  {YELLOW}Format warning: {msg}{RST}")
        write_keys({slot: key_value})
        click.echo(f"  {GREEN}✓ Saved {slot} → ~/.linkright/.env{RST}")
        new_managed = read_all_managed()
        total, pcount = _count_keys(new_managed)
        score = resilience_score(total, pcount)
        click.echo(f"  Cascade resilience: {_plural(total, "key")} across {_plural(pcount, "provider")} — {score}\n")
        return

    # ── Bulk mode: --bulk flag ──────────────────────────────────────────────
    if bulk:
        click.echo("  Paste keys (one per line or comma-separated), then press Enter on an empty line:")
        click.echo("")
        lines: list[str] = []
        while True:
            try:
                line = input("  > ").strip()
            except EOFError:
                break
            if not line:
                break
            lines.append(line)
        raw_keys: list[str] = []
        for line in lines:
            for part in line.replace(",", "\n").splitlines():
                part = part.strip()
                if part:
                    raw_keys.append(part)
        if not raw_keys:
            click.echo("  No keys entered. Aborted.")
            sys.exit(1)
        added = 0
        for raw_key in raw_keys:
            managed = read_all_managed()
            slot = spec.next_available_slot(managed)
            if slot is None:
                click.echo(f"  {YELLOW}All slots filled — stopping at {added} key(s).{RST}")
                break
            ok, msg = _validate_key_format(spec, raw_key)
            if not ok:
                click.echo(f"  {YELLOW}⚠ {raw_key[:12]}…  format warning: {msg} — saved anyway{RST}")
            write_keys({slot: raw_key})
            click.echo(f"  {GREEN}✓{RST} {slot}")
            added += 1
        if added == 0:
            click.echo("  No keys saved.")
            sys.exit(1)
        click.echo(f"\n  {GREEN}✓ {_plural(added, "key")} saved to ~/.linkright/.env{RST}")
        new_managed = read_all_managed()
        total, pcount = _count_keys(new_managed)
        score = resilience_score(total, pcount)
        click.echo(f"  Cascade resilience: {_plural(total, "key")} across {_plural(pcount, "provider")} — {score}\n")
        return

    # ── Env auto-detect ─────────────────────────────────────────────────────
    managed = read_all_managed()
    env_keys = _detect_env_keys(spec)
    # Filter out keys already stored
    stored_vals = set(v for v in managed.values() if v)
    fresh_env_keys = [k for k in env_keys if k not in stored_vals]
    if fresh_env_keys:
        click.echo(f"  {GREEN}Found {len(fresh_env_keys)} key(s) for {spec.name} in your shell environment.{RST}")
        for k in fresh_env_keys:
            click.echo(f"    {DIM}{k[:8]}…{k[-4:]}{RST}")
        click.echo("")
        do_import = questionary.confirm(
            f"  Import all {len(fresh_env_keys)} key(s) now?", default=True
        ).ask()
        if do_import:
            imported = 0
            for raw_key in fresh_env_keys:
                managed = read_all_managed()
                slot = spec.next_available_slot(managed)
                if slot is None:
                    click.echo(f"  {YELLOW}All slots filled — stopping at {imported} key(s).{RST}")
                    break
                write_keys({slot: raw_key})
                click.echo(f"  {GREEN}✓{RST} {slot}")
                imported += 1
            new_managed = read_all_managed()
            total, pcount = _count_keys(new_managed)
            score = resilience_score(total, pcount)
            click.echo(f"\n  {GREEN}✓ {_plural(imported, "key")} imported → ~/.linkright/.env{RST}")
            click.echo(f"  Cascade resilience: {_plural(total, "key")} across {_plural(pcount, "provider")} — {score}\n")
            return
        click.echo("")  # user declined import → fall through to manual entry

    # ── Interactive loop ────────────────────────────────────────────────────
    added = 0
    while True:
        managed = read_all_managed()
        slot = spec.next_available_slot(managed)
        if slot is None:
            click.echo(f"{YELLOW}All {len(spec.all_env_vars)} slot(s) for {spec.name} are filled.{RST}")
            break

        key_num = added + 1
        label = "primary key" if slot == spec.primary_env else f"key #{key_num} (rotation slot)"
        key_val = questionary.password(f"Paste {spec.name} {label}:").ask()
        if key_val is None:
            click.echo("  Aborted.")
            break
        key_val = key_val.strip()
        if not key_val:
            click.echo("  Empty — skipped.")
            break

        ok, msg = _validate_key_format(spec, key_val)
        if not ok:
            click.echo(f"\n  {RED}Format warning: {msg}{RST}")
            proceed = questionary.confirm("Save anyway?", default=False).ask()
            if not proceed:
                click.echo("  Key not saved.")
                break

        updates: dict[str, str] = {slot: key_val}

        # Cloudflare needs a paired account ID per key
        if spec.paired_env and slot == spec.primary_env:
            account_id = questionary.text(
                "Cloudflare Account ID (find at dash.cloudflare.com → profile):").ask()
            if account_id:
                updates[spec.paired_env] = account_id.strip()
        elif spec.paired_env and slot in spec.extra_envs:
            slot_idx = spec.extra_envs.index(slot) + 1
            pair_var = f"{spec.paired_env}_{slot_idx}"
            account_id = questionary.text(f"Cloudflare Account ID for this key ({pair_var}):").ask()
            if account_id:
                updates[pair_var] = account_id.strip()

        write_keys(updates)
        click.echo(f"  {GREEN}✓ Saved → {slot}{RST}")
        # K-7: live ping to verify key actually works
        _ping_and_report(spec, key_val, updates)
        added += 1

        # Check if more slots exist; if so offer to add another
        managed = read_all_managed()
        next_slot = spec.next_available_slot(managed)
        if next_slot is None:
            click.echo(f"  All {len(spec.all_env_vars)} slot(s) for {spec.name} filled.")
            break
        add_another = questionary.confirm(
            f"  Add another key for {spec.name}? ({next_slot} is next open slot)",
            default=False,
        ).ask()
        if not add_another:
            break

    if added == 0:
        click.echo("  No keys saved.")
        sys.exit(1)

    click.echo(f"\n  {GREEN}✓ {_plural(added, "key")} saved to ~/.linkright/.env{RST}")
    new_managed = read_all_managed()
    total, pcount = _count_keys(new_managed)
    score = resilience_score(total, pcount)
    click.echo(f"  Cascade resilience: {_plural(total, "key")} across {_plural(pcount, "provider")} — {score}")
    click.echo("")

    # K-12: offer to add keys for another provider after finishing the current one
    # (only in interactive mode — skip for --key / --bulk / env-import paths)
    _offer_more_providers(spec)


@keys_group.command("import")
@click.option("--dry-run", is_flag=True, help="Show what would be imported without saving.")
def keys_import(dry_run: bool) -> None:
    """Scan your shell environment for API keys and import them into ~/.linkright/.env.

    Detects standard slot vars (GROQ_API_KEY, CEREBRAS_API_KEY_1…) and
    aggregate vars (CEREBRAS_API_KEYS=k1,k2,k3). Shows a table of what was
    found, then imports on confirmation (or use --dry-run to preview only).
    """
    managed = read_all_managed()
    stored_vals = set(v for v in managed.values() if v)

    found_rows: list[tuple[str, str, str]] = []  # (provider_name, slot_var, key_val)

    for spec in PROVIDERS:
        env_keys = _detect_env_keys(spec)
        fresh = [k for k in env_keys if k not in stored_vals]
        if not fresh:
            continue
        avail_slots = [s for s in spec.all_env_vars if not managed.get(s)]
        for key_val, slot in zip(fresh, avail_slots):
            found_rows.append((spec.name, slot, key_val))

    click.echo("")
    if not found_rows:
        click.echo("  No new keys found in shell environment.")
        click.echo("  (Checked GROQ_API_KEY, CEREBRAS_API_KEYS, GEMINI_API_KEY, etc.)")
        click.echo("  Use `linkright keys add <provider>` to add keys manually.")
        click.echo("  Or manually edit ~/.linkright/.env (one per line: GROQ_API_KEY=gsk_...)")
        click.echo("")
        return

    label = "Would import" if dry_run else "Found"
    click.echo(f"  {label} {_plural(len(found_rows), 'key')} from shell environment:\n")
    click.echo(f"  {'Provider':<22} {'Slot':<32} {'Key (masked)'}")
    click.echo("  " + "─" * 70)
    for provider_name, slot, key_val in found_rows:
        masked = f"{key_val[:6]}…{key_val[-4:]}" if len(key_val) > 10 else key_val
        click.echo(f"  {provider_name:<22} {slot:<32} {DIM}{masked}{RST}")
    click.echo("")

    if dry_run:
        click.echo(f"  {YELLOW}--dry-run: nothing saved.{RST} Remove --dry-run to import.")
        click.echo("")
        return

    proceed = questionary.confirm(
        f"  Import {len(found_rows)} key(s) into ~/.linkright/.env?", default=True
    ).ask()
    if not proceed:
        click.echo("  Aborted — no keys saved.")
        return

    updates: dict[str, str] = {slot: key_val for _, slot, key_val in found_rows}
    write_keys(updates)

    click.echo(f"\n  {GREEN}✓ {_plural(len(updates), 'key')} imported → ~/.linkright/.env{RST}")
    new_managed = read_all_managed()
    total, pcount = _count_keys(new_managed)
    score = resilience_score(total, pcount)
    click.echo(f"  Cascade resilience: {_plural(total, "key")} across {_plural(pcount, "provider")} — {score}")
    click.echo("")


@keys_group.command("remove")
@click.argument("provider", default="")
def keys_remove(provider: str) -> None:
    """Remove a key for PROVIDER. Interactive: picks which slot to remove."""
    if not provider:
        valid = ", ".join(p.key for p in PROVIDERS)
        click.echo(f"Usage: linkright keys remove <provider>")
        click.echo(f"Providers: {valid}")
        sys.exit(1)
    spec = PROVIDER_MAP.get(provider.lower())
    if not spec:
        valid = ", ".join(p.key for p in PROVIDERS)
        click.echo(f"{RED}Unknown provider: {provider!r}{RST}. Valid: {valid}")
        sys.exit(1)

    managed = read_all_managed()
    configured = [(var, managed[var]) for var in spec.all_env_vars if managed.get(var)]
    if not configured:
        click.echo(f"  No keys configured for {spec.name}.")
        sys.exit(0)

    choices = [f"{var}  ({mask_key(val)})" for var, val in configured]
    choices.append("Cancel")
    selected = questionary.select(
        f"Which key to remove from {spec.name}?",
        choices=choices,
        instruction="(↑/↓ to navigate, enter to confirm)",
    ).ask()
    if selected is None or selected == "Cancel":
        click.echo("  Cancelled.")
        sys.exit(0)

    var_name = selected.split()[0].strip()
    removed = remove_key(var_name)
    if removed:
        click.echo(f"  {GREEN}✓ Removed {var_name}{RST}")
    else:
        click.echo(f"  {YELLOW}Key {var_name} was not present.{RST}")


@keys_group.command("test")
def keys_test() -> None:
    """Test each configured key with a 1-token ping. Reports alive / rate-limited / invalid."""
    from linkright.keys.liveness import probe_key, LivenessStatus, STATUS_SYMBOLS

    managed = read_all_managed()
    total, _ = _count_keys(managed)
    if total == 0:
        click.echo(f"  {YELLOW}No keys configured. Run `linkright keys add groq` to add one.{RST}")
        sys.exit(0)

    click.echo("")
    click.echo(f"{BOLD}LinkRight Keys — Live Test{RST}")
    click.echo("─" * 48)
    click.echo(f"  {DIM}Testing {total} key(s) with 1-token completions…{RST}")
    click.echo("")

    alive = rate_limited = invalid = error = 0

    for p in PROVIDERS:
        keys_for_provider = [(var, managed[var]) for var in p.all_env_vars if managed.get(var)]
        if not keys_for_provider:
            continue
        click.echo(f"  {BOLD}{p.name}{RST}")
        for var, val in keys_for_provider:
            masked = mask_key(val)
            # Cloudflare needs paired account ID
            paired_val = None
            if p.paired_env:
                if var == p.primary_env:
                    paired_val = managed.get(p.paired_env)
                else:
                    slot_idx = p.extra_envs.index(var) + 1
                    paired_val = managed.get(f"{p.paired_env}_{slot_idx}")

            status = probe_key(p, val, paired_value=paired_val)
            sym, color = STATUS_SYMBOLS[status]
            label = status.value.replace("_", "-")
            click.echo(f"    {color}{sym}{RST}  {var:<30}  {DIM}{masked}{RST}  → {color}{label}{RST}")
            if status == LivenessStatus.ALIVE:
                alive += 1
            elif status == LivenessStatus.RATE_LIMITED:
                rate_limited += 1
            elif status == LivenessStatus.INVALID:
                invalid += 1
            else:
                error += 1

    click.echo("")
    click.echo("─" * 48)
    click.echo(f"  {GREEN}alive: {alive}{RST}  "
               f"{YELLOW}rate-limited: {rate_limited}{RST}  "
               f"{RED}invalid: {invalid}{RST}  "
               f"{DIM}error: {error}{RST}")
    click.echo("")


def _validate_key_format(spec: "ProviderSpec", key_val: str) -> tuple[bool, str]:  # noqa: F821
    """Validate key format. Returns (ok, message)."""
    if len(key_val) < spec.key_min_len:
        return False, (
            f"Key too short ({len(key_val)} chars, expected ≥{spec.key_min_len}). "
            f"Did you paste the full key?"
        )
    if spec.key_prefix and not key_val.startswith(spec.key_prefix):
        return False, (
            f"Expected format: `{spec.key_prefix}...` for {spec.name}. "
            f"Got: `{key_val[:4]}...` — check you copied the right key."
        )
    # Basic alphanumeric + common separators check
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.")
    bad_chars = set(key_val) - allowed
    if bad_chars:
        return False, f"Unexpected characters in key: {bad_chars}"
    return True, "OK"
