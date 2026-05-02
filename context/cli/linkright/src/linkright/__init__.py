"""LinkRight — local-first, agent-native career OS."""
from importlib.metadata import version, PackageNotFoundError

try:
    # Single source of truth = pyproject.toml. Eliminates version drift.
    __version__ = version("linkright")
except PackageNotFoundError:
    # Editable / dev install before dist-info metadata is generated.
    __version__ = "0.0.0+local"
