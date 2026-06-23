from ephemeraldaddy.core.interpretations import (
    ELEMENT_COLORS,
    MODE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    SIGN_COLORS,
)
from ephemeraldaddy.gui.features.charts.database_analytics import (
    DatabaseAnalyticsChartsMixin,
)
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR


class _FakeAnalytics(DatabaseAnalyticsChartsMixin):
    def _standard_deviation_indicators_visible(self) -> bool:
        return False


def test_database_analytics_popout_info_colors_signs_and_highlighted_subheaders():
    html = _FakeAnalytics()._build_database_analytics_popout_info_html(
        chart_title="Dominant Signs",
        label="Aries",
        value=0.12,
    )

    assert f'color:{SIGN_COLORS["Aries"]}' in html
    assert f'<b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Category:</b>' in html
    assert "Zodiac sign" in html
    assert "What this measures:" in html
    assert "Where it appears:" in html


def test_database_analytics_popout_info_colors_elements_modes_and_nakshatras():
    analytics = _FakeAnalytics()

    element_html = analytics._build_database_analytics_popout_info_html(
        chart_title="Elements",
        label="Fire",
        value=None,
    )
    mode_html = analytics._build_database_analytics_popout_info_html(
        chart_title="Modes",
        label="Cardinal",
        value=None,
    )
    nakshatra_html = analytics._build_database_analytics_popout_info_html(
        chart_title="Nakshatras",
        label="Ashwini",
        value=None,
    )

    assert f'color:{ELEMENT_COLORS["Fire"]}' in element_html
    assert "Element" in element_html
    assert f'color:{MODE_COLORS["cardinal"]}' in mode_html
    assert "Mode / modality" in mode_html
    assert f'color:{NAKSHATRA_PLANET_COLOR["Ashwini"][1]}' in nakshatra_html
    assert "Nakshatra" in nakshatra_html
