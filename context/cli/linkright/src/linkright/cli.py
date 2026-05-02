"""LinkRight CLI entry point.

Top-level command groups:
  resume      — Pillar 1: Tailor, score, batch, iterate (16-step pipeline)
  cover-letter — Pillar 1 extension: Cover letter generation (cl alias)
  jobsearch   — Pillar 2: Evaluate, scan, recommend, apply
  interview   — Pillar 3: Schedule, prep, mock, debrief
  content     — Pillar 4: Plan, draft, schedule, performance

Ops commands:
  init        — Bootstrap ~/.linkright/ + MongoDB collections
  mcp serve   — Start per-session MCP server (for Claude Code / Cursor)
  profile     — import / export user data
  auth        — log in to sync.linkright.in (required for jobs commands)

Legacy v0.0 commands (preserved — do not break existing users):
  optimize, validate, assisted
"""
from __future__ import annotations

import json
import sys

import click
import yaml

from linkright import __version__
from linkright.cli_aliases import AliasedGroup
from linkright.resume.cli import resume_group
from linkright.jobsearch.cli import jobsearch_group
from linkright.auth.cli import auth_group
from linkright.interview.cli import interview_group
from linkright.content.cli import content_group
from linkright.coverletter.cli import coverletter_group


_EPILOG = """\
\b
Common workflow:
  linkright tailor -j jd.md       1. Generate tailored resume
  linkright cl -j jd.md           2. Generate cover letter (same JD)
  linkright critique              3. LLM review → issues + fixes
  linkright fill                  4. Resolve missing-metric gaps
  linkright practice              5. Interview prep cards

\b
Quick reference:
  linkright tldr                  cheat sheet
  linkright doctor                health check (config + keys + deps)

\b
Pillars (full names — short aliases also work):
  linkright resume {tailor | score | improve | practice | critique | fill | plan}
  linkright cover-letter -j <jd.md>   (alias: cl)
  linkright profile {create | show | edit-contact | enrich | delete-nugget}
"""


@click.group(cls=AliasedGroup, epilog=_EPILOG)
@click.version_option(version=__version__, prog_name="linkright")
def main() -> None:
    """LinkRight — local-first, agent-native career OS.

    \b
    Try first: linkright tldr
    """


# ── Pillars ─────────────────────────────────────────────────────────────

main.add_command(resume_group)
main.add_command(auth_group)
main.add_command(jobsearch_group)       # name="jobs" (registered in group def)
main.add_command(jobsearch_group, name="jobsearch")  # backward-compat alias
main.add_command(interview_group)
main.add_command(content_group)
main.add_command(coverletter_group)     # name="cover-letter"
main.add_command(coverletter_group, name="cl")  # top-level alias


# ── Top-level shortcuts (skip the `resume` group prefix) ────────────────
def _register_top_level_shortcuts():
    """Add high-frequency commands as top-level shortcuts.

    For each command, the FIRST name in ``names`` is the canonical name
    (registered via ``add_command``, shows in ``--help``). Remaining names
    are registered as aliases (resolution-only, hidden from help). This
    keeps ``--help`` clean while still letting users type short forms.
    """
    from linkright.resume.cli import (
        tailor as _tailor_cmd,
        improve_cmd as _improve_cmd,
    )

    _shortcuts: list[tuple[click.Command, list[str]]] = [
        (_tailor_cmd,   ["tailor",   "t"]),
        (_improve_cmd,  ["improve",  "imp", "i"]),
    ]

    # Other resume.* shortcuts — guarded since some are feature-gated
    for attr, names in (
        ("fill_metrics_cmd",     ["fill",     "f"]),
        ("critique_cmd",         ["critique", "crit", "c"]),
        ("practice_cmd",         ["practice", "prac", "p"]),
        ("strategy_review_cmd",  ["plan",     "review", "r"]),
        ("score",                ["score",    "s"]),
    ):
        try:
            from linkright.resume import cli as _resume_cli
            cmd = getattr(_resume_cli, attr, None)
            if cmd is not None:
                _shortcuts.append((cmd, names))
        except Exception:
            pass

    for cmd, names in _shortcuts:
        canonical, *aliases = names
        try:
            main.add_command(cmd, name=canonical)
        except Exception:
            pass
        for alias in aliases:
            try:
                main.add_alias(alias, canonical)
            except Exception:
                pass

    # Profile shortcut — `contact` (canonical at top level) + `ec` alias.
    try:
        from linkright.profile import cli as _profile_cli
        contact_cmd = getattr(_profile_cli, "edit_contact_cmd", None)
        if contact_cmd is not None:
            try:
                main.add_command(contact_cmd, name="contact")
            except Exception:
                pass
            try:
                main.add_alias("ec", "contact")
            except Exception:
                pass
    except Exception:
        pass


