"""Python runtime compatibility checks for EphemeralDaddy."""

from __future__ import annotations

import sys

SUPPORTED_PYTHON_MIN = (3, 11)
SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 12)
SUPPORTED_PYTHON_LABEL = "3.11"


def _version_label(version_info: tuple[int, int] | sys.version_info = sys.version_info) -> str:
    return f"{version_info[0]}.{version_info[1]}"


def python_compatibility_message(
    version_info: tuple[int, int] | sys.version_info = sys.version_info,
) -> str | None:
    """Return a remediation message when the active Python is unsupported."""
    current = (version_info[0], version_info[1])
    if SUPPORTED_PYTHON_MIN <= current < SUPPORTED_PYTHON_MAX_EXCLUSIVE:
        return None

    return (
        "EphemeralDaddy source installs currently support CPython "
        f"{SUPPORTED_PYTHON_LABEL}. You are running Python {_version_label(version_info)}. "
        "On Windows, pyswisseph publishes prebuilt wheels for Python 3.11; newer "
        "Python versions can make pip fall back to compiling Swiss Ephemeris and "
        "fail with 'Microsoft Visual C++ 14.0 or greater is required'. Install "
        "64-bit Python 3.11, then recreate the virtual environment from the repo root:\n\n"
        "  py -3.11 -m venv venv\n"
        "  .\\venv\\Scripts\\Activate.ps1\n"
        "  python -m pip install --upgrade pip wheel setuptools\n"
        "  python -m pip install -r requirements.txt\n"
        "  python -m ephemeraldaddy.gui.bootstrap\n\n"
        "If you intentionally want to use another Python version, install the "
        "Microsoft C++ Build Tools first so pyswisseph can compile from source."
    )


def ensure_supported_python() -> None:
    """Raise a clear error before importing compiled GUI/ephemeris dependencies."""
    message = python_compatibility_message()
    if message is not None:
        raise RuntimeError(message)
