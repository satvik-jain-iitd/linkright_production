"""Optional company-branded resume + cover letter design (Phase 1).

Runs AFTER `linkright resume tailor` — never inline. Output is a separate
`15_final_resume_branded.pdf` alongside the original B&W PDF. The B&W default
is preserved — branding is opt-in.

Cover letter branding (`--cover-letter <md-path>`) renders an additional
`cover_letter_branded.pdf` next to the source markdown. Same color spec —
metric bolds get colored, all other text stays black.

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

import html as _html
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

    Replaces ONLY the hex value — preserves everything after (whitespace,
    `!important`, trailing comments, the closing `;`). This makes the swap
    robust against future template/CSS edits that add `!important` or other
    qualifiers to brand variable declarations.

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
        # Match `--brand-X-color:<ws>#HEX` and replace ONLY the hex.
        # Anything after the hex (`!important`, comments, `;`) is preserved.
        pattern = re.compile(
            rf"({re.escape(css_var)}\s*:\s*)#[0-9A-Fa-f]{{6}}"
        )
        html = pattern.sub(rf"\g<1>{hex_value}", html)
    return html


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")

# Match metric tokens with EXPLICIT units only — $, %, K/M/B, x, ratio, time unit, +.
# Stricter than orchestrator's `_METRIC_REBOLD_RE` (which also matches bare digits)
# because cover letter prose contains many non-metric numbers (years, team sizes,
# addresses) that should NOT be auto-bolded. Reviewer-mandated guard against false
# positives like "joined in 2024" or "led 5 teams".
_METRIC_AUTO_BOLD_RE = re.compile(
    r"""
    (?<![A-Za-z*])                   # not preceded by letter or `*` (avoid Q4, S3, **already-bold**)
    (?:
        \$\d+(?:[.,]\d+)*[KMB]?      # $1.2M, $50K, $100
      | \d+(?:[.,]\d+)*\s*%          # 40%, 99.5%
      | \d+(?:[.,]\d+)*[KMB](?!\w)   # 100K, 1.5M (no `$`)
      | \d+(?:[.,]\d+)*x(?!\w)       # 2x, 10x
      | \d+(?:,\d{3})*:\d+(?:,\d{3})*  # ratios — 2,137:1, 100:50
      | \d+\+                        # 100+, 10+
      | \d+\s*(?:hrs?|hours?|mins?|minutes?|days?|weeks?|months?|years?|wks?|yrs?)(?!\w)  # time units
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _bold_metrics_in_markdown(md: str) -> str:
    """Auto-wrap metric tokens in `**`, preserving existing `**bold**` segments.

    Real cover-letter pipeline produces plain prose — the LLM is told "no
    bullets, only flowing paragraphs" and is never instructed to bold metrics.
    Without this pre-processor, the brand color rule on `<b>` would never
    fire on real CL runs. Reviewer-blocker fix.

    Strategy: split on `**...**` boundaries (preserving them), then auto-bold
    metric tokens only in the non-bolded segments. Avoids double-wrapping.
    """
    parts = re.split(r"(\*\*[^*]+?\*\*)", md)
    result: list[str] = []
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            result.append(part)
        else:
            result.append(
                _METRIC_AUTO_BOLD_RE.sub(lambda m: f"**{m.group(0)}**", part)
            )
    return "".join(result)


def markdown_to_branded_html(md_text: str, primary: str) -> str:
    """Convert cover letter markdown to a minimal branded HTML page.

    Cover letters are prose, not structured sections — so the only colored
    surface is bolded metrics within paragraphs (matching the resume's
    bullet-metric rule). All other text stays black.

    Pipeline:
    1. Auto-wrap metric tokens (`$1.2M`, `40%`, `2,137:1`, etc.) in `**` —
       the real CL LLM does not emit `**`, so without this step bold-coloring
       would never fire. Existing `**bold**` segments are preserved.
    2. Split on blank lines into paragraphs.
    3. HTML-escape each paragraph (XSS guard).
    4. Replace `**...**` → `<b>...</b>` (CSS rule colors `<b>` as primary).
    5. Replace soft newlines with `<br>`.

    Lists, headers, links etc. are NOT supported — CLs do not need them.
    If the LLM produces `# Header` or `- bullet`, they render as plain text.
    """
    md_with_bold_metrics = _bold_metrics_in_markdown(md_text)

    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", md_with_bold_metrics.strip()):
        block = block.strip()
        if not block:
            continue
        # Escape HTML special chars FIRST, then re-introduce <b> tags
        escaped = _html.escape(block)
        # Now replace literal `**...**` (which survived escape — `*` is not HTML special)
        body = _BOLD_RE.sub(r"<b>\1</b>", escaped)
        # Soft newlines within a paragraph → <br>
        body = body.replace("\n", "<br>\n")
        paragraphs.append(f"<p>{body}</p>")

    body_html = "\n".join(paragraphs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cover Letter</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --brand-primary-color: {primary};
    --brand-secondary-color: {primary};
    --brand-tertiary-color: {primary};
    --ui-text-primary-color: #000000;
    --ui-page-bg-color: #FFFFFF;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Roboto', sans-serif;
    color: var(--ui-text-primary-color);
    background: var(--ui-page-bg-color);
    font-size: 11pt;
    line-height: 1.5;
  }}
  .page {{
    width: 210mm;
    min-height: 297mm;
    padding: 25mm;
    background: var(--ui-page-bg-color);
  }}
  p {{ margin-bottom: 4mm; }}
  b {{ color: var(--brand-primary-color); font-weight: 700; }}
  @media print {{
    body {{ background: none; padding: 0; }}
    .page {{ margin: 0; }}
    @page {{ size: A4; margin: 0; }}
  }}
