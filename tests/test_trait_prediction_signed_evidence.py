from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts import trait_factor_sections
from ephemeraldaddy.gui.features.predictions import trait_factor_explanations as explanations


def _chart() -> SimpleNamespace:
    return SimpleNamespace()


def test_signed_normal_weights_partition_present_missing_and_omit_zero(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "signs": {"Libra": 5, "Aries": -4, "Gemini": 0},
        "gates": {49: 3, 12: -2, 22: 0},
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": ["Libra", "Aries", "Gate 12"], "negative": []},
    )

    assert evidence.supporting == ("Libra",)
    assert evidence.missing == ("Missing Gate 49",)
    assert evidence.inverse_present == ("Aries", "Gate 12")
    assert evidence.inverse_missing == ()
    rendered = (
        evidence.supporting
        + evidence.missing
        + evidence.inverse_present
        + evidence.inverse_missing
    )
    assert all("Gemini" not in row and "22" not in row for row in rendered)


def test_inverse_position_alternative_is_not_missing_when_same_normal_bucket_matches(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "positions": {
            "Pluto in Cancer": 3,
            "Pluto in Taurus": -7,
        }
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": ["Pluto in Cancer"], "negative": []},
    )

    assert evidence.supporting == ("Pluto in Cancer",)
    assert evidence.inverse_missing == ()


def test_cross_family_position_bucket_suppresses_missing_anti_alternative(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "positions": {"Pluto in Cancer": 3},
        "antipositions": {"Pluto in Taurus": 4},
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": ["Pluto in Cancer"], "negative": []},
    )

    assert evidence.supporting == ("Pluto in Cancer",)
    assert evidence.negative_indicators_missing == ()
    assert evidence.has_negative_definitions is True


def test_no_birth_time_house_criteria_are_unknown_not_missing_or_undefined(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "houses": {6: 3, 8: -2},
        "antihouses": {9: 4, 10: 0},
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": [], "negative": []},
    )

    assert evidence.supporting == ()
    assert evidence.missing == ()
    assert evidence.inverse_present == ()
    assert evidence.inverse_missing == ()
    assert evidence.negative_indicators_present == ()
    assert evidence.negative_indicators_missing == ()
    assert evidence.positive_unknown == ("House 6 (no BT: unknown)",)
    assert evidence.inverse_unknown == ("House 8 (no BT: unknown)",)
    assert evidence.negative_indicators_unknown == ("House 9 (no BT: unknown)",)
    assert evidence.has_negative_definitions is True


def test_anti_properties_are_negative_indicators_and_zero_is_omitted(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "antiaspects": {
            "Mars square Saturn": 9,
            "Venus trine Jupiter": -5,
            "Sun sextile Moon": 0,
        },
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": [], "negative": ["Mars square Saturn"]},
    )

    assert evidence.negative_indicators_present == ("Mars square Saturn",)
    assert evidence.negative_indicators_missing == ("Venus trine Jupiter",)
    assert evidence.counter_factors == ("Mars square Saturn",)
    assert evidence.has_negative_definitions is True
    assert all(
        "Sun sextile Moon" not in row
        for row in evidence.negative_indicators_present + evidence.negative_indicators_missing
    )


def test_counter_factors_compatibility_includes_inverse_and_anti_matches(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "signs": {"Aries": -4},
        "antiaspects": {"Mars square Saturn": 9},
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={
            "positive": ["Aries"],
            "negative": ["Mars square Saturn"],
        },
    )

    assert evidence.counter_factors == ("Aries", "Mars square Saturn")


