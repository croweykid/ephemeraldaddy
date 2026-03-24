from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimilarityInputState:
    selected_chart_ids: list[int]
    first_checked: bool
    second_checked: bool
    first_input_value: str
    second_input_value: str


@dataclass(frozen=True)
class SimilarityPairResolution:
    first_chart_id: int | None
    second_chart_id: int | None
    guidance: str | None
    allow_click: bool


def build_chart_lookup(rows: list[tuple]) -> tuple[dict[str, int], list[str]]:
    lookup: dict[str, int] = {}
    labels: list[str] = []
    for row in rows:
        chart_id, name, alias, *_rest = row
        display_name = (
            name.strip()
            if isinstance(name, str) and name.strip()
            else f"Chart {chart_id}"
        )
        if alias:
            display_name = f"{display_name} ({alias})"
        label = f"{display_name}  [#{chart_id}]"
        lookup[label] = int(chart_id)
        labels.append(label)
    return lookup, labels


def resolve_chart_id(raw_value: str, chart_lookup: dict[str, int]) -> int | None:
    query = raw_value.strip()
    if not query:
        return None
    chart_id = chart_lookup.get(query)
    if chart_id is not None:
        return chart_id
    for label, candidate_id in chart_lookup.items():
        if query.lower() == label.lower():
            return candidate_id
    return None


def resolve_similarity_pair_targets(
    input_state: SimilarityInputState,
    chart_lookup: dict[str, int],
) -> SimilarityPairResolution:
    selected_chart_ids = input_state.selected_chart_ids
    first_input_id = (
        resolve_chart_id(input_state.first_input_value, chart_lookup)
        if input_state.first_checked
        else None
    )
    second_input_id = (
        resolve_chart_id(input_state.second_input_value, chart_lookup)
        if input_state.second_checked
        else None
    )

    if not input_state.first_checked and not input_state.second_checked:
        if len(selected_chart_ids) == 2:
            return SimilarityPairResolution(
                first_chart_id=selected_chart_ids[0],
                second_chart_id=selected_chart_ids[1],
                guidance=None,
                allow_click=True,
            )
        return SimilarityPairResolution(
            first_chart_id=None,
            second_chart_id=None,
            guidance="Select exactly 2 charts to compare.",
            allow_click=False,
        )

    if input_state.first_checked and input_state.second_checked:
        if first_input_id is None or second_input_id is None:
            return SimilarityPairResolution(
                first_chart_id=None,
                second_chart_id=None,
                guidance="Ticked inputs must reference saved charts.",
                allow_click=True,
            )
        if first_input_id == second_input_id:
            return SimilarityPairResolution(
                first_chart_id=None,
                second_chart_id=None,
                guidance="Choose two different charts to compare.",
                allow_click=True,
            )
        return SimilarityPairResolution(
            first_chart_id=first_input_id,
            second_chart_id=second_input_id,
            guidance=None,
            allow_click=True,
        )

    checked_input_id = first_input_id if input_state.first_checked else second_input_id
    if checked_input_id is None:
        return SimilarityPairResolution(
            first_chart_id=None,
            second_chart_id=None,
            guidance="Enter a saved chart name for the checked input, or select chart(s) from Database.",
            allow_click=True,
        )
    if len(selected_chart_ids) != 1:
        return SimilarityPairResolution(
            first_chart_id=None,
            second_chart_id=None,
            guidance="Select exactly 1 chart when using one checked input.",
            allow_click=False,
        )
    selected_chart_id = selected_chart_ids[0]
    if checked_input_id == selected_chart_id:
        return SimilarityPairResolution(
            first_chart_id=None,
            second_chart_id=None,
            guidance="Choose two different charts to compare.",
            allow_click=True,
        )
    return SimilarityPairResolution(
        first_chart_id=checked_input_id,
        second_chart_id=selected_chart_id,
        guidance=None,
        allow_click=True,
    )
