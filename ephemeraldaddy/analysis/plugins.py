"""Generic local plugin discovery, installation, and hook dispatch.

The runtime deliberately keeps plugin management separate from any one analysis
feature. Legacy data-only plugins can remain registered alongside versioned
Python plugins, while hook modules are imported lazily and cached until plugin
state changes.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

PLUGIN_API_VERSION = 1
PLUGIN_DIR = Path.home() / ".ephemeraldaddy" / "plugins"
DISABLED_PLUGIN_DIR = PLUGIN_DIR / "disabled"


@dataclass(frozen=True)
class PluginSpec:
    """One plugin filename understood by this EphemeralDaddy build."""

    filename: str
    display_name: str
    plugin_type: str


PLUGIN_SPECS: tuple[PluginSpec, ...] = (
    PluginSpec(
        filename="humdes_gates.json",
        display_name="Human Design Gates-Lines Supplement",
        plugin_type="legacy_json",
    ),
    PluginSpec(
        filename="sun-moon_hot-takes.py",
        display_name="Sun-Moon Hot Takes",
        plugin_type="python",
    ),
)
RECOGNIZED_PLUGIN_FILENAMES: tuple[str, ...] = tuple(spec.filename for spec in PLUGIN_SPECS)
_PLUGIN_SPEC_BY_FILENAME = {spec.filename: spec for spec in PLUGIN_SPECS}
_plugin_revision = 0


def recognized_plugin_names() -> list[str]:
    """Return filenames accepted by the current plugin registry."""
    return list(RECOGNIZED_PLUGIN_FILENAMES)


def installed_plugin_names() -> list[str]:
    """Return recognized plugin filenames installed in either state."""
    return [
        name
        for name in RECOGNIZED_PLUGIN_FILENAMES
        if (PLUGIN_DIR / name).exists() or (DISABLED_PLUGIN_DIR / name).exists()
    ]


def plugin_installations() -> list[dict[str, Any]]:
    """Describe installed plugins without importing executable plugin code."""
    installations: list[dict[str, Any]] = []
    for name in installed_plugin_names():
        enabled_path = PLUGIN_DIR / name
        enabled = enabled_path.exists()
        path = enabled_path if enabled else DISABLED_PLUGIN_DIR / name
        spec = _PLUGIN_SPEC_BY_FILENAME[name]
        installations.append(
            {
                "name": name,
                "display_name": spec.display_name,
                "enabled": enabled,
                "path": path,
                "plugin_type": spec.plugin_type,
            }
        )
    return installations


def plugin_revision() -> int:
    """Return the in-process revision of installed/enabled plugin state."""
    return _plugin_revision


def invalidate_plugin_caches() -> None:
    """Invalidate hook-module caches after an install or state change."""
    global _plugin_revision
    _plugin_revision += 1
    _loaded_python_plugins.cache_clear()


def set_plugin_enabled(name: str, enabled: bool) -> Path:
    """Enable or disable an installed plugin while retaining its local files."""
    if name not in _PLUGIN_SPEC_BY_FILENAME:
        raise ValueError("Plugin filename is not recognized.")
    source = (DISABLED_PLUGIN_DIR if enabled else PLUGIN_DIR) / name
    destination = (PLUGIN_DIR if enabled else DISABLED_PLUGIN_DIR) / name
    if not source.exists():
        if destination.exists():
            return destination
        raise FileNotFoundError(f"Plugin is not installed: {name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination)
    invalidate_plugin_caches()
    return destination


def _python_manifest_from_source(source: str, *, filename: str) -> dict[str, Any]:
    """Read a literal PLUGIN_MANIFEST without executing plugin code."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise ValueError(f"Plugin Python could not be parsed: {exc.msg}.") from exc

    manifest_value: Any = None
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "PLUGIN_MANIFEST" for target in targets):
            continue
        value_node = node.value
        if value_node is None:
            continue
        try:
            manifest_value = ast.literal_eval(value_node)
        except (ValueError, TypeError, SyntaxError) as exc:
            raise ValueError("PLUGIN_MANIFEST must be a literal dictionary.") from exc
        break

    if not isinstance(manifest_value, dict):
        raise ValueError("Python plugins must define a literal PLUGIN_MANIFEST dictionary.")
    return dict(manifest_value)


