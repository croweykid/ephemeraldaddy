from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SimilarityInputState:
    selected_chart_uids: list[str]
    first_checked: bool
    second_checked: bool
    first_input_value: str
    second_input_value: str


@dataclass(frozen=True)
class SimilarityPairResolution:
    first_chart_uid: str | None
    second_chart_uid: str | None
    guidance: str | None
    allow_click: bool


def build_chart_lookup(
    rows: list[tuple], chart_uids_by_local_row: Mapping[int, str]
) -> tuple[dict[str, str], list[str]]:
    lookup: dict[str, str] = {}
    labels: list[str] = []
    for row in rows:
        local_row_id, name, alias, *_rest = row
        chart_uid = chart_uids_by_local_row.get(int(local_row_id))
        if not chart_uid:
            continue
        display_name = (
            name.strip()
            if isinstance(name, str) and name.strip()
            else "Unnamed Chart"
        )
        if alias:
            display_name = f"{display_name} ({alias})"
        from_whence = str(row[3] or "").strip() if len(row) > 3 else ""
        if from_whence:
            display_name = f"{display_name} ({from_whence})"
        lookup[display_name] = chart_uid
        labels.append(display_name)
    return lookup, labels


def resolve_chart_uid(raw_value: str, chart_lookup: dict[str, str]) -> str | None:
    query = raw_value.strip()
    if not query:
        return None
    chart_uid = chart_lookup.get(query)
    if chart_uid is not None:
        return chart_uid
    for label, candidate_uid in chart_lookup.items():
        if query.casefold() == label.casefold():
            return candidate_uid
    return None


def resolve_similarity_pair_targets(
    input_state: SimilarityInputState,
    chart_lookup: dict[str, str],
) -> SimilarityPairResolution:
    selected_chart_uids = input_state.selected_chart_uids
    first_input_uid = (
        resolve_chart_uid(input_state.first_input_value, chart_lookup)
        if input_state.first_checked
        else None
    )
    second_input_uid = (
        resolve_chart_uid(input_state.second_input_value, chart_lookup)
        if input_state.second_checked
        else None
    )

    if not input_state.first_checked and not input_state.second_checked:
        if len(selected_chart_uids) == 2:
            return SimilarityPairResolution(
                first_chart_uid=selected_chart_uids[0],
                second_chart_uid=selected_chart_uids[1],
                guidance=None,
                allow_click=True,
            )
        return SimilarityPairResolution(None, None, "Select charts to compare.", False)

    if input_state.first_checked and input_state.second_checked:
        if first_input_uid is None or second_input_uid is None:
            return SimilarityPairResolution(
                None, None, "Ticked inputs must reference saved charts.", True
            )
        if first_input_uid == second_input_uid:
            return SimilarityPairResolution(None, None, "Choose charts to compare.", True)
        return SimilarityPairResolution(first_input_uid, second_input_uid, None, True)

    checked_input_uid = first_input_uid if input_state.first_checked else second_input_uid
    if checked_input_uid is None:
        return SimilarityPairResolution(
            None,
            None,
            "Enter a saved chart name for the checked input, or select chart(s) from Database.",
            True,
        )
    if len(selected_chart_uids) != 1:
        return SimilarityPairResolution(
            None,
            None,
            "Select exactly 1 additional chart when using one checked input.",
            False,
        )
    selected_chart_uid = selected_chart_uids[0]
    if checked_input_uid == selected_chart_uid:
        return SimilarityPairResolution(None, None, "Choose charts to compare.", True)
    return SimilarityPairResolution(checked_input_uid, selected_chart_uid, None, True)


def similarity_breakdown_chart_uids(
    resolution: SimilarityPairResolution,
) -> list[str] | None:
    """Return the stable chart UIDs for a resolved pair-analysis breakdown."""
    if resolution.first_chart_uid is None or resolution.second_chart_uid is None:
        return None
    return [resolution.first_chart_uid, resolution.second_chart_uid]