def test_trait_factor_sections_render_exact_labels_and_negative_indicator_fallback(monkeypatch):
    fixed_evidence = explanations.TraitFactorEvidence(
        supporting=("Libra",),
        missing=("Missing Gate 49",),
        inverse_present=("Aries",),
        inverse_missing=("Missing Gate 12",),
        negative_indicators_present=(),
        negative_indicators_missing=(),
    )
    monkeypatch.setattr(
        trait_factor_sections,
        "build_trait_factor_evidence",
        lambda *_args, **_kwargs: fixed_evidence,
    )

    class Core:
        CHART_DATA_HIGHLIGHT_COLOR = "#abcdef"

        @staticmethod
        def _trait_info_html(_trait, chart=None):
            return "BASE" if chart is None else "LEGACY"

        @staticmethod
        def matched_weighted_criteria(_chart, _profile):
            return {"positive": [], "negative": []}

        @staticmethod
        def weighted_string_entries(_values):
            return {}

        @staticmethod
        def weighted_house_entries(_values):
            return {}

    trait_factor_sections.install_trait_factor_sections(Core)
    rendered = Core._trait_info_html(
        {"name": "Contrarian", "profile": {}},
        SimpleNamespace(name="Example"),
    )

    assert rendered.startswith("BASE")
    assert "LEGACY" not in rendered
    assert "Positive Supporting Indicators" in rendered
    assert "Missing Positive Indicators" in rendered
    assert "Inverse Correlations Present" in rendered
    assert "Inverse Correlations Missing" in rendered
    assert "Negative Indicators Present" not in rendered
    assert "Missing Negative Indicators" not in rendered
    assert "No negative indicators are defined for &#x27;Contrarian&#x27; trait." in rendered


def test_trait_factor_sections_render_negative_indicator_sections(monkeypatch):
    fixed_evidence = explanations.TraitFactorEvidence(
        supporting=(),
        missing=(),
        inverse_present=(),
        inverse_missing=(),
        negative_indicators_present=("Mars square Saturn",),
        negative_indicators_missing=("Venus trine Jupiter",),
    )
    monkeypatch.setattr(
        trait_factor_sections,
        "build_trait_factor_evidence",
        lambda *_args, **_kwargs: fixed_evidence,
    )

    class Core:
        CHART_DATA_HIGHLIGHT_COLOR = "#abcdef"

        @staticmethod
        def _trait_info_html(_trait, chart=None):
            return "BASE" if chart is None else "LEGACY"

        @staticmethod
        def matched_weighted_criteria(_chart, _profile):
            return {"positive": [], "negative": []}

        @staticmethod
        def weighted_string_entries(_values):
            return {}

        @staticmethod
        def weighted_house_entries(_values):
            return {}

    trait_factor_sections.install_trait_factor_sections(Core)
    rendered = Core._trait_info_html(
        {"name": "Contrarian", "profile": {}},
        SimpleNamespace(name="Example"),
    )

    assert "Negative Indicators Present" in rendered
    assert "Missing Negative Indicators" in rendered
    assert "No negative indicators are defined" not in rendered


def test_trait_factor_sections_render_no_birth_time_unknowns_without_undefined_fallback(monkeypatch):
    fixed_evidence = explanations.TraitFactorEvidence(
        supporting=(),
        missing=(),
        inverse_present=(),
        inverse_missing=(),
        negative_indicators_present=(),
        negative_indicators_missing=(),
        positive_unknown=("House 6 (no BT: unknown)",),
        inverse_unknown=("House 8 (no BT: unknown)",),
        negative_indicators_unknown=("House 9 (no BT: unknown)",),
        has_negative_definitions=True,
    )
    monkeypatch.setattr(
        trait_factor_sections,
        "build_trait_factor_evidence",
        lambda *_args, **_kwargs: fixed_evidence,
    )

    class Core:
        CHART_DATA_HIGHLIGHT_COLOR = "#abcdef"

        @staticmethod
        def _trait_info_html(_trait, chart=None):
            return "BASE" if chart is None else "LEGACY"

        @staticmethod
        def matched_weighted_criteria(_chart, _profile):
            return {"positive": [], "negative": []}

        @staticmethod
        def weighted_string_entries(_values):
            return {}

        @staticmethod
        def weighted_house_entries(_values):
            return {}

    trait_factor_sections.install_trait_factor_sections(Core)
    rendered = Core._trait_info_html(
        {"name": "House Dependent", "profile": {}},
        SimpleNamespace(name="Example"),
    )

    assert "Positive Indicators Unknown" in rendered
    assert "Inverse Correlations Unknown" in rendered
    assert "Negative Indicators Unknown" in rendered
    assert "House 6 (no BT: unknown)" in rendered
    assert "House 8 (no BT: unknown)" in rendered
    assert "House 9 (no BT: unknown)" in rendered
    assert "No negative indicators are defined" not in rendered
