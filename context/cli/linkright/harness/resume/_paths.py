"""Path shim for the resume harness — isolates ``~/.linkright/runs`` lookups."""
from __future__ import annotations

import os
from pathlib import Path

LINKRIGHT_HOME = Path(os.environ.get("LINKRIGHT_HOME", str(Path.home() / ".linkright")))
RUNS_ROOT = LINKRIGHT_HOME / "runs"
HARNESS_ROOT = Path(__file__).resolve().parents[1]  # .../harness
CONTINUOUS_LOG = HARNESS_ROOT / "CONTINUOUS_RCA_LOG.md"


def ensure_runs_root() -> Path:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    return RUNS_ROOT
