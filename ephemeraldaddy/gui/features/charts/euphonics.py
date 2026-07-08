"""Euphonics rendering helpers for Chart View's ABC panel."""

from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


_EUPHONICS_PATH = Path(__file__).resolve().parents[3] / "analysis" / "euphonics.json"
_TRAILING_COMMA_RE = re.compile(r",(?=\s*[}\]])")


def _load_lenient_json(path: Path) -> Any:
    """Load the bundled JSON-like euphonics data, tolerating trailing commas."""
    return json.loads(_TRAILING_COMMA_RE.sub("", path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def euphonics_entries() -> list[dict[str, Any]]:
    """Return normalized euphonics entries from the bundled analysis data."""
    try:
        raw_entries = _load_lenient_json(_EUPHONICS_PATH)
    except Exception:
        return []
    if not isinstance(raw_entries, list):
        return []
    entries: list[dict[str, Any]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            continue
        tokens = _entry_tokens(raw_entry)
        if not tokens:
            continue
        entries.append({**raw_entry, "_tokens": tokens})
    entries.sort(key=lambda entry: max(len(token) for token in entry["_tokens"]), reverse=True)
    return entries


def _entry_tokens(entry: dict[str, Any]) -> set[str]:
    values: list[Any] = [entry.get("id"), entry.get("letterGroup")]
    for key in ("syllable", "examples"):
        raw_values = entry.get(key)
        if isinstance(raw_values, list):
            values.extend(raw_values)
        else:
            values.append(raw_values)
    tokens: set[str] = set()
    for value in values:
        token = re.sub(r"[^a-z]", "", str(value or "").lower())
        if token:
            tokens.add(token)
    return tokens


def _token_positions(normalized_name: str, token: str) -> list[int]:
    """Return overlapping occurrence positions for a euphonics token."""
    if not token:
        return []
    return [
        match.start()
        for match in re.finditer(f"(?={re.escape(token)})", normalized_name)
    ]


def _sound_color(sound_id: str) -> str:
    """Assign a stable high-contrast color to each euphonics sound."""
    palette = (
        "#ff8fa3",
        "#ffd166",
        "#8ee6a8",
        "#72ddf7",
        "#a78bfa",
        "#f0a6ff",
        "#ffb86c",
        "#7dd3fc",
        "#c4f1be",
        "#fca5a5",
        "#b5e48c",
        "#f9a8d4",
    )
    index = sum(ord(character) for character in str(sound_id or "")) % len(palette)
    return palette[index]


def euphonics_matches_for_name(name: str) -> list[dict[str, str | int]]:
    """Match euphonics entries present in a chart name, sorted by frequency then appearance."""
    normalized_name = re.sub(r"[^a-z]", "", str(name or "").lower())
    if not normalized_name:
        return []
    matches: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for entry in euphonics_entries():
        token_positions = [
            (token, positions)
            for token in entry["_tokens"]
            if token and (positions := _token_positions(normalized_name, token))
        ]
        if not token_positions:
            continue
        matched_token, positions = max(
            token_positions,
            key=lambda token_and_positions: (
                len(token_and_positions[1]),
                -token_and_positions[1][0],
                len(token_and_positions[0]),
            ),
        )
        entry_id = str(entry.get("id") or entry.get("letterGroup") or matched_token).strip()
        if entry_id in seen:
            continue
        seen.add(entry_id)
        matches.append(
            {
                "id": entry_id,
                "title": str(entry.get("title") or entry_id).strip(),
                "summary": str(entry.get("summary") or "No summary available.").strip(),
                "matched_token": matched_token.upper(),
                "occurrences": len(positions),
                "first_index": positions[0],
                "color": _sound_color(entry_id),
            }
        )
    matches.sort(key=lambda match: (-int(match["occurrences"]), int(match["first_index"])))
    return matches


def render_euphonics_html(name: str) -> str:
    """Render chart-name euphonics as a compact bulleted HTML list."""
    display_name = str(name or "").strip()
    if not display_name:
        return "No chart name available for Euphonics."
    matches = euphonics_matches_for_name(display_name)
    if not matches:
        return f"No Euphonics meanings found for <b>{html.escape(display_name)}</b>."
    items = []
    for match in matches:
        label = html.escape(str(match["id"]))
        token = html.escape(str(match["matched_token"]))
        title = html.escape(str(match["title"]))
        summary = html.escape(str(match["summary"]))
        occurrences = int(match["occurrences"])
        color = html.escape(str(match["color"]))
        items.append(
            "<li>"
            f"<span style='color:{color};'><b>{label}</b></span> "
            f"<span style='color:#9bd3ff;'>(found: {token} x {occurrences})</span>: "
            f"<span style='color:{color};'>{title}<br>{summary}</span>"
            "</li>"
        )
    return f"<div>Euphonics for <b>{html.escape(display_name)}</b>:</div><ul>{''.join(items)}</ul>"