_register_top_level_shortcuts()


# ── Ops commands ────────────────────────────────────────────────────────

@main.command("init")
def init_cmd() -> None:
    """Bootstrap ~/.linkright/ + MongoDB collections + indices."""
    from linkright.db.migrations import init as run_init
    status = run_init(verbose=False)
    click.echo(json.dumps(status, indent=2))
    if not status.get("mongo_ok"):
        click.echo("\n⚠ MongoDB unreachable. Install MongoDB 8 CE and start `mongod`.", err=True)
        sys.exit(1)
    click.echo("\n✓ LinkRight initialized.")


# ── tldr — quick reference cheat sheet ────────────────────────────────────

_TLDR = """\
LinkRight — Quick Reference (cheat sheet)

🚀 Common workflow (most users only need these 5):
  linkright tailor -j <jd.md>      Generate tailored resume for a JD
  linkright cl -j <jd.md>          Generate cover letter for the same JD
  linkright critique               LLM review → 5 actionable issues
  linkright fill                   Resolve missing-metric gaps (interactive)
  linkright practice               Interview prep cards from your resume

📝 Pillar 1 — Cover letter:
  linkright cl -j <jd.md>                      Generate 3-paragraph cover letter
  linkright cl --from-discovery <id>           Cover letter from saved job discovery
  linkright cl -j <jd.md> --tone formal        Formal tone
  linkright cl -j <jd.md> --tone enthusiastic  Enthusiastic tone
  linkright cl -j <jd.md> --pdf               Also render PDF
  linkright cover-letter --help                Full option list

🔍 Pillar 2 — Job feed (daily workflow):
  linkright auth login             Log in to sync.linkright.in (once)
  linkright auth status            Show current session
  linkright jobs find              Today's top-10 scored job matches
  linkright jobs find --top 20     See more results
  linkright jobs show <id>         Full JD + scoring breakdown
  linkright jobs apply <id>        Tailor resume + mark applied
  linkright jobs status <id> saved Save a job for later
  linkright jobs import jobs.csv   Import jobs from CSV

🎯 First-time setup (run once):
  linkright setup                  Pick LLM / embedder / PDF — guided wizard
  linkright profile create -r <resume.pdf>
  linkright contact                Verify phone / email / LinkedIn

🔍 Resume inspect:
  linkright score                  Quality scorecard for latest run
  linkright profile show           Career memory tree
  linkright practice -n            Non-interactive prep packet (pipe-friendly)

🛠  Drill into a specific quality dim:
  linkright improve --target-dim <dim>
  linkright plan                   Strategy review — confirm bullet plan pre-gen

⚡ Shortcuts (single letter — when you don't want to type):
  t   tailor       imp / i  improve     fill / f  fill-metrics
  c   critique     prac / p practice    r         strategy-review
  s   score        cl       cover-letter          ec / contact edit-contact
  (jobs group)  jobs f → find    jobs s → status

🩺 Health:
  linkright doctor                 Check config + API keys + deps
  linkright --version              Print version

📚 Full reference:
  linkright --help                 Top-level groups + commands
  linkright resume --help          All resume subcommands
  linkright jobs --help            All jobsearch subcommands
  linkright auth --help            Auth subcommands
  linkright profile --help         All profile subcommands

Tip: prefix matching works (git-style) — `linkright tail` resolves to `tailor`
if no other tail* exists. Aliases never override exact names; long names
always work too.
"""


@main.command("tldr")
def tldr_cmd() -> None:
    """Print a one-page cheat sheet of the most-used commands."""
    click.echo(_TLDR)


# ── doctor — environment + config + deps health check ─────────────────────

