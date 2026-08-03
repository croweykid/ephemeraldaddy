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


def test_database_analytics_popout_info_uses_focused_standard_template():
    html = _FakeAnalytics()._build_database_analytics_popout_info_html(
        chart_title="Dominant Signs",
        label="Aries",
        value=0.12,
    )

    assert f'color:{SIGN_COLORS["Aries"]}' in html
    assert f'<b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Associated charts:</b>' in html
    assert "Database deviation: unavailable" in html
    assert "Category:" not in html
    assert "What this measures:" not in html
    assert "Where it appears:" not in html
    assert "Bar reading:" not in html


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
    assert f'color:{MODE_COLORS["cardinal"]}' in mode_html
    assert f'color:{NAKSHATRA_PLANET_COLOR["Ashwini"][1]}' in nakshatra_html

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


def test_database_analytics_popout_info_always_uses_database_template():
    analytics = _FakeAnalyticsWithOwner()

    assert "Associated charts:" in analytics._build_database_analytics_popout_info_html(
        chart_title="Dominant Bodies", label="Venus", value=1.0
    )
    assert "Associated charts:" in analytics._build_database_analytics_popout_info_html(
        chart_title="Dominant Signs", label="Aries", value=1.0
    )
    assert "Associated charts:" in analytics._build_database_analytics_popout_info_html(
        chart_title="Dominant Houses", label="House 7", value=1.0
    )
    assert "Associated charts:" in analytics._build_database_analytics_popout_info_html(
        chart_title="Nakshatras", label="Ashwini", value=1.0
    )


def test_database_analytics_enneagram_preserves_specific_popout_details():
    result = _FakeAnalytics()._build_database_analytics_popout_info_html(
        chart_title="Enneagram Predictions",
        label="Type 2",
        value=1.0,
    )

    assert "Associated charts:" in result
    assert "Enneagram Type 2" in result
    assert "Motivation:" in result


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

    title_index = html.index("Creative Spark")
    description_index = html.index("<p><i>Finds patterns in unusual places.</i></p>")
    associated_index = html.index("Associated charts:")
    assert title_index < description_index < associated_index


def test_birthday_popout_lists_uid_links_and_database_deviation():
    class Chart:
        chart_uid = "UID-123"
        name = "Ada Lovelace"
        birth_month = 12
        birth_day = 10
        dt = None

    class BirthdayAnalytics(_FakeAnalytics):
        _analysis_chart_export_rows = {
            "birth_month": [("12-10", 2, 3, 0, 2, 3, 0, 0.1, 1.75)]
        }

        def _selected_chart_uids(self):
            return ["UID-123"]

        def _get_chart_for_filter_by_uid(self, chart_uid):
            assert chart_uid == "UID-123"
            return Chart()

    result = BirthdayAnalytics()._build_database_analytics_popout_info_html(
        chart_title="Birthday",
        label="12-10",
        value=0.2,
        chart_key="birth_month",
        bar_color="#123456",
    )

    assert '<h3 style="color:#123456' in result
    assert '<a href="chart:UID-123">Ada Lovelace</a>' in result
    assert "1.75 standard deviations above the database norm" in result
