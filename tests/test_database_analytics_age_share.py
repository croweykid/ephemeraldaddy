import pytest
from matplotlib.figure import Figure

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from ephemeraldaddy.gui.features.charts.database_analytics import (
    DatabaseAnalyticsChartsMixin,
)


class _FakeAnalytics(DatabaseAnalyticsChartsMixin):
    pass


def test_tiny_selection_share_gets_a_visible_axis_and_precise_labels():
    analytics = _FakeAnalytics()
    share = 1 / 333
    ax = Figure().subplots()

    axis_max = analytics._configure_selection_share_axis(ax, [share])

    assert axis_max > share
    assert axis_max < 0.01
    assert len(set(tick.get_text() for tick in ax.get_xticklabels())) == 5
    assert (
        analytics._format_selection_database_count_label(
            "Baby Boomers", 333, 1, True
        )
        == "(1 of 333 : 0.30%) Baby Boomers"
    )