@main.command("doctor")
def doctor_cmd() -> None:
    """Health check — config, API keys, deps, embedder, MongoDB, render path.

    Prints a table of green/red checks. Run this whenever something feels
    broken — it's the fastest way to localize the problem to a specific
    layer (network, missing key, bad install, etc.).
    """
    import os
    import shutil as _shutil

    rows: list[tuple[str, bool, str]] = []

    # 1. ~/.linkright/ + config.yaml present
    home_lr = os.path.expanduser("~/.linkright")
    config_path = os.path.join(home_lr, "config.yaml")
    rows.append(("~/.linkright/ exists", os.path.isdir(home_lr), home_lr))
    rows.append(("config.yaml present",  os.path.isfile(config_path), config_path))

    # 2. Profile present
    profile_dir = os.path.join(home_lr, "profile")
    profile_meta = os.path.join(profile_dir, "metadata.yaml")
    rows.append(("Profile created",      os.path.isfile(profile_meta),
                 profile_meta if os.path.isfile(profile_meta)
                 else "run `linkright profile create -r resume.pdf`"))

    # 3. At least one LLM provider key in env or ~/.linkright/.env
    env_path = os.path.join(home_lr, ".env")
    env_text = ""
    if os.path.isfile(env_path):
        try:
            with open(env_path) as f:
                env_text = f.read()
        except Exception:
            env_text = ""
    provider_envs = [
        "GROQ_API_KEY", "GROQ_API_KEY_2",
        "CEREBRAS_API_KEY", "CEREBRAS_API_KEY_2",
        "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "ZAI_API_KEY", "ZAI_API_KEY_2",
        "SAMBANOVA_API_KEY",
        "CLOUDFLARE_API_TOKEN",
        "OPENROUTER_API_KEY",
    ]
    found_keys = [
        k for k in provider_envs
        if os.environ.get(k) or (k + "=" in env_text)
    ]
    rows.append((
        "At least 1 free-tier LLM key",
        bool(found_keys),
        ", ".join(found_keys[:3]) + (f" (+{len(found_keys)-3} more)" if len(found_keys) > 3 else "")
        if found_keys else "no GROQ/CEREBRAS/GEMINI/ZAI/SAMBANOVA/CLOUDFLARE/OPENROUTER key found",
    ))

    # 4. Embedder availability — fastembed (default) or sentence-transformers
    fastembed_ok = False
    try:
        import fastembed  # noqa: F401
        fastembed_ok = True
    except Exception:
        pass
    rows.append(("Embedder (fastembed)", fastembed_ok,
                 "installed" if fastembed_ok else "pip install fastembed (or set ORACLE_BACKEND_URL)"))

    # 5. PDF render path — playwright OR weasyprint
    pw_ok = False
    try:
        import playwright  # noqa: F401
        pw_ok = True
    except Exception:
        pass
    wp_ok = False
    try:
        import weasyprint  # noqa: F401
        wp_ok = True
    except Exception:
        pass
    rows.append((
        "PDF renderer (playwright|weasyprint)",
        pw_ok or wp_ok,
        ("playwright" if pw_ok else "") + (" + weasyprint" if wp_ok else "") or
        "pip install playwright && playwright install chromium",
    ))

    # 6. unpdf / pypdf for PDF parsing
    unpdf_ok = bool(_shutil.which("node"))
    pypdf_ok = False
    try:
        import pypdf  # noqa: F401
        pypdf_ok = True
    except Exception:
        pass
    rows.append((
        "PDF parser (unpdf via node|pypdf)",
        unpdf_ok or pypdf_ok,
        ("node" if unpdf_ok else "") + (" + pypdf" if pypdf_ok else "") or
        "install node OR `pip install pypdf`",
    ))

    # 7. Mongo (optional — only needed for `linkright init` paths that touch DB)
    mongo_ok = False
    mongo_msg = "(optional — only used by some flows)"
    try:
        import pymongo
        from pymongo import MongoClient
        cli = MongoClient(os.environ.get("MONGODB_URL", "mongodb://localhost:27017"),
                          serverSelectionTimeoutMS=400)
        cli.admin.command("ping")
        mongo_ok = True
        mongo_msg = "reachable"
    except Exception as e:
        mongo_msg = f"unreachable ({type(e).__name__}) — fine unless you use DB-backed flows"
    rows.append(("MongoDB", mongo_ok, mongo_msg))

    # 8. agent-mode CLI present (if config selected one)
    try:
        from linkright.config import Config
        cfg = Config.load()
        backend = getattr(cfg, "agent_backend", None)
    except Exception:
        backend = None
    if backend:
        bin_present = bool(_shutil.which(backend))
        rows.append((f"Agent backend `{backend}` on PATH", bin_present,
                     "installed" if bin_present else f"`{backend}` not on PATH"))

    # 9. Render the table
    GREEN = "\033[32m"; RED = "\033[31m"; DIM = "\033[2m"; RST = "\033[0m"
    width = max(len(label) for label, _, _ in rows)
    click.echo("LinkRight doctor — environment & deps check\n")
    failures = 0
    for label, ok, detail in rows:
        mark = f"{GREEN}✓{RST}" if ok else f"{RED}✗{RST}"
        if not ok:
            failures += 1
        click.echo(f"  {mark}  {label:<{width}}  {DIM}{detail}{RST}")
    click.echo("")
    if failures == 0:
        click.echo(f"{GREEN}All checks passed.{RST} You're good to run `linkright tailor`.")
    else:
        click.echo(f"{RED}{failures} issue(s) above.{RST} "
                   f"Run `linkright setup` to auto-fix common ones, or `linkright tldr` for the cheat sheet.")
        sys.exit(1)


