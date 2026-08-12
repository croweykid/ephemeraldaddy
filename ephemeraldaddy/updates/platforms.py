"""Platform selection kept separate from update transport and Qt UI."""

from __future__ import annotations

import platform
import sys


def current_platform_key() -> str:
    """Return the manifest artifact key for the running application."""

    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    if sys.platform == "win32":
        return f"windows-{architecture}"
    if sys.platform == "darwin":
        return "macos-universal"
    if sys.platform.startswith("linux"):
        return f"linux-{architecture}"
    return f"{sys.platform}-{architecture}"

