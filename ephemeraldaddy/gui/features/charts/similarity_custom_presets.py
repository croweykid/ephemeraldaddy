"""Local persistence for user-defined Astro Twin scoring presets."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping


CUSTOM_ASTRO_TWIN_PRESETS_FILENAME = "custom_astro_twin_presets"
CUSTOM_ASTRO_TWIN_PRESETS_PATH_ENV = "EPHEMERALDADDY_CUSTOM_ASTRO_TWIN_PRESETS_PATH"
_NUMBERED_CUSTOM_NAME_RE = re.compile(r"^Custom (\d+)$")


def resolve_custom_astro_twin_presets_path(
    path: str | os.PathLike[str] | None = None,
) -> Path:
    """Return the extensionless local preset-file path."""
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get(CUSTOM_ASTRO_TWIN_PRESETS_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".ephemeraldaddy" / CUSTOM_ASTRO_TWIN_PRESETS_FILENAME


def load_custom_astro_twin_presets(
    path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Load valid named preset records; absent or malformed files are empty."""
    try:
        payload = json.loads(resolve_custom_astro_twin_presets_path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records = payload.get("presets", []) if isinstance(payload, Mapping) else []
    if not isinstance(records, list):
        return []
    return [
        dict(record)
        for record in records
        if isinstance(record, Mapping)
        and str(record.get("name", "")).strip()
        and isinstance(record.get("settings"), Mapping)
    ]


def next_custom_astro_twin_preset_name(
    presets: list[Mapping[str, Any]] | None = None,
    *,
    path: str | os.PathLike[str] | None = None,
) -> str:
    """Return Custom N using one more than the greatest existing Custom N."""
    records = load_custom_astro_twin_presets(path) if presets is None else presets
    used_numbers = []
    for record in records:
        match = _NUMBERED_CUSTOM_NAME_RE.fullmatch(str(record.get("name", "")).strip())
        if match:
            used_numbers.append(int(match.group(1)))
    return f"Custom {max(used_numbers, default=0) + 1}"


def save_custom_astro_twin_preset(
    name: str,
    settings: Mapping[str, Any],
    *,
    path: str | os.PathLike[str] | None = None,
) -> Path:
    """Append a named settings snapshot using an atomic local-file replace."""
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Preset name cannot be empty.")
    preset_path = resolve_custom_astro_twin_presets_path(path)
    records = load_custom_astro_twin_presets(preset_path)
    records.append({"name": clean_name, "settings": dict(settings)})
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = preset_path.with_name(f".{preset_path.name}.tmp")
    temporary_path.write_text(
        json.dumps({"version": 1, "presets": records}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(preset_path)
    return preset_path