def _validate_python_manifest(path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    try:
        api_version = int(manifest.get("api_version", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Plugin api_version must be an integer.") from exc
    if api_version != PLUGIN_API_VERSION:
        raise ValueError(
            f"Unsupported plugin api_version {api_version}; expected {PLUGIN_API_VERSION}."
        )

    name = str(manifest.get("name", "")).strip()
    if not name:
        raise ValueError("Python plugins must declare a non-empty name.")

    hooks = manifest.get("hooks", ())
    if not isinstance(hooks, (list, tuple)) or not hooks:
        raise ValueError("Python plugins must declare at least one hook.")
    normalized_hooks = tuple(str(hook).strip() for hook in hooks if str(hook).strip())
    if not normalized_hooks:
        raise ValueError("Python plugins must declare at least one valid hook.")

    data_files = manifest.get("data_files", ())
    if not isinstance(data_files, (list, tuple)):
        raise ValueError("Plugin data_files must be a list or tuple.")
    normalized_data_files: list[str] = []
    for raw_name in data_files:
        data_name = str(raw_name).strip()
        if not data_name or Path(data_name).name != data_name:
            raise ValueError("Plugin data_files must contain sibling filenames only.")
        data_path = path.parent / data_name
        if not data_path.is_file():
            raise ValueError(f"Required plugin data file is missing: {data_name}")
        normalized_data_files.append(data_name)

    normalized = dict(manifest)
    normalized["api_version"] = api_version
    normalized["name"] = name
    normalized["hooks"] = normalized_hooks
    normalized["data_files"] = tuple(normalized_data_files)
    return normalized


def python_plugin_manifest(path: str | Path) -> dict[str, Any]:
    plugin_path = Path(path)
    source = plugin_path.read_text(encoding="utf-8")
    manifest = _python_manifest_from_source(source, filename=str(plugin_path))
    return _validate_python_manifest(plugin_path, manifest)


def validate_plugin_file(path: str | Path) -> dict[str, Any]:
    """Validate a recognized plugin without importing Python plugin code."""
    plugin_path = Path(path)
    spec = _PLUGIN_SPEC_BY_FILENAME.get(plugin_path.name)
    if spec is None:
        raise ValueError("Plugin filename is not recognized.")

    if spec.plugin_type == "legacy_json":
        with plugin_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if plugin_path.name == "humdes_gates.json":
            from ephemeraldaddy.analysis.human_design_plugins import _validate_humdes_payload

            return _validate_humdes_payload(payload)
        raise ValueError("No validator is registered for this JSON plugin.")

    if spec.plugin_type == "python":
        return python_plugin_manifest(plugin_path)
    raise ValueError(f"Unsupported plugin type: {spec.plugin_type}")


def install_plugin_file(path: str | Path) -> Path:
    """Validate and install one registered plugin plus declared sibling data files."""
    source_path = Path(path)
    validation = validate_plugin_file(source_path)
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    if source_path.suffix.lower() == ".py":
        for data_name in validation.get("data_files", ()):
            source_data = source_path.parent / str(data_name)
            shutil.copyfile(source_data, PLUGIN_DIR / str(data_name))

    destination = PLUGIN_DIR / source_path.name
    shutil.copyfile(source_path, destination)
    disabled_copy = DISABLED_PLUGIN_DIR / source_path.name
    if disabled_copy.exists():
        disabled_copy.unlink()
    invalidate_plugin_caches()
    return destination


def _load_python_module(path: Path, revision: int) -> ModuleType:
    safe_stem = "".join(char if char.isalnum() else "_" for char in path.stem)
    module_name = f"_ephemeraldaddy_plugin_{safe_stem}_{revision}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for plugin: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=8)
def _loaded_python_plugins(revision: int) -> tuple[tuple[dict[str, Any], ModuleType], ...]:
    loaded: list[tuple[dict[str, Any], ModuleType]] = []
    for spec in PLUGIN_SPECS:
        if spec.plugin_type != "python":
            continue
        path = PLUGIN_DIR / spec.filename
        if not path.is_file():
            continue
        try:
            manifest = python_plugin_manifest(path)
            module = _load_python_module(path, revision)
        except (OSError, ImportError, ValueError, RuntimeError, SyntaxError):
            continue
        loaded.append((manifest, module))
    return tuple(loaded)


def _normalize_chart_info_paragraphs(value: Any) -> list[list[dict[str, Any]]]:
    """Normalize plugin chart-info output to declarative styled paragraphs."""
    if not isinstance(value, (list, tuple)):
        return []
    paragraphs: list[list[dict[str, Any]]] = []
    for raw_paragraph in value:
        if not isinstance(raw_paragraph, (list, tuple)):
            continue
        paragraph: list[dict[str, Any]] = []
        for raw_segment in raw_paragraph:
            if not isinstance(raw_segment, Mapping):
                continue
            text = str(raw_segment.get("text", ""))
            if not text:
                continue
            segment: dict[str, Any] = {"text": text}
            if raw_segment.get("bold"):
                segment["bold"] = True
            if raw_segment.get("italic"):
                segment["italic"] = True
            role = str(raw_segment.get("color_role", "")).strip()
            if role:
                segment["color_role"] = role
            paragraph.append(segment)
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def chart_info_plugin_paragraphs(context: Mapping[str, Any]) -> list[list[dict[str, Any]]]:
    """Collect Chart Info supplements from enabled plugins that register the hook."""
    collected: list[list[dict[str, Any]]] = []
    revision = plugin_revision()
    for manifest, module in _loaded_python_plugins(revision):
        if "chart_info" not in manifest.get("hooks", ()):
            continue
        handler = getattr(module, "chart_info", None)
        if not callable(handler):
            continue
        try:
            result = handler(dict(context))
        except Exception:
            # A local optional plugin must never take down Chart Editor.
            continue
        paragraphs = _normalize_chart_info_paragraphs(result)
        if not paragraphs:
            continue
        if collected:
            collected.append([{"text": ""}])
        collected.extend(paragraphs)
    return collected
