"""Optional company-branded resume design (Phase 1).

Runs AFTER `linkright resume tailor` — never inline. Output is a separate
`15_final_resume_branded.pdf` alongside the original B&W PDF. The B&W default
is preserved — branding is opt-in.

Per Satvik design spec 2026-05-03 (memory: feedback_brand_design_spec_2026_05_03):
- Default = pure black-and-white. No tinted backgrounds, no colored panels.
- Font color = ALWAYS black. Body, headings, dates, locations, bullets — black.
- Background = ALWAYS white.
- Color lands in EXACTLY 2 places:
    1. Bolded metrics in bullets (`<b>$1.2M</b>`, `<b>70%</b>`)
    2. Section dividers (linear gradient under each section title)
  NOTHING ELSE.
- Subtle, not flashy. Max 3 colors in gradient.

Phase 2 (deferred): admin DB lookup of `companies.brand_*_hex` columns for
`linkright resume brand --auto`.
"""
from __future__ import annotations

import re
from pathlib import Path

import click

from ..config import Config

HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def normalize_hex(s: str | None) -> str | None:
    """Validate and normalize a hex code. Returns `#RRGGBB` (uppercase) or None.

    Accepts: "#635BFF", "635BFF", "#635bff", "635bff" — all normalize to
    "#635BFF". Anything else (3-char hex, named colors, garbage) returns None.
    """
    if not s:
        return None
    s = s.strip()
    if not HEX_RE.match(s):
        return None
    if not s.startswith("#"):
        s = f"#{s}"
    return s.upper()


def apply_brand_to_html(
    html: str,
    primary: str,
    secondary: str | None,
    accent: str | None,
) -> str:
    """Surgically swap brand color CSS variables in the rendered HTML.

    Targets the orchestrator's `:root` override block injected at end of <head>
    by `step_14_assemble_html`:
        --brand-primary-color: #...;
        --brand-secondary-color: #...;
        --brand-tertiary-color: #...;

    Empty `secondary` → falls back to primary (divider becomes solid line).
    Empty `accent` → falls back to secondary (2-stop gradient).
    """
    secondary = secondary or primary
    accent = accent or secondary

    swaps = [
        ("--brand-primary-color", primary),
        ("--brand-secondary-color", secondary),
        ("--brand-tertiary-color", accent),
    ]
    for css_var, hex_value in swaps:
        pattern = re.compile(
            rf"({re.escape(css_var)}:\s*)#[0-9A-Fa-f]{{6}}(\s*;)"
        )
        html = pattern.sub(rf"\g<1>{hex_value}\g<2>", html)
    return html


def render_branded_pdf(html_path: Path, pdf_out: Path) -> Path:
    """Render an HTML file to PDF via Playwright (mirrors step_15_pdf logic)."""
    from playwright.sync_api import sync_playwright

    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_load_state("networkidle")
        page.pdf(
            path=str(pdf_out),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()
    return pdf_out


def _prompt_hex(label: str, required: bool) -> str | None:
    """Interactive hex prompt with re-prompt on invalid input."""
    while True:
        suffix = "" if required else " (optional, press Enter to skip)"
        raw = click.prompt(
            f"  {label} hex{suffix}",
            default="",
            show_default=False,
        )
        if not raw and not required:
            return None
        normalized = normalize_hex(raw)
        if normalized:
            return normalized
        click.echo(
            "    Invalid hex. Expected 6 hex chars like #635BFF or 635BFF. "
            "Try again."
        )


@click.command("brand")
@click.option("--run-id", required=True,
              help="Run ID from `linkright resume tailor` (e.g. 2026-05-03_141023)")
@click.option("--primary", default=None,
              help="Primary brand hex (#RRGGBB) — used for metric bolds + first gradient stop")
@click.option("--secondary", default=None,
              help="Secondary hex — gradient mid-stop. Empty = solid primary line")
@click.option("--accent", default=None,
              help="Accent hex — gradient end-stop. Empty = 2-stop gradient")
@click.option("--yes", is_flag=True,
              help="Skip interactive prompts (--primary required when set)")
def brand_cmd(
    run_id: str,
    primary: str | None,
    secondary: str | None,
    accent: str | None,
    yes: bool,
) -> None:
    """Apply optional brand colors to a tailored resume.

    \b
    Defaults to pure B&W if you skip this step entirely. When you opt in,
    only metric bolds + section dividers get colored — all other text stays
    black, background stays white. Max 3 colors.

    \b
    Examples:
      linkright resume brand --run-id 2026-05-03_141023               # interactive prompts
      linkright resume brand --run-id 2026-05-03_141023 \\
          --primary "#635BFF" --secondary "#00D4FF" --accent "#FF6B6B"
    """
    cfg = Config.load()
    run_dir = cfg.runs_dir() / run_id
    artifacts = run_dir / "artifacts"
    if not artifacts.exists():
        raise click.ClickException(
            f"run_id '{run_id}' not found at {run_dir}. "
            "Did you run `linkright resume tailor` first?"
        )

    html_path = artifacts / "14_final_resume.html"
    if not html_path.exists():
        raise click.ClickException(
            f"14_final_resume.html missing in {artifacts}. "
            "Run `linkright resume tailor` first."
        )

    primary = normalize_hex(primary)
    secondary = normalize_hex(secondary)
    accent = normalize_hex(accent)

    if not primary:
        if yes:
            raise click.ClickException(
                "--primary is required when --yes is set (no interactive prompt)"
            )
        click.echo(
            "Optional company-branded resume design.\n"
            "Subtle styling: only metric numbers + section dividers get colored.\n"
            "All other text stays black, background stays white. Max 3 colors.\n"
        )
        primary = _prompt_hex("Primary brand", required=True)
    if not secondary and not yes:
        secondary = _prompt_hex("Secondary brand", required=False)
    if not accent and not yes:
        accent = _prompt_hex("Accent brand", required=False)

    click.echo(
        f"\nApplying brand colors:\n"
        f"  primary   = {primary}\n"
        f"  secondary = {secondary or '(skip — solid primary line)'}\n"
        f"  accent    = {accent or '(skip — 2-stop gradient)'}\n"
    )

    html = html_path.read_text(encoding="utf-8")
    html_branded = apply_brand_to_html(html, primary, secondary, accent)
    branded_html_path = artifacts / "14_final_resume_branded.html"
    branded_html_path.write_text(html_branded, encoding="utf-8")

    branded_pdf_path = artifacts / "15_final_resume_branded.pdf"
    render_branded_pdf(branded_html_path, branded_pdf_path)

    click.echo(f"  branded resume:  {branded_pdf_path}")
    click.echo(
        "\nOriginal B&W PDF (15_final_resume.pdf) is unchanged. "
        "Email both as needed."
    )
