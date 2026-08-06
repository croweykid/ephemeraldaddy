from ephemeraldaddy.core.interpretations import (
    ELEMENT_COLORS,
    MODE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    SIGN_COLORS,
    RELATIONSHIP_TYPE_MEANINGS,
    SENTIMENT_MEANINGS,
)
from ephemeraldaddy.gui.features.charts.database_analytics import (
    DatabaseAnalyticsChartsMixin,
)
from ephemeraldaddy.gui.features.database_view.analytics.popout_chart_info import (
    DatabaseAnalyticsChartInfoTarget,
    combine_database_analytics_chart_info_html,
    database_analytics_generic_reference_html,
    database_analytics_chart_info_target,
    generic_database_analytics_chart_context,
)
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR


class _FakeAnalytics(DatabaseAnalyticsChartsMixin):
    def _standard_deviation_indicators_visible(self) -> bool:
        return False


def test_astro_popout_labels_route_to_generic_chart_info_topics():
    cases = [
        ({"chart_title": "Sun Sign", "label": "Aries"}, ("sign", "Aries")),
        ({"chart_title": "Dominant Bodies", "label": "Venus"}, ("planet", "Venus")),
        ({"chart_title": "Houses", "label": "House 7"}, ("house", "7")),
        ({"chart_title": "Nakshatras", "label": "Ashwini"}, ("nakshatra", "Ashwini")),
        ({"chart_title": "Elements", "label": "Fire"}, ("element", "Fire")),
        ({"chart_title": "Modes", "label": "Cardinal"}, ("mode", "Cardinal")),
    ]
    for arguments, expected in cases:
        target = database_analytics_chart_info_target(**arguments)
        assert target == DatabaseAnalyticsChartInfoTarget(*expected)


def test_human_design_popout_modes_disambiguate_every_graph_family():
    cases = [
        ("hd_gates", "12", ("gate", "12")),
        ("hd_lines", "4", ("hd-line", "4")),
        ("hd_channels", "12-22", ("hd-channel", "12-22")),
        ("hd_defined_centers", "Sacral", ("hd-center", "Sacral")),
        ("hd_types", "MF Generator", ("hd-property:type", "Manifesting Generator")),
        ("hd_profiles", "1/3", ("hd-property:profile", "1/3")),
        ("hd_authorities", "Sacral", ("hd-property:authority", "Sacral")),
        (
            "hd_incarnation_crosses",
            "Right Angle Cross of Eden",
            ("hd-property:incarnation_cross", "Right Angle Cross of Eden"),
        ),
    ]
    for mode, label, expected in cases:
        target = database_analytics_chart_info_target(
            chart_title="Human Design", label=label, chart_mode=mode
        )
        assert target == DatabaseAnalyticsChartInfoTarget(*expected)


def test_database_summary_precedes_generic_chart_info():
    combined = combine_database_analytics_chart_info_html(
        "<h3>Aries</h3><p>Associated charts: Ada</p>",
        "<h3>Aries reference</h3><p>At Best: courageous</p>",
    )

    assert combined.index("Associated charts") < combined.index("<hr>")
    assert combined.index("<hr>") < combined.index("Aries reference")


def test_generic_reference_omits_duplicate_factor_and_chart_placement_fallback():
    generic = (
        "<h3>Libra</h3><p>No chart placements in Libra</p>"
        "<p><b>At Best:</b></p><ul><li>elegant</li></ul>"
    )

    rendered = database_analytics_generic_reference_html(
        generic,
        factor_name="Libra",
    )

    assert "No chart placements" not in rendered
    assert rendered.count("Libra") == 0
    assert "At Best:" in rendered
    assert "elegant" in rendered


def test_generic_reference_keeps_first_content_block_when_it_is_not_a_heading():
    rendered = database_analytics_generic_reference_html(
        "<p><b>At Best:</b></p><ul><li>strategic</li></ul>",
        factor_name="Libra",
    )

    assert "At Best:" in rendered
    assert "strategic" in rendered


def test_generic_reference_omits_expanded_house_heading():
    rendered = database_analytics_generic_reference_html(
        "<h3>House 7</h3><p>Partnership and one-to-one bonds.</p>",
        factor_name="7",
        factor_kind="house",
    )

    assert "House 7" not in rendered
    assert "Partnership and one-to-one bonds." in rendered


def test_observations_popout_info_adds_centralized_meaning_subheader():
    analytics = _FakeAnalytics()

    sentiment_html = analytics._build_database_analytics_popout_info_html(
        chart_title="Sentiment Prevalence", label="trust", value=0.5
    )
    relationship_html = analytics._build_database_analytics_popout_info_html(
        chart_title="Relationship Prevalence", label="mentor", value=0.5
    )

    for rendered, label, meaning in (
        (sentiment_html, "trust", SENTIMENT_MEANINGS["trust"]),
        (relationship_html, "mentor", RELATIONSHIP_TYPE_MEANINGS["mentor"]),
    ):
        assert rendered.index(label) < rendered.index(f"Meaning: {meaning}")
        assert rendered.index(f"Meaning: {meaning}") < rendered.index("Associated charts:")
        assert "font-style: italic" in rendered
        assert "color: #b8b8b8" in rendered


def test_generic_database_info_suppresses_and_restores_active_chart_context():
    active_chart = object()
    owner = type("Owner", (), {"_latest_chart": active_chart})()

    with generic_database_analytics_chart_context(owner):
        assert owner._latest_chart is None

    assert owner._latest_chart is active_chart


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


