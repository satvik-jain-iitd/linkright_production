"""PDF -> plain-text extractor.

Uses unpdf (same library as production at repo/website) via a Node subprocess.
pypdf (previous extractor) was replaced because it corrupted bold-rendered
acronyms on Jane's PDF (7 patterns: AM L, M anager, M L, M CP, CM S, HTM L,
M usic). unpdf parity test confirmed 0 corruption on the same PDF.

Fix reference: F03 (vision.md RCA line 3232). bd issue: linkright-dg5.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_UNPDF_SCRIPT = Path(__file__).resolve().parent / "unpdf_parity_test.mjs"


def extract_text(pdf_path: Path) -> str:
    """Extract text via unpdf (Node subprocess). Returns a single merged string.

    Falls back to pypdf if the unpdf subprocess fails (e.g. sandboxed environment
    where Node can't read the module path). pypdf is known to corrupt some
    bold-rendered acronyms (AM L, M anager, M L, M CP) — fallback emits a
    stderr warning so downstream RCA knows.
    """
    try:
        result = subprocess.run(
            ["node", str(_UNPDF_SCRIPT), str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        unpdf_err = f"unpdf exit {result.returncode}: {result.stderr[:300]}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        unpdf_err = f"unpdf subprocess failed: {type(e).__name__}: {e}"

    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError(f"unpdf failed and pypdf not available. unpdf: {unpdf_err}; pypdf: {e}")
    import sys as _sys
    print(
        f"[pdf_parse] WARNING: unpdf failed ({unpdf_err}); falling back to pypdf — "
        "known to corrupt some bold-rendered acronyms (AM L, M anager, etc.)",
        file=_sys.stderr,
    )
    reader = PdfReader(str(pdf_path))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages).strip()
