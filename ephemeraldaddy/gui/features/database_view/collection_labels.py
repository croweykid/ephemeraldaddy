"""Presentation helpers for Database View collection labels."""

from collections.abc import Iterable


def custom_collection_label(
    name: str,
    member_chart_uids: Iterable[object],
    live_chart_uids: Iterable[object],
) -> str:
    """Format a collection label with its live, UID-resolvable member count."""

    normalized_live_uids = {
        str(chart_uid or "").strip().upper()
        for chart_uid in live_chart_uids
        if str(chart_uid or "").strip()
    }
    normalized_member_uids = {
        str(chart_uid or "").strip().upper()
        for chart_uid in member_chart_uids
        if str(chart_uid or "").strip()
    }
    return f"{name} ({len(normalized_member_uids & normalized_live_uids)})"
