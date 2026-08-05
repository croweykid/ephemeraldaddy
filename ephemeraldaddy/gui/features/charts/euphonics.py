"""Euphonics rendering helpers for Chart View's Linguistics panel.

The surrounding right-panel route still uses the legacy ``abc`` token for
compatibility; user-facing copy should call the combined Anagrams + Euphonics
area the Linguistics panel.
"""

from __future__ import annotations

import html
import json
import random
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
    entries.sort(
        key=lambda entry: max(len(token) for token in entry["_tokens"]), reverse=True
    )
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


def _name_parts_with_offsets(name: str) -> list[tuple[str, int]]:
    """Return normalized alphabetic name parts and their starts in the joined name."""
    parts: list[tuple[str, int]] = []
    joined_offset = 0
    for match in re.finditer(r"[a-z]+", str(name or "").lower()):
        part = match.group(0)
        parts.append((part, joined_offset))
        joined_offset += len(part)
    return parts


def _token_positions(normalized_name: str, token: str) -> list[int]:
    """Return overlapping occurrence positions for a euphonics token."""
    if not token:
        return []
    return [
        match.start()
        for match in re.finditer(f"(?={re.escape(token)})", normalized_name)
    ]


def _special_y_positions(
    entry_id: str, name_parts: list[tuple[str, int]]
) -> list[int] | None:
    """Return position-restricted matches for the context-sensitive Y entries."""
    normalized_name = "".join(part for part, _offset in name_parts)
    if entry_id == "Y_INITIAL":
        return [offset for part, offset in name_parts if part.startswith("y")]
    if entry_id == "Y_FINAL":
        if normalized_name.endswith("y"):
            return [len(normalized_name) - 1]
        return []
    return None


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


def euphonics_matches_for_name(name: str) -> list[dict[str, Any]]:
    """Match euphonics entries present in a chart name, sorted by first appearance."""
    name_parts = _name_parts_with_offsets(str(name or ""))
    normalized_name = "".join(part for part, _offset in name_parts)
    if not normalized_name:
        return []
    matches: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for entry in euphonics_entries():
        entry_id = str(entry.get("id") or entry.get("letterGroup") or "").strip()
        special_positions = _special_y_positions(entry_id, name_parts)
        if special_positions is not None:
            token_positions = [("y", special_positions)] if special_positions else []
        else:
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
        entry_id = entry_id or matched_token
        if entry_id in seen:
            continue
        seen.add(entry_id)
        examples = entry.get("examples")
        matches.append(
            {
                "id": entry_id,
                "title": str(entry.get("title") or entry_id).strip(),
                "summary": str(entry.get("summary") or "No summary available.").strip(),
                "matched_token": matched_token.upper(),
                "occurrences": len(positions),
                "first_index": positions[0],
                "color": _sound_color(entry_id),
                "examples": (
                    [
                        str(example).strip()
                        for example in examples
                        if str(example).strip()
                    ]
                    if isinstance(examples, list)
                    else []
                ),
            }
        )
    matches.sort(key=lambda match: int(match["first_index"]))
    return matches


def _weighted_title_style(occurrences: int) -> str:
    """Return inline emphasis for compact Euphonics titles by frequency."""
    if occurrences > 2:
        return "font-size:18px; font-weight:700;"
    if occurrences > 1:
        return "font-size:15px; font-weight:700;"
    return "font-size:13px; font-weight:400;"


def _random_examples(examples: list[str], count: int) -> list[str]:
    """Return random examples, repeating only when the source list is too short."""
    if count <= 0 or not examples:
        return []
    if len(examples) >= count:
        return random.sample(examples, count)
    return random.choices(examples, k=count)


def render_euphonics_compact_html(name: str) -> str:
    """Render the default compact chart-name euphonics summary."""
    display_name = str(name or "").strip()
    if not display_name:
        return "No chart name available for Euphonics."
    matches = euphonics_matches_for_name(display_name)
    if not matches:
        return f"No Euphonics meanings found for <b>{html.escape(display_name)}</b>."

    title_parts: list[str] = []
    example_sections: list[str] = []
    for match in matches:
        color = html.escape(str(match["color"]))
        occurrences = int(match["occurrences"])
        title = html.escape(str(match["title"]))
        title_parts.append(
            f"<span style='color:{color}; {_weighted_title_style(occurrences)}'>{title}</span>"
        )

        examples = _random_examples(list(match.get("examples", [])), occurrences * 3)
        if examples:
            label = html.escape(str(match["id"]))
            example_text = ", ".join(html.escape(example) for example in examples)
            example_sections.append(
                f"<div style='margin:2px 0;'><span style='color:{color}; font-weight:700;'>{label}</span>: "
                f"<span style='color:{color};'>{example_text}</span></div>"
            )

    examples_html = "".join(example_sections) or "<div>No examples available.</div>"
    return (
        f"<div>Euphonics for <b>{html.escape(display_name)}</b>:</div>"
        f"<div style='line-height:1.55; margin-top:4px;'>{'. '.join(title_parts)}.</div>"
        "<hr style='border:0; border-top:1px solid rgba(255,255,255,0.25); margin:8px 0;'>"
        f"<div>{examples_html}</div>"
    )


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
