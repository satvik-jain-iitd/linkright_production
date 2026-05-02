"""`linkright auth` subcommand group.

Manages the ~/.linkright/session.json Supabase JWT session.

Methods:
  login --method email   — email + password via Supabase REST
  login --method jwt     — manual paste of existing JWT from browser
  status                 — show current session info
  logout                 — clear session
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import click

from linkright.config import LINKRIGHT_HOME
from linkright.cli_aliases import AliasedGroup

# Supabase project config (public values — same as the browser bundle)
_SUPABASE_URL = "https://ahjapzyslbhyjekswqpt.supabase.co"
_SUPABASE_ANON_KEY = "sb_publishable_S0yYFybP8e5IH22ebRdAdw_JqFb_dHg"


@click.group(cls=AliasedGroup, name="auth")
def auth_group() -> None:
    """Auth — log in to sync.linkright.in to access your job feed."""


@auth_group.command("login")
@click.option(
    "--method",
    type=click.Choice(["email", "jwt"]),
    default=None,
    help="email = email+password login; jwt = paste existing browser JWT",
)
def login(method: str | None) -> None:
    """Log in to sync.linkright.in and save JWT session locally.

    \b
    Two methods:
      email  — enter your email + password (recommended for most users)
      jwt    — paste a JWT you copied from browser DevTools (advanced)
    """
    from linkright.auth import save_session

    if method is None:
        click.echo("How would you like to log in?")
        click.echo("  [1] email + password  (recommended)")
        click.echo("  [2] Paste JWT from browser DevTools  (advanced)")
        choice = click.prompt("Choice", type=click.Choice(["1", "2"]), default="1", show_choices=False)
        method = "email" if choice == "1" else "jwt"

    if method == "email":
        _login_email(save_session)
    else:
        _login_jwt(save_session)


def _login_email(save_session_fn) -> None:
    """Login via email + password using Supabase REST auth."""
    import httpx
    from datetime import timedelta

    email = click.prompt("Email")
    password = click.prompt("Password", hide_input=True)

    url = f"{_SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": _SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    body = {"email": email, "password": password}

    click.echo("Logging in...", nl=False)
    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=15)
    except Exception as e:
        click.echo(f" failed.\nNetwork error: {e}", err=True)
        sys.exit(1)

    if resp.status_code != 200:
        click.echo(" failed.", err=True)
        try:
            err_body = resp.json()
            err_detail = (
                err_body.get("error_description")
                or err_body.get("msg")
                or err_body.get("error")
                or resp.text
            )
        except Exception:
            err_detail = resp.text
        click.echo(f"Error: {err_detail}", err=True)
        sys.exit(1)

    data = resp.json()
    expires_in = data.get("expires_in", 3600)
    exp_dt = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    user_obj = data.get("user", {}) or {}
    session = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": exp_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user_id": user_obj.get("id", ""),
        "email": user_obj.get("email", email),
    }
    save_session_fn(session)
    click.echo(
        f" done.\n"
        f"Logged in as {session['email']} (session valid until {session['expires_at']}).\n"
        f"\nTry:  linkright jobs find"
    )


def _login_jwt(save_session_fn) -> None:
    """Login by pasting a JWT from browser DevTools."""
    click.echo(
        "\nTo get your JWT from the browser:\n"
        "  1. Open sync.linkright.in and log in\n"
        "  2. Open DevTools → Console\n"
        "  3. Run: JSON.parse(localStorage.getItem('supabase.auth.token')).currentSession.access_token\n"
        "  4. Copy the token (starts with eyJ)\n"
    )
    jwt_token = click.prompt("Paste your access_token").strip()

    if not jwt_token.startswith("eyJ"):
        click.echo(
            "Error: that doesn't look like a JWT (should start with eyJ).\n"
            "Try --method email instead.",
            err=True,
        )
        sys.exit(1)

    # Decode payload to get user info + expiry (base64, no signature check needed here)
    exp_dt = None
    sub = ""
    user_email = ""
    try:
        import base64
        parts = jwt_token.split(".")
        if len(parts) >= 2:
            padding = 4 - len(parts[1]) % 4
            padded = parts[1] + ("=" * padding)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            exp_ts = payload.get("exp", 0)
            sub = payload.get("sub", "")
            user_email = payload.get("email", "")
            if exp_ts:
                exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    except Exception:
        pass

    if exp_dt and exp_dt <= datetime.now(timezone.utc):
        click.echo(
            "Warning: that JWT is already expired. Please log in fresh at sync.linkright.in.",
            err=True,
        )
        sys.exit(1)

    session = {
        "access_token": jwt_token,
        "refresh_token": "",
        "expires_at": exp_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if exp_dt else "",
        "user_id": sub,
        "email": user_email,
    }
    save_session_fn(session)
    msg = "Session saved"
    if exp_dt:
        msg += f" (valid until {session['expires_at']})"
    click.echo(f"{msg}.\n\nTry:  linkright jobs find")


@auth_group.command("status")
def status_cmd() -> None:
    """Show current session info (logged-in user + expiry)."""
    from linkright.auth import load_session

    sess = load_session()
    if not sess:
        click.echo("Not logged in (or session expired). Run: linkright auth login")
        return

    click.echo(f"Logged in as : {sess.get('email') or '(unknown)'}")
    click.echo(f"User ID      : {sess.get('user_id') or '(unknown)'}")
    click.echo(f"Expires at   : {sess.get('expires_at') or '(unknown)'}")
    click.echo(f"Session file : {LINKRIGHT_HOME / 'session.json'}")


@auth_group.command("logout")
def logout() -> None:
    """Clear the local session (does not revoke the server-side JWT)."""
    from linkright.auth import clear_session, load_session

    if not load_session():
        click.echo("No active session to clear.")
        return
    clear_session()
    click.echo("Logged out. Session file removed.")
