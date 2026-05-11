"""LinkRight — local-first, agent-native career OS."""
import os
import logging
from importlib.metadata import version, PackageNotFoundError

# Suppress HuggingFace Hub / tokenizers noise before any lazy import fires.
# setdefault preserves user overrides (e.g. HF_HUB_DISABLE_PROGRESS_BARS=0).
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

for _noisy in (
    "huggingface_hub",
    "huggingface_hub.utils._headers",
    "huggingface_hub.file_download",
    "tokenizers",
    "fastembed",
):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

del _noisy

try:
    # Single source of truth = pyproject.toml. Eliminates version drift.
    __version__ = version("linkright")
except PackageNotFoundError:
    # Editable / dev install before dist-info metadata is generated.
    __version__ = "0.0.0+local"
