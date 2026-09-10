from __future__ import annotations

from types import SimpleNamespace

import pytest

from ephemeraldaddy.gui.features.transits import personal_timeline_window as timeline


def test_database_selection_uid_is_authoritative() -> None:
    owner = SimpleNamespace(
        _selected_chart_uids=lambda: ["abc12345def67890"],
        _latest_chart=SimpleNamespace(chart_uid="SHOULDNOTWIN1234"),
    )

    assert timeline._selected_chart_uid_for_owner(owner) == "ABC12345DEF67890"


def test_database_selection_requires_exactly_one_uid() -> None:
    owner = SimpleNamespace(
        _selected_chart_uids=lambda: ["AAAAAAAABBBBBBBB", "CCCCCCCCDDDDDDDD"]
    )

    with pytest.raises(timeline.PersonalTimelineSelectionError):
        timeline._selected_chart_uid_for_owner(owner)