def test_associated_chart_matching_supports_common_analytics_keys(monkeypatch):
    class Chart:
        chart_uid = "UID-ALL"
        name = "Included Person"
        sentiments = ["trusted"]
        relationship_types = ["Friend"]
        tags = ["Important"]
        gender = "F"
        positions = {"Sun": 5.0}
        birth_month = 1
        birth_day = 2

    class Analytics(_FakeAnalytics):
        _sign_distribution_mode = "Sun"
        _human_design_mode = "hd_gates"
        _prevalence_mode = "sign_prevalence"
        _dominant_factors_mode = "top3_signs"

        def _selected_chart_uids(self):
            return ["UID-ALL"]

        def _get_chart_for_filter_by_uid(self, _chart_uid):
            return Chart()

        def _normalize_gender_value(self, value):
            return value

        def _split_tag_category(self, tag):
            return "Uncategorized", tag

        def _is_placeholder_chart(self, _chart):
            return False

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics._calculate_dominant_sign_weights",
        lambda _chart: {"Aries": 10.0, "Taurus": 1.0},
    )
    analytics = Analytics()

    cases = [
        ("sentiment_prevalence", "trusted", None),
        ("relationship_prevalence", "Friend", None),
        ("tag_distribution", "Important", None),
        ("gender", "F", "actual_gender"),
        ("sign_prevalence", "Aries", "sign_prevalence"),
        ("dominant_signs", "Aries", "top3_signs"),
        ("traits_distribution", "Any computed trait", "trait_predictions"),
        ("birth_month", "01-02", "birthday_distribution"),
    ]
    for chart_key, label, chart_mode in cases:
        assert analytics._analysis_matching_charts(
            chart_key,
            label,
            chart_mode=chart_mode,
        ) == [("UID-ALL", "Included Person")]


def test_associated_chart_matching_uses_frozen_popout_mode():
    class Chart:
        chart_uid = "UID-MODE"
        name = "Gate Holder"

    class Analytics(_FakeAnalytics):
        _human_design_mode = "hd_types"

        def _selected_chart_uids(self):
            return ["UID-MODE"]

        def _get_chart_for_filter_by_uid(self, _chart_uid):
            return Chart()

        def _extract_human_design_profile(self, _chart):
            return [12], [], [], [], "Generator", "Sacral"

    assert Analytics()._analysis_matching_charts(
        "human_design",
        "12",
        chart_mode="hd_gates",
    ) == [("UID-MODE", "Gate Holder")]


def test_associated_chart_matching_can_use_database_population_when_none_selected():
    class Chart:
        def __init__(self, uid, name):
            self.chart_uid = uid
            self.name = name

    charts = {
        "UID-RONALDO": Chart("UID-RONALDO", "Cristiano Ronaldo"),
        "UID-OTHER": Chart("UID-OTHER", "Ada Lovelace"),
    }

    class Analytics(_FakeAnalytics):
        def _selected_chart_uids(self):
            return []

        def _get_chart_for_filter_by_uid(self, chart_uid):
            return charts[chart_uid]

    html = Analytics()._build_database_analytics_popout_info_html(
        chart_title="Names",
        label="Ronaldo",
        value=1.0,
        chart_key="name_distribution",
        chart_uids=charts,
    )

    assert '<a href="chart:UID-RONALDO">Cristiano Ronaldo</a>' in html
    assert "Ada Lovelace" not in html


def test_dominant_house_matching_preserves_label_for_multiple_charts(monkeypatch):
    class Chart:
        def __init__(self, uid):
            self.chart_uid = uid
            self.name = uid

    class Analytics(_FakeAnalytics):
        def _selected_chart_uids(self):
            return ["UID-1", "UID-2"]

        def _get_chart_for_filter_by_uid(self, chart_uid):
            return Chart(chart_uid)

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics._calculate_dominant_house_weights",
        lambda _chart: {7: 10.0},
    )

    assert Analytics()._analysis_matching_charts(
        "dominant_signs",
        "House 7",
        chart_mode="top3_houses",
    ) == [("UID-1", "UID-1"), ("UID-2", "UID-2")]


def test_house_prevalence_matching_uses_prevalence_counts(monkeypatch):
    class Chart:
        chart_uid = "UID-HOUSE"
        name = "House Contributor"
        positions = {}

    class Analytics(_FakeAnalytics):
        def _selected_chart_uids(self):
            return ["UID-HOUSE"]

        def _get_chart_for_filter_by_uid(self, _chart_uid):
            return Chart()

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics._calculate_house_prevalence_counts",
        lambda _chart: {4: 1.0},
    )
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics._calculate_dominant_house_weights",
        lambda _chart: {5: 99.0},
    )

    analytics = Analytics()
    assert analytics._analysis_matching_charts(
        "sign_prevalence", "4", chart_mode="house_prevalence"
    ) == [("UID-HOUSE", "House Contributor")]
    assert analytics._analysis_matching_charts(
        "sign_prevalence", "5", chart_mode="house_prevalence"
    ) == []


def test_species_matching_uses_ranked_family_for_selected_mode():
    class Chart:
        chart_uid = "UID-SPECIES"
        name = "Elf Chart"

    class Analytics(_FakeAnalytics):
        def _selected_chart_uids(self):
            return ["UID-SPECIES"]

        def _get_chart_for_filter_by_uid(self, _chart_uid):
            return Chart()

        def _dnd_species_class_payload_for_chart(self, _chart):
            return {"species": [{"family": "Elf"}, {"family": "Dwarf"}]}

    analytics = Analytics()
    assert analytics._analysis_matching_charts(
        "species_distribution", "Elf", chart_mode="top_species"
    ) == [("UID-SPECIES", "Elf Chart")]
    assert analytics._analysis_matching_charts(
        "species_distribution", "Dwarf", chart_mode="top_species"
    ) == []
    assert analytics._analysis_matching_charts(
        "species_distribution", "Dwarf", chart_mode="top_three_species"
    ) == [("UID-SPECIES", "Elf Chart")]
