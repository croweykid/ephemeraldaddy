# ephemeraldaddy/__init__.py
"""Compatibility package entrypoint for the source checkout.

The repository root and the importable application package are both named
``ephemeraldaddy``.  When pytest imports this root ``__init__`` during test
collection, Python's package path otherwise points only at the repository root
and cannot resolve subpackages such as ``ephemeraldaddy.core`` from the nested
source directory.  Include the nested source directory in this package path
before importing the dependency bootstrap.
"""

from pathlib import Path

_SOURCE_PACKAGE_DIR = Path(__file__).resolve().parent / "ephemeraldaddy"
if _SOURCE_PACKAGE_DIR.is_dir():
    __path__.append(str(_SOURCE_PACKAGE_DIR))

from ephemeraldaddy.core.deps import ensure_all_deps

# Ensure dependencies are present as soon as the package is imported.
ensure_all_deps(verbose=True)
