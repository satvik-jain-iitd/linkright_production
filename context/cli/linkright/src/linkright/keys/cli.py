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
    click.echo(f"  {total_keys} key(s) across {provider_count} provider(s)  |  "
               f"Resilience: {color}{score}{RST}")
    click.echo("")
    if total_keys == 0:
        click.echo(f"  {YELLOW}No keys configured.{RST} Run `linkright keys add groq` to add your first key.")
    elif score == "FAIR":
        click.echo(f"  {YELLOW}Tip:{RST} Add keys from a 2nd provider for rate-limit resilience.")
    click.echo("")


@keys_group.command("add")
@click.argument("provider", default="")
def keys_add(provider: str) -> None:
    """Add a new key for PROVIDER (groq, cerebras, sambanova, cloudflare, zai, gemini, openrouter).

    Picks the next available slot automatically.
    """
    if not provider:
        # Interactive provider selection
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

    managed = read_all_managed()
    slot = spec.next_available_slot(managed)
    if slot is None:
        click.echo(f"{YELLOW}All 4 key slots for {spec.name} are already used.{RST}")
        click.echo("  Use `linkright keys remove` to free a slot first.")
        sys.exit(1)

    click.echo(f"\n  Adding key for {BOLD}{spec.name}{RST}")
    click.echo(f"  Get a key at: {DIM}{spec.signup_url}{RST}")
    click.echo(f"  Free tier: {spec.free_tier}")
    click.echo(f"  Slot: {slot}")
    click.echo("")

    key_val = questionary.password(f"Paste {spec.name} API key:").ask()
    if key_val is None:
        sys.exit(1)
    key_val = key_val.strip()

    ok, msg = _validate_key_format(spec, key_val)
    if not ok:
        click.echo(f"\n  {RED}Format warning: {msg}{RST}")
        proceed = questionary.confirm("Save anyway?", default=False).ask()
        if not proceed:
            click.echo("  Aborted — key not saved.")
            sys.exit(1)

    updates: dict[str, str] = {slot: key_val}

    # Cloudflare needs a paired account ID
    if spec.paired_env and slot == spec.primary_env:
        account_id = questionary.text(
            f"Cloudflare Account ID (find at dash.cloudflare.com → profile):").ask()
        if account_id:
            updates[spec.paired_env] = account_id.strip()
    elif spec.paired_env:
        # fallback slot — paired slot is CLOUDFLARE_ACCOUNT_ID_N
        slot_idx = spec.extra_envs.index(slot) + 1
        pair_var = f"{spec.paired_env}_{slot_idx}"
        account_id = questionary.text(
            f"Cloudflare Account ID for this key ({pair_var}):").ask()
        if account_id:
            updates[pair_var] = account_id.strip()

    write_keys(updates)
    click.echo(f"\n  {GREEN}✓ Saved {slot} → ~/.linkright/.env{RST}")

    # Re-count
    new_managed = read_all_managed()
    total, pcount = _count_keys(new_managed)
    score = resilience_score(total, pcount)
    click.echo(f"  Cascade resilience: {total} key(s) across {pcount} provider(s) — {score}")
    click.echo("")


@keys_group.command("remove")
@click.argument("provider")
def keys_remove(provider: str) -> None:
    """Remove a key for PROVIDER. Interactive: picks which slot to remove."""
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
            f"Got: `{key_val[:8]}...` — check you copied the right key."
        )
    # Basic alphanumeric + common separators check
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.")
    bad_chars = set(key_val) - allowed
    if bad_chars:
        return False, f"Unexpected characters in key: {bad_chars}"
    return True, "OK"
