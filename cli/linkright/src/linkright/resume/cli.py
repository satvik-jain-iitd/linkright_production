"""`linkright resume` subcommand group.

Subcommands:
  tailor  — resume + JD → tailored HTML/PDF + scorecard
  score   — compute scorecard for an existing PDF against a JD
  batch   — tailor across a directory of JDs
  iterate — open the B1-B9 iteration loop (harness-driven)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from ..config import Config


@click.group(name="resume")
def resume_group() -> None:
    """Pillar 1 — Resume tailoring + scoring."""


@resume_group.command("tailor")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Resume PDF or career_signals.yaml")
@click.option("--jd", "-j", "jd_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Job description markdown file")
@click.option("--mode", default=None, help="Skill mode: product_manager | swe | ds | designer | generic")
@click.option("--llm-mode", type=click.Choice(["agent", "direct", "mcp"]), default=None,
              help="LLM routing: agent (MCP, default) | direct (user's key) | mcp (alias)")
@click.option("--yes", is_flag=True, help="Skip interactive confirmations")
@click.option("--run-id", default=None, help="Override run id (defaults to timestamp)")
@click.option("--no-cache", is_flag=True, help="Skip the ~/.linkright/profile/ cache; force fresh parse+extract+embed.")
@click.option("--deterministic", is_flag=True,
              help="Pin temperature=0 + seed across all LLM calls. Pairs with hypothesis-test for variance reduction.")
@click.option("--seed", default=42, type=int, help="Seed for deterministic mode (default 42). Honoured by Groq/Cerebras/OpenRouter; Gemini ignores.")
def tailor(resume_path: Path, jd_path: Path, mode: str | None, llm_mode: str | None, yes: bool, run_id: str | None, no_cache: bool, deterministic: bool, seed: int) -> None:
    """Tailor resume for a JD via the 16-step pipeline."""
    cfg = Config.load()
    llm_mode = llm_mode or cfg.default_llm_mode
    mode = mode or cfg.default_skill_mode
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

    if deterministic:
        os.environ["LR_DETERMINISTIC"] = "1"
        os.environ["LR_SEED"] = str(seed)
        click.echo(f"Deterministic mode ON (seed={seed}) — temperature pinned to 0 across all LLM calls.")

    run_dir = cfg.runs_dir() / run_id
    (run_dir / "inputs").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    # Stage inputs — orchestrator expects inputs/{resume.pdf|resume.md,jd.md}
    if resume_path.suffix.lower() == ".pdf":
        shutil.copy(resume_path, run_dir / "inputs" / "resume.pdf")
    elif resume_path.suffix.lower() in (".md", ".markdown"):
        shutil.copy(resume_path, run_dir / "inputs" / "resume.md")
    else:
        shutil.copy(resume_path, run_dir / "inputs" / resume_path.name)
    shutil.copy(jd_path, run_dir / "inputs" / "jd.md")

    # Profile-cache pre-populate: if ~/.linkright/profile/ exists AND its
    # embedder tier matches the active tier, copy the per-step artifacts
    # into run_dir so orchestrator's step_00..03 cache guards short-circuit
    # (saves 30-60 sec of LLM + embed work per run).
    cache_used = False
    if not no_cache:
        from linkright.profile.pipeline import _profile_dir, load_metadata
        from linkright.resume.lib.embedder import _detect_tier
        profile_dir = _profile_dir()
        meta = load_metadata(profile_dir)
        if meta:
            active_tier = _detect_tier()
            if meta.get("embedder_tier") == active_tier:
                profile_artifacts = profile_dir / "artifacts"
                cached_files = ["00_resume_raw_text.txt", "01_resume_parsed.json",
                                "02_nuggets_extracted.json", "03_nuggets_embedded.jsonl"]
                copied = []
                for fname in cached_files:
                    src = profile_artifacts / fname
                    if src.exists():
                        shutil.copy(src, run_dir / "artifacts" / fname)
                        copied.append(fname)
                if copied:
                    cache_used = True
                    click.echo(f"✓ Profile cache hit — reusing {len(copied)} artifacts from ~/.linkright/profile/ "
                               f"(saves ~30-60s of step_00-03 work).")
            else:
                click.echo(f"⚠ Profile embedder tier ({meta.get('embedder_tier')}) ≠ active tier "
                           f"({active_tier}); skipping cache (rebuild profile to align).")

    click.echo(f"Run ID: {run_id}")
    click.echo(f"Output: {run_dir}")
    click.echo(f"LLM mode: {llm_mode}  •  Skill mode: {mode}")
    if no_cache:
        click.echo("Cache: --no-cache flag set, fresh extraction.")

    if llm_mode in ("direct", "agent", "mcp"):
        # 2026-05-01: agent/mcp modes share the same orchestrator path as direct.
        # The dispatch difference lives inside `linkright.llm.direct.chat_with_fallback`
        # (and sibling functions) which check LR_LLM_MODE and route through the user's
        # chosen CLI subprocess (`agent_chat`) when set to "agent". This means agent-mode
        # reuses all 16 pipeline steps + telemetry + scorecard wiring without duplication.
        if llm_mode in ("agent", "mcp"):
            os.environ["LR_LLM_MODE"] = "agent"
            # Route to the backend picked by the user in `linkright setup`.
            # Env var takes priority — only set if the user hasn't already overridden.
            if not os.environ.get("LR_AGENT_BACKEND") and getattr(cfg, "agent_backend", None):
                os.environ["LR_AGENT_BACKEND"] = cfg.agent_backend
            backend = os.environ.get("LR_AGENT_BACKEND", "claude")
            click.echo(f"Agent mode active — '{backend}' CLI subprocess handles LLM calls (no API keys needed).")
        # Delegate to the 16-step pipeline
        from . import orchestrator
        orchestrator.RUN_DIR = run_dir
        orchestrator.ARTIFACTS = run_dir / "artifacts"
        orchestrator.INPUTS = run_dir / "inputs"
        orchestrator.LOG_PATH = run_dir / "logs" / "pipeline.log"
        orchestrator.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        orchestrator.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Orchestrator's main() expects argparse; we invoke the lower-level run
            # primitives individually when an entry exists, else fall back to main.
            if hasattr(orchestrator, "run"):
                orchestrator.run(run_id=run_id)
            else:
                # Shim: call main() via argv
                old_argv = sys.argv
                sys.argv = ["orchestrator.py", "--run-id", run_id]
                try:
                    orchestrator.main()
                finally:
                    sys.argv = old_argv
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            click.echo(f"Pipeline error: {e}", err=True)
            raise click.Abort()
        click.echo(f"✓ Done — see {run_dir}")
    else:
        raise click.BadParameter(f"Unknown llm-mode: {llm_mode}")


@resume_group.command("verify")
@click.argument("run_id")
@click.option("--strict", is_flag=True, help="Exit non-zero if any canary fails.")
def verify_cmd(run_id: str, strict: bool) -> None:
    """Run canary checks on a completed `tailor` run.

    Catches silent failure modes (0% coverage despite exit 0, telemetry $0
    when LLM ran, all-zero cosines indicating broken embedder, etc.).
    """
    import sys as _sys
    # Make harness package importable (lives beside src/, not inside it).
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.canaries import run_all, format_report
    cfg = Config.load()
    run_dir = cfg.runs_dir() / run_id
    if not run_dir.exists():
        click.echo(f"Run dir not found: {run_dir}", err=True)
        _sys.exit(1)
    all_passed, results = run_all(run_dir=run_dir)
    click.echo(format_report(results))
    if strict and not all_passed:
        _sys.exit(2)


@resume_group.command("score")
@click.option("--pdf", "pdf_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--jd", "jd_path", type=click.Path(exists=True, path_type=Path), required=True)
def score(pdf_path: Path, jd_path: Path) -> None:
    """Score an existing PDF against a JD using the resume scorecard (stub — wires in Phase 4A-complete)."""
    click.echo(f"Scorecard stub — pdf={pdf_path.name}, jd={jd_path.name}")
    click.echo("Resume scorecard harness: harness/resume/ (to be wired).")


@resume_group.command("batch")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--jds", "jds_dir", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
@click.option("--parallel", default=3, type=int)
def batch(resume_path: Path, jds_dir: Path, parallel: int) -> None:
    """Tailor resume across a directory of JDs (parallel)."""
    jds = sorted(jds_dir.glob("*.md"))
    click.echo(f"Found {len(jds)} JDs; would tailor with parallel={parallel}")
    click.echo("(Batch runner uses asyncio.gather + per-run subprocess — implemented after direct-mode ships.)")


@resume_group.command("iterate")
@click.option("--run-id", default=None, help="Run id under ~/.linkright/runs/ (defaults to latest)")
@click.option("--max-iterations", default=3, type=int, help="Max B1-B9 loops (informational)")
def iterate(run_id: str | None, max_iterations: int) -> None:
    """Open the B1-B9 iteration loop: pick worst dim → propose fix → re-run."""
    # Make the top-level `harness` package importable (lives beside src/, not inside it)
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.iterate import run_iterate
    run_iterate(run_id=run_id, max_iterations=max_iterations)


@resume_group.command("improve")
@click.option("--run-id", default=None, help="Run id (defaults to latest non-hypothesis run)")
@click.option("--target-dim", default=None,
              help="Scorecard dim to improve. If unset, picks weakest. MVP: width_hit_rate only.")
@click.option("--dry-run", is_flag=True,
              help="Identify deficiencies but don't actually call LLM for refinement.")
def improve_cmd(run_id: str | None, target_dim: str | None, dry_run: bool) -> None:
    """REFINE existing bullets — NOT regenerate from scratch.

    Per Satvik 2026-05-01: scratch regen (tailor command) generates new content;
    improve (this command) reads existing artifacts, identifies what's missing
    vs target dim, runs targeted refinement LLM calls to fix ONLY that
    deficiency while preserving everything else (metrics, bolds, verbs).

    MVP supports `width_hit_rate` only — bullets outside [108,118] char band
    get trimmed/expanded via klass=B refinement. Pattern extends to other dims.
    """
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.improve import run_improve
    result = run_improve(run_id=run_id, target_dim=target_dim, dry_run=dry_run)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("fill-metrics")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
@click.option("--dry-run", is_flag=True,
              help="Detect gaps and print, but skip user prompts + LLM rewrites.")
def fill_metrics_cmd(run_id: str | None, dry_run: bool) -> None:
    """Interactive truth-engine — fill missing/weak bullet metrics from user input.

    Truth Engine track extension. For every bullet whose magnitude tier is
    <= 0.5 (raw count or no metric), the tool:
      1. Shows 3 LLM-suggested metric TYPES (e.g., cost reduction, time saved,
         user reach) with industry-average ranges + per-bullet rationale.
      2. User picks ONE type (or marks "metric not relevant" to skip).
      3. User picks ONE of three paths:
           a. Provide actual value (e.g., '18%')
           b. Use placeholder ('X%', 'Y$M', 'Z hours' — fill offline later)
           c. Cancel — leave bullet alone
      4. Bullet rewritten with chosen value; re-render + re-score.

    Placeholders are NOT fabrication — they openly signal "value pending".
    A common industry pattern for NDA / privacy / mid-process candidates.
    Per Satvik 2026-05-02: this is coaching about what metrics matter; user
    supplies actuals offline, tool never invents numbers.
    """
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.fill_metrics import run_fill_metrics
    result = run_fill_metrics(run_id=run_id, dry_run=dry_run)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("practice")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
@click.option("--non-interactive", is_flag=True,
              help="Print the full prep packet without prompting (for piping/review).")
def practice_cmd(run_id: str | None, non_interactive: bool) -> None:
    """Walk through interview-practice cards generated from your tailored resume.

    Reads `<run>/artifacts/15b_interview_prep.json` (auto-generated by
    step_14 via NEW-6 hybrid signal classifier) and shows per bullet:
      - the competency signal it conveys
      - 2 recruiter screening questions this bullet best answers
      - STAR seed template (Action pre-filled from the bullet)
      - prompt to type your answer (saved as audit log)

    Per Satvik 2026-05-02 (memory feedback_bullets_sell_fit_and_seed_stories):
    "every bullet must serve as baseline narrative for Round 1 / HR screening
    rounds for common questions that are always asked always". This command
    operationalizes that — Pillar 1 (resume) ↔ Pillar 3 (interview prep) bridge.
    """
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.practice import run_practice
    result = run_practice(run_id=run_id, interactive=not non_interactive)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("strategy-review")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
def strategy_review_cmd(run_id: str | None) -> None:
    """Review the bullet plan BEFORE generation — Truth Engine Layer 2 (PRE).

    Per Satvik 2026-05-02 (memory feedback_strategy_human_in_the_loop):
    "the strategy step where outline is decided is the MOST CRUCIAL PHASE,
    align with user on all the things before building out the resume,
    dimensions, no of bullets, what kind of experience will be showcased
    by each bullet in order of alignment with highest on top in every
    job role/title inside a company".

    Workflow:
      1. Run `linkright resume tailor` once (produces artifacts incl. step_07/08)
      2. Run THIS command — review per-role nugget plan, pick which become bullets
      3. Future tailor runs read the confirmed plan and override auto-retrieval
    """
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.strategy_review import run_strategy_review
    result = run_strategy_review(run_id=run_id)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("critique")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
def critique_cmd(run_id: str | None) -> None:
    """End-of-pipeline LLM critique — Truth Engine Layer 3.

    Reads the rendered resume + JD, asks an LLM critic to identify up to 5
    actionable issues (weak phrasings, generic skills, missing JD coverage,
    illogical bullets, etc.), then walks each issue interactively. Per
    issue, user picks: apply suggested fix / open in $EDITOR for manual
    edit / skip.

    Closes the Truth Engine loop:
      Layer 1 (start):  `linkright profile create` → contact verify
      Layer 2 (mid):    `linkright resume fill-metrics` → metric resolution
      Layer 3 (end):    THIS command — critique + fix-or-skip per issue

    Per Satvik 2026-05-02: "ask the model to criticise and say what does
    not make sense and how to fix it and then figure out with the user how
    to go about improving the resume with couple of options (including a
    manual edit one)".
    """
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.critique import run_critique
    result = run_critique(run_id=run_id)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("hypothesis-test")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Path to resume PDF (or pre-existing profile staged file).")
@click.option("--jd", "-j", "jd_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Path to job description markdown.")
@click.option("--hypothesis", required=True,
              help="One-line description of the hypothesis being tested. Logged to CONTINUOUS_RCA_LOG.md.")
@click.option("--variant-env", "variant_env_pairs", multiple=True,
              help="key=value env var override applied to variant arm only. "
                   "May be specified multiple times. "
                   "Common: LR_TIER_OVERRIDE_<step|intent>=<provider>.")
@click.option("--target-dim", "target_dims", multiple=True,
              help="Scorecard dim(s) the variant should improve (e.g. keyword_coverage). "
                   "If unset, falls back to overall_score.")
@click.option("--n", default=3, type=int, help="Runs per arm (default 3 → 6 total pipelines).")
@click.option("--seed", default=42, type=int, help="Seed base. Each run uses seed+i.")
@click.option("--skip-baseline", is_flag=True,
              help="Run only the variant arm; assumes a baseline arm was run earlier under the same hypothesis_id.")
def hypothesis_test_cmd(resume_path, jd_path, hypothesis, variant_env_pairs,
                        target_dims, n, seed, skip_baseline) -> None:
    """K baseline + K variant runs (deterministic mode) → median + stdev → KEEP/REVERT/INCONCLUSIVE.

    Single-command 99% iteration loop primitive. Each arm runs ``n`` pipelines
    with `LR_DETERMINISTIC=1`, scores via ResumeScorecard, computes per-dim
    median + stdev, applies the decision rule, and appends a YAML block to
    ``harness/CONTINUOUS_RCA_LOG.md``.

    Decision rule:
      KEEP        any --target-dim improved ≥ 2× pooled_stdev AND no other
                  dim regressed > 1× stdev
      REVERT      any target dim regressed ≥ 1× stdev
                  OR any non-target dim regressed ≥ 1× stdev
      INCONCLUSIVE no target improvement above noise band → suggest higher --n

    Exit codes: 0 KEEP, 1 REVERT, 2 INCONCLUSIVE.
    """
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.hypothesis_test import run_hypothesis_test

    variant_env: dict[str, str] = {}
    for pair in variant_env_pairs:
        if "=" not in pair:
            click.echo(f"Invalid --variant-env: {pair!r} (expected key=value)", err=True)
            sys.exit(2)
        k, v = pair.split("=", 1)
        variant_env[k.strip()] = v.strip()

    result = run_hypothesis_test(
        resume_path=resume_path,
        jd_path=jd_path,
        hypothesis=hypothesis,
        variant_env=variant_env,
        target_dims=list(target_dims),
        n=n,
        seed_base=seed,
        skip_baseline=skip_baseline,
    )

    if result["verdict"] == "REVERT":
        sys.exit(1)
    if result["verdict"] == "INCONCLUSIVE":
        sys.exit(2)
