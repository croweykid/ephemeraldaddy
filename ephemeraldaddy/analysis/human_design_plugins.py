"""Local Human Design supplement plugin loading.

Plugins are user-supplied JSON files stored outside the packaged reference data.
"""
from __future__ import annotations

import json
import shutil
import re
from pathlib import Path
from typing import Any

RECOGNIZED_PLUGIN_FILENAMES: tuple[str, ...] = ("humdes_gates.json",)
PLUGIN_DIR = Path.home() / ".ephemeraldaddy" / "plugins"
HUMDES_GATES_PATH = PLUGIN_DIR / "humdes_gates.json"

_OPTIONAL_GATE_KEYS = {"app_summary", "source_ref"}
_REQUIRED_GATE_KEYS = {"gate", "source_name", "app_name", "source_summary", "lines"}
_REQUIRED_LINE_KEYS = {"id", "gate", "line", "source_name", "app_name"}


def recognized_plugin_names() -> list[str]:
    return list(RECOGNIZED_PLUGIN_FILENAMES)


def installed_plugin_names() -> list[str]:
    """Return recognized plugin filenames that are currently installed locally."""
    return [name for name in RECOGNIZED_PLUGIN_FILENAMES if (PLUGIN_DIR / name).exists()]


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


def validate_plugin_file(path: str | Path) -> dict[str, Any]:
    plugin_path = Path(path)
    if plugin_path.name not in RECOGNIZED_PLUGIN_FILENAMES:
        raise ValueError("Plugin filename is not recognized.")
    with plugin_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if plugin_path.name == "humdes_gates.json":
        return _validate_humdes_payload(payload)
    raise ValueError("Plugin filename is not recognized.")


def install_plugin_file(path: str | Path) -> Path:
    source_path = Path(path)
    validate_plugin_file(source_path)
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    destination = PLUGIN_DIR / source_path.name
    shutil.copyfile(source_path, destination)
    return destination


def load_humdes_gates(path: str | Path | None = None) -> dict[str, Any] | None:
    plugin_path = Path(path) if path is not None else HUMDES_GATES_PATH
    if not plugin_path.exists():
        return None
    try:
        return validate_plugin_file(plugin_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


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

    # Detriment: preserve the lead-in before the exaltation header, remove the
    # exaltation header/body, and keep the detriment header plus its body text.
    if not detriment_headers:
        return clean
    exaltation_headers = _fixing_header_matches(clean, r"\b(?:in\s+)?exalt(?:ed|ation)\b")
    lead_end = exaltation_headers[0].start() if exaltation_headers else detriment_headers[0].start()
    lead = clean[:lead_end].strip()
    detriment = clean[detriment_headers[0].start() :].strip()
    return f"{lead}\n{detriment}".strip() if lead else detriment


def humdes_gate_line_supplement_lines(gate: int, line: int | None = None, fixing: str | None = None, fixing_body: str | None = None) -> list[str]:
    payload = load_humdes_gates()
    if not payload:
        return []
    gates = payload.get("gates", {})
    gate_data = gates.get(str(int(gate)))
    if not isinstance(gate_data, dict):
        return []

    lines: list[str] = ["Advanced plugin supplement:"]
    source_name = _clean_text(gate_data.get("app_name")) or _clean_text(gate_data.get("source_name"))
    if source_name:
        lines.append(f"• Gate name: {source_name}")
    summary = _clean_text(gate_data.get("app_summary")) or _clean_text(gate_data.get("source_summary"))
    if summary:
        lines.append(f"• Gate summary: {summary}")
    for key, label in (("center", "Center"), ("circuit", "Circuit"), ("quarter", "Quarter"), ("channel", "Channel"), ("deity", "Deity"), ("physiology", "Physiology")):
        value = _clean_text(gate_data.get(key))
        if value:
            lines.append(f"• {label}: {value}")
    notes = gate_data.get("additional_notes", [])
    if isinstance(notes, list):
        clean_notes = [_clean_text(note) for note in notes if _clean_text(note)]
        if clean_notes:
            lines.append(f"• Additional notes: {', '.join(clean_notes)}")

    if line is not None:
        line_data = gate_data.get("lines", {}).get(str(int(line)))
        if isinstance(line_data, dict):
            raw_line_name = _clean_text(line_data.get("app_name")) or _clean_text(line_data.get("source_name"))
            line_name = _trim_line_fixing_text(raw_line_name, fixing, fixing_body)
            if line_name:
                lines.extend(["", f"Advanced line {int(line)} supplement:", line_name])
    return lines