@main.command("setup")
@click.option("--check", is_flag=True, help="Skip the wizard; just smoke-test current config.")
def setup_cmd(check: bool) -> None:
    """Interactive setup wizard — pick LLM / embedder / PDF, auto-install, smoke-test.

    Use this once after `pip install linkright` to get to a working state in ~1 minute.
    Re-run anytime to change picks. Use `--check` to verify current config without prompts.
    """
    from linkright.setup_wizard import run_wizard, run_check
    sys.exit(run_check() if check else run_wizard())


@main.group()
def mcp() -> None:
    """MCP server (agent mode)."""


@mcp.command("serve")
def mcp_serve() -> None:
    """Run the per-session MCP server. Spawned by agent clients (Claude Code / Cursor)."""
    from linkright.llm.mcp import serve
    serve()


# Profile commands live in linkright.profile (one-time creation, persistent
# reuse). This replaces the earlier import-only stub.
from linkright.profile.cli import profile_group as _profile_group
main.add_command(_profile_group)

# Admin commands — Oracle Postgres company knowledge base + slug discovery.
# ORACLE_PG_URL must be configured before admin commands will connect.
from linkright.admin.cli import admin_group as _admin_group
main.add_command(_admin_group)



# ── Legacy v0.0 commands (preserved for back-compat, hidden from --help) ─

@main.command(hidden=True)
@click.option("--resume", "-r", required=True, type=click.Path(exists=True))
@click.option("--jd", "-j", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", default=None, type=click.Path())
@click.option("--template", "-t", default=None, type=click.Path(exists=True))
def optimize(resume: str, jd: str, output: str | None, template: str | None) -> None:
    """(Legacy v0.0) Run the 7-step Click pipeline."""
    from linkright.pipeline import run_pipeline
    result_path = run_pipeline(resume_path=resume, jd_path=jd, output_path=output, template_path=template)
    click.echo(f"Done → {result_path}")


@main.command(hidden=True)
@click.option("--resume", "-r", required=True, type=click.Path(exists=True))
def validate(resume: str) -> None:
    """(Legacy v0.0) Validate career_signals.yaml schema."""
    from linkright.schemas.career_signals import CareerSignals
    with open(resume) as f:
        data = yaml.safe_load(f)
    signals = CareerSignals(**data)
    click.echo(f"✓ Valid — {len(signals.signals)} signals, {sum(len(s.achievements) for s in signals.signals)} achievements")


@main.command(hidden=True)
@click.option("--resume", "-r", required=True, type=click.Path(exists=True))
@click.option("--jd", "-j", required=True, type=click.Path(exists=True))
@click.option("--jd-analysis", required=True, type=click.Path(exists=True))
@click.option("--bullets", "-b", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", default=None, type=click.Path())
@click.option("--template", "-t", default=None, type=click.Path(exists=True))
def assisted(resume: str, jd: str, jd_analysis: str, bullets: str, output: str | None, template: str | None) -> None:
    """(Legacy v0.0) Agent-assisted mode: pre-computed JSON → HTML, zero API calls."""
    from linkright.pipeline_assisted import run_assisted_pipeline
    result = run_assisted_pipeline(
        resume_path=resume, jd_path=jd, jd_analysis_path=jd_analysis,
        bullets_path=bullets, output_path=output, template_path=template,
    )
    click.echo(f"Done → {result['output_path']}")


if __name__ == "__main__":
    main()
