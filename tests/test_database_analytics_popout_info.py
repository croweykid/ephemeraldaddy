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

class _FakeChartAnalyticsOwner:
    _latest_chart = object()

    def _build_body_popout_info(self, chart, body):
        assert chart is self._latest_chart
        return f"body explainer: {body}"

    def _build_sign_popout_info(self, chart, sign):
        assert chart is self._latest_chart
        return f"sign explainer: {sign}"

    def _build_house_popout_info(self, chart, house):
        assert chart is self._latest_chart
        return f"house explainer: {house}"

    def _build_nakshatra_popout_info(self, chart, nakshatra):
        assert chart is self._latest_chart
        return f"nakshatra explainer: {nakshatra}"


class _FakeAnalyticsWithOwner(_FakeAnalytics):
    def __init__(self):
        self._app_owner = _FakeChartAnalyticsOwner()


def test_database_analytics_popout_info_reuses_chart_analytics_astro_explainers():
    analytics = _FakeAnalyticsWithOwner()

    assert analytics._build_database_analytics_popout_info_html(
        chart_title="Dominant Bodies", label="Venus", value=1.0
    ) == "body explainer: Venus"
    assert analytics._build_database_analytics_popout_info_html(
        chart_title="Dominant Signs", label="Aries", value=1.0
    ) == "sign explainer: Aries"
    assert analytics._build_database_analytics_popout_info_html(
        chart_title="Dominant Houses", label="House 7", value=1.0
    ) == "house explainer: 7"
    assert analytics._build_database_analytics_popout_info_html(
        chart_title="Nakshatras", label="Ashwini", value=1.0
    ) == "nakshatra explainer: Ashwini"


def test_database_analytics_popout_info_includes_trait_description(monkeypatch):
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics.list_traits",
        lambda active_only=False: [
            {
                "name": "Creative Spark",
                "description": "Finds patterns in unusual places.",
                "color": "#cc99ff",
                "archived": False,
            }
        ],
    )

    html = _FakeAnalytics()._build_database_analytics_popout_info_html(
        chart_title="Traits",
        label="Creative Spark",
        value=None,
    )

    assert "Description:" in html
    assert "Finds patterns in unusual places." in html
