"""linkright.lib — runtime helpers used across CLI surfaces.

Empty marker file. Required by setuptools.find_packages() for directories
to be recognized as importable packages and bundled into the wheel.
Without this file, the version-check helper would silently disappear from
PyPI installs (dev-mode editable installs would still work via Python 3.3+
namespace packages, but real users would get ImportError swallowed by the
try/except guards in cli.py).
"""