</style>
</head>
<body>
<div class="page">
{body_html}
</div>
</body>
</html>"""


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
@click.option("--cover-letter", "cover_letter_md", default=None,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to cover_letter.md — also renders cover_letter_branded.pdf")
@click.option("--yes", is_flag=True,
              help="Skip interactive prompts (--primary required when set)")
def brand_cmd(
    run_id: str,
    primary: str | None,
    secondary: str | None,
    accent: str | None,
    cover_letter_md: Path | None,
    yes: bool,
) -> None:
    """Apply optional brand colors to a tailored resume (and optional cover letter).

    \b
    Defaults to pure B&W if you skip this step entirely. When you opt in,
    only metric bolds + section dividers get colored — all other text stays
    black, background stays white. Max 3 colors.

    \b
    Cover letter branding (consistency when emailing both together):
      Pass `--cover-letter <path-to-cover_letter.md>` to also render
      `cover_letter_branded.pdf` next to the source markdown.

    \b
    Examples:
      linkright resume brand --run-id 2026-05-03_141023               # interactive prompts
      linkright resume brand --run-id 2026-05-03_141023 \\
          --primary "#635BFF" --secondary "#00D4FF" --accent "#FF6B6B"
      linkright resume brand --run-id <id> --primary "#635BFF" \\
          --cover-letter ~/.linkright/runs/cl-001/artifacts/cover_letter.md
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

    # Resume re-render
    html = html_path.read_text(encoding="utf-8")
    html_branded = apply_brand_to_html(html, primary, secondary, accent)
    branded_html_path = artifacts / "14_final_resume_branded.html"
    branded_html_path.write_text(html_branded, encoding="utf-8")

    branded_pdf_path = artifacts / "15_final_resume_branded.pdf"
    render_branded_pdf(branded_html_path, branded_pdf_path)
    click.echo(f"  branded resume:        {branded_pdf_path}")

    # Cover letter re-render (optional)
    if cover_letter_md is not None:
        cl_md_text = cover_letter_md.read_text(encoding="utf-8")
        cl_html = markdown_to_branded_html(cl_md_text, primary)
        cl_branded_html_path = cover_letter_md.with_name("cover_letter_branded.html")
        cl_branded_html_path.write_text(cl_html, encoding="utf-8")

        cl_branded_pdf_path = cover_letter_md.with_name("cover_letter_branded.pdf")
        render_branded_pdf(cl_branded_html_path, cl_branded_pdf_path)
        click.echo(f"  branded cover letter:  {cl_branded_pdf_path}")

    click.echo(
        "\nOriginal B&W PDF (15_final_resume.pdf) is unchanged. "
        "Email both as needed."
    )
