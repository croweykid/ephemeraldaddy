"""Shared packaged-icon lookup helpers."""

from pathlib import Path


def get_share_icon_path() -> str | None:
    icon_path = Path(__file__).resolve().parents[1] / "graphics" / "share_icon2.png"
    return str(icon_path) if icon_path.exists() else None
