"""Human Design supplement support for the legacy humdes_gates.json plugin."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ephemeraldaddy.analysis import plugins as plugin_runtime

# Compatibility exports for callers that predate the generic plugin runtime.
RECOGNIZED_PLUGIN_FILENAMES = plugin_runtime.RECOGNIZED_PLUGIN_FILENAMES
PLUGIN_DIR = plugin_runtime.PLUGIN_DIR
DISABLED_PLUGIN_DIR = plugin_runtime.DISABLED_PLUGIN_DIR
HUMDES_GATES_PATH = PLUGIN_DIR / "humdes_gates.json"
recognized_plugin_names = plugin_runtime.recognized_plugin_names
installed_plugin_names = plugin_runtime.installed_plugin_names
plugin_installations = plugin_runtime.plugin_installations
set_plugin_enabled = plugin_runtime.set_plugin_enabled
validate_plugin_file = plugin_runtime.validate_plugin_file
install_plugin_file = plugin_runtime.install_plugin_file

_OPTIONAL_GATE_KEYS = {"app_summary", "source_ref"}
_REQUIRED_GATE_KEYS = {"gate", "source_name", "app_name", "source_summary", "lines"}
_REQUIRED_LINE_KEYS = {"id", "gate", "line", "source_name", "app_name"}


def _clean_text(value: Any) -> str:
    return str(value or "").replace("\\n", "\n").strip()


def _validate_humdes_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Plugin JSON must contain an object at the top level.")
    gates = payload.get("gates")
    if not isinstance(gates, dict) or not gates:
        raise ValueError("Plugin JSON must contain a non-empty 'gates' object.")

    normalized_payload = dict(payload)
    normalized_gates: dict[str, Any] = {}
    for gate_key, gate_data in gates.items():
        if not isinstance(gate_data, dict):
            raise ValueError(f"Gate {gate_key} must be an object.")
        missing = _REQUIRED_GATE_KEYS - set(gate_data.keys()) - _OPTIONAL_GATE_KEYS
        if missing:
            raise ValueError(f"Gate {gate_key} is missing required fields: {', '.join(sorted(missing))}.")
        try:
            gate_number = int(gate_data.get("gate", gate_key))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Gate {gate_key} has an invalid gate number.") from exc
        if not 1 <= gate_number <= 64:
            raise ValueError(f"Gate {gate_key} must be between 1 and 64.")
        canonical_gate_key = str(gate_number)
        if canonical_gate_key in normalized_gates:
            raise ValueError(f"Gate {canonical_gate_key} appears more than once in plugin data.")

        normalized_gate_data = dict(gate_data)
        normalized_gate_data["gate"] = gate_number
        lines = gate_data.get("lines", {})
        if not isinstance(lines, dict):
            raise ValueError(f"Gate {gate_key} lines must be an object.")
        normalized_lines: dict[str, Any] = {}
        for line_key, line_data in lines.items():
            if not isinstance(line_data, dict):
                raise ValueError(f"Gate {gate_key} line {line_key} must be an object.")
            missing_line = _REQUIRED_LINE_KEYS - set(line_data.keys())
            if missing_line:
                raise ValueError(
                    f"Gate {gate_key} line {line_key} is missing required fields: "
                    f"{', '.join(sorted(missing_line))}."
                )
            try:
                line_number = int(line_data.get("line", line_key))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Gate {gate_key} line {line_key} has an invalid line number.") from exc
            if not 1 <= line_number <= 6:
                raise ValueError(f"Gate {gate_key} line {line_key} must be between 1 and 6.")
            canonical_line_key = str(line_number)
            if canonical_line_key in normalized_lines:
                raise ValueError(
                    f"Gate {canonical_gate_key} line {canonical_line_key} appears more than once in plugin data."
                )
            normalized_line_data = dict(line_data)
            normalized_line_data["gate"] = gate_number
            normalized_line_data["line"] = line_number
            normalized_lines[canonical_line_key] = normalized_line_data
        normalized_gate_data["lines"] = normalized_lines
        normalized_gates[canonical_gate_key] = normalized_gate_data
    normalized_payload["gates"] = normalized_gates
    return normalized_payload


def _load_humdes_path(plugin_path: Path) -> dict[str, Any] | None:
    if not plugin_path.exists():
        return None
    try:
        with plugin_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return _validate_humdes_payload(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


@lru_cache(maxsize=8)
def _load_default_humdes_gates(revision: int) -> dict[str, Any] | None:
    del revision  # The cache key is intentionally the plugin-state revision.
    return _load_humdes_path(plugin_runtime.PLUGIN_DIR / "humdes_gates.json")


def load_humdes_gates(path: str | Path | None = None) -> dict[str, Any] | None:
    """Load validated HD supplement data; default installed data is revision-cached."""
    if path is not None:
        return _load_humdes_path(Path(path))
    return _load_default_humdes_gates(plugin_runtime.plugin_revision())


_FIXING_HEADER_PATTERN = re.compile(
    r"(?m)^.*?(?:\b(?:in\s+)?exalt(?:ed|ation)\b|\bin\s+detriment\b).*?$",
    flags=re.IGNORECASE,
)


def _fixing_header_matches(text: str, keyword: str) -> list[re.Match[str]]:
    return [
        match
        for match in _FIXING_HEADER_PATTERN.finditer(text)
        if re.search(keyword, match.group(0), flags=re.IGNORECASE)
    ]


def _trim_line_fixing_text(text: str, fixing: str | None, body: str | None = None) -> str:
    """Keep only the relevant lead-in/exaltation/detriment part of plugin line text."""
    clean = _clean_text(text)
    if not clean:
        return ""
    if fixing not in {"exaltation", "detriment"}:
        parts = clean.split("\n")
        return "\n".join(parts[:2]).strip() if len(parts) >= 2 else clean

    detriment_headers = _fixing_header_matches(clean, r"\bin\s+detriment\b")
    if fixing == "exaltation":
        if detriment_headers:
            return clean[: detriment_headers[0].start()].strip()
        return clean

    if not detriment_headers:
        return clean
    exaltation_headers = _fixing_header_matches(clean, r"\b(?:in\s+)?exalt(?:ed|ation)\b")
    lead_end = exaltation_headers[0].start() if exaltation_headers else detriment_headers[0].start()
    lead = clean[:lead_end].strip()
    detriment = clean[detriment_headers[0].start() :].strip()
    return f"{lead}\n{detriment}".strip() if lead else detriment


def humdes_gate_line_supplement_lines(
    gate: int,
    line: int | None = None,
    fixing: str | None = None,
    fixing_body: str | None = None,
) -> list[str]:
    payload = load_humdes_gates()
    if not payload:
        return []
    gates = payload.get("gates", {})
    gate_data = gates.get(str(int(gate)))
    if not isinstance(gate_data, dict):
        return []

    lines: list[str] = ["<strong>Advanced plugin supplement:</strong>"]
    source_name = _clean_text(gate_data.get("app_name")) or _clean_text(gate_data.get("source_name"))
    if source_name:
        lines.append(f"• <strong>Gate:</strong> {source_name}")
    summary = _clean_text(gate_data.get("app_summary")) or _clean_text(gate_data.get("source_summary"))
    if summary:
        lines.append(f"• <strong>Gate summary:</strong> {summary}")
    for key, label in (
        ("center", "Center"),
        ("circuit", "Circuit"),
        ("quarter", "Quarter"),
        ("channel", "Channel"),
        ("deity", "Deity"),
        ("physiology", "Physiology"),
    ):
        value = _clean_text(gate_data.get(key))
        if value:
            lines.append(f"• <strong>{label}:</strong> {value}")
    notes = gate_data.get("additional_notes", [])
    if isinstance(notes, list):
        clean_notes = [_clean_text(note) for note in notes if _clean_text(note)]
        if clean_notes:
            lines.append(f"• <strong>Additional notes:</strong> {', '.join(clean_notes)}")

    if line is not None:
        line_data = gate_data.get("lines", {}).get(str(int(line)))
        if isinstance(line_data, dict):
            raw_line_name = _clean_text(line_data.get("app_name")) or _clean_text(line_data.get("source_name"))
            line_name = _trim_line_fixing_text(raw_line_name, fixing, fixing_body)
            if line_name:
                lines.extend(["", f"<strong>Advanced line {int(line)} supplement:</strong>", line_name])
    return lines
