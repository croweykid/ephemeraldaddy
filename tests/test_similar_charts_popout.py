import sys
import types
from types import SimpleNamespace


def _install_pyside_stubs():
    pyside = sys.modules.setdefault("PySide6", types.ModuleType("PySide6"))
    qt_core = sys.modules.setdefault("PySide6.QtCore", types.ModuleType("PySide6.QtCore"))
    qt_gui = sys.modules.setdefault("PySide6.QtGui", types.ModuleType("PySide6.QtGui"))
    qt_widgets = sys.modules.setdefault("PySide6.QtWidgets", types.ModuleType("PySide6.QtWidgets"))

    class _Qt:
        WindowModal = 1
        Horizontal = 2
        Vertical = 3
        AlignTop = 4
        AlignLeft = 5
        Widget = 6
        RichText = 7
        TextBrowserInteraction = 8
        TextSelectableByMouse = 9
        PointingHandCursor = 10
        DownArrow = 11
        RightArrow = 12

    class _QEventLoop:
        AllEvents = 1

    class _Widget:
        def __init__(self, *_args, **_kwargs):
            pass

    qt_core.QEventLoop = getattr(qt_core, "QEventLoop", _QEventLoop)
    qt_core.QSignalBlocker = getattr(qt_core, "QSignalBlocker", _Widget)
    qt_core.QSize = getattr(qt_core, "QSize", _Widget)
    qt_core.Qt = getattr(qt_core, "Qt", _Qt)
    qt_gui.QIcon = getattr(qt_gui, "QIcon", _Widget)
    qt_gui.QIntValidator = getattr(qt_gui, "QIntValidator", _Widget)
    for name in (
        "QApplication",
        "QCheckBox",
        "QComboBox",
        "QDialog",
        "QFrame",
        "QHBoxLayout",
        "QLabel",
        "QLineEdit",
        "QMessageBox",
        "QProgressDialog",
        "QPushButton",
        "QScrollArea",
        "QSplitter",
        "QTextEdit",
        "QToolButton",
        "QVBoxLayout",
        "QWidget",
    ):
        if not hasattr(qt_widgets, name):
            setattr(qt_widgets, name, _Widget)

    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui
    pyside.QtWidgets = qt_widgets


def _install_style_stub():
    style = sys.modules.setdefault("ephemeraldaddy.gui.style", types.ModuleType("ephemeraldaddy.gui.style"))
    style.CHART_DATA_DIVIDER = getattr(style, "CHART_DATA_DIVIDER", "---------")
    style.CHART_DATA_HIGHLIGHT_COLOR = getattr(style, "CHART_DATA_HIGHLIGHT_COLOR", "#ffffff")
    style.DEFAULT_DROPDOWN_STYLE = getattr(style, "DEFAULT_DROPDOWN_STYLE", "")

    def format_chart_header(*_args, **_kwargs):
        return ""

    def blend_hex_colors(color_a, color_b, ratio=0.5):
        return color_a or color_b or "#000000"

    if not hasattr(style, "format_chart_header"):
        style.format_chart_header = format_chart_header
    if not hasattr(style, "blend_hex_colors"):
        style.blend_hex_colors = blend_hex_colors
    for helper_name in ("apply_button_cursor", "apply_chart_info_link_cursor", "apply_popout_cursor"):
        if not hasattr(style, helper_name):
            setattr(style, helper_name, lambda *_args, **_kwargs: None)


_install_pyside_stubs()
_install_style_stub()

from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: E402
    _human_design_gate_difference_lines,
)


def test_human_design_gate_differences_use_chart_labels():
    subject = SimpleNamespace(name="Alice", human_design_gates=[1, "2", "bad"])
    compared = SimpleNamespace(name="Boris", human_design_gates=[2, 3])

    assert _human_design_gate_difference_lines(subject, compared) == [
        "Only in Alice's chart: Gate 1",
        "Only in Boris' chart: Gate 3",
    ]


def _band_for_test(_percent):
    return "test band", "#ffffff"


def test_similar_chart_export_rows_include_z_score():
    match = SimpleNamespace(
        chart_id=7,
        chart_name="Test Chart",
        score=0.82,
        placement_score=0.8,
        aspect_score=0.7,
        distribution_score=0.6,
        dominance_score=0.5,
    )

    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        build_similar_charts_export_lines,
        build_similar_charts_export_rows_from_matches,
    )

    rows = build_similar_charts_export_rows_from_matches(
        matches=[match],
        resolve_similarity_band=_band_for_test,
        similarity_average=70.0,
        similarity_standard_deviation=6.0,
    )

    assert rows[0]["similarity_z_score"] == 2.0
    markdown = "\n".join(build_similar_charts_export_lines(subject_name="Subject", rows=rows, is_markdown=True))
    plain = "\n".join(build_similar_charts_export_lines(subject_name="Subject", rows=rows, is_markdown=False))
    assert "+2.000" in markdown
    assert "z=+2.000" in plain


def test_similar_match_blocks_include_z_score():
    match = SimpleNamespace(
        chart_id=7,
        chart_name="Test Chart",
        score=0.82,
        placement_score=0.8,
        aspect_score=0.7,
        distribution_score=0.6,
        dominance_score=0.5,
        chart_uses_houses=True,
        algorithm_mode="default",
    )

    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        render_similar_match_blocks,
    )

    html = render_similar_match_blocks(
        matches=[match],
        highlight_color="#ffffff",
        resolve_similarity_band=_band_for_test,
        similarity_average=70.0,
        similarity_standard_deviation=6.0,
    )

    assert "z=+2.00" in html


def test_similar_match_blocks_preserve_starting_rank_for_per_row_rendering():
    match = SimpleNamespace(
        chart_id=9,
        chart_name="Ranked Chart",
        score=0.72,
        placement_score=0.7,
        aspect_score=0.6,
        distribution_score=0.5,
        dominance_score=0.4,
        chart_uses_houses=True,
        algorithm_mode="default",
    )

    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        render_similar_match_blocks,
    )

    html = render_similar_match_blocks(
        matches=[match],
        highlight_color="#ffffff",
        resolve_similarity_band=_band_for_test,
        start_rank=7,
    )

    assert ">7.</span>" in html
    assert ">1.</span>" not in html


def test_popout_chart_name_links_request_database_to_chart_view_transition():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()
    assert "transition_to_chart_view: bool = False" in source
    assert "_similar_chart_popout_opened_from_database_view = bool(database_view_active)" in source
    assert "transition_to_chart_view=bool(" in source
    assert "activate=False" in source
    assert "manage_dialog.hide()" in source
    assert "lambda dialog=source_dialog: self._keep_similar_charts_popout_in_front(dialog)" in source
    assert "except RuntimeError:" in source
    assert "if current_chart_id == chart_id:" in source
    assert "chart_is_hypothetical as _chart_is_hypothetical" in source
    assert "if _chart_is_hypothetical(chart):" in source


def test_similarity_reasoning_html_links_chart_info_terms():
    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        build_similarity_reasoning_panel_html,
    )

    subject = SimpleNamespace(name="Subject", positions={"Sun": 5.0}, houses=[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330])
    compared = SimpleNamespace(name="Compared", positions={"Sun": 6.0}, houses=[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330])
    match = SimpleNamespace(chart_id=7, chart_name="Compared", algorithm_mode="default", dominance_score=1.0)

    html = build_similarity_reasoning_panel_html(
        match=match,
        subject_name="Subject",
        subject_chart=subject,
        compared_chart=compared,
        resolve_similarity_band=_band_for_test,
    )

    assert "chart-info:body:Sun" in html
    assert "chart-info:sign:Aries" in html
    assert "chart-info:house:1" in html


def test_big_3_similarity_reasoning_html_shows_component_breakdown_for_both_analysis_modes():
    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        build_similarity_reasoning_panel_html,
    )

    subject = SimpleNamespace(
        name="Subject",
        positions={
            "Sun": 5.0,
            "Moon": 45.0,
            "Mercury": 65.0,
            "Venus": 95.0,
            "Mars": 125.0,
            "AS": 215.0,
            "MC": 275.0,
        },
    )
    compared = SimpleNamespace(
        name="Compared",
        positions={
            "Sun": 6.0,
            "Moon": 75.0,
            "Mercury": 66.0,
            "Venus": 155.0,
            "Mars": 126.0,
            "AS": 245.0,
            "MC": 276.0,
        },
    )
    match = SimpleNamespace(chart_id=7, chart_name="Compared", algorithm_mode="big_3", score=0.5)

    for analysis_mode in ("similarities", "dissimilarities"):
        html = build_similarity_reasoning_panel_html(
            match=match,
            subject_name="Subject",
            subject_chart=subject,
            compared_chart=compared,
            resolve_similarity_band=_band_for_test,
            analysis_mode=analysis_mode,
        )

        if analysis_mode == "similarities":
            assert "Big 3 sign matches:" in html
            assert "Sun</a> sign:" in html
            assert "both <a href='chart-info:sign:Aries'" in html
            assert "Mercury</a> sign:" in html
            assert "Mars</a> sign:" in html
            assert "MC</a> sign:" in html
            assert "Moon</a> sign:" not in html
            assert "AS</a>:" not in html
        else:
            assert "Big 3 sign differences:" in html
            assert "Moon</a> sign:" in html
            assert "Subject <a href='chart-info:sign:Taurus'" in html
            assert "Compared <a href='chart-info:sign:Gemini'" in html
            assert "Venus</a> sign:" in html
            assert "AS</a>:" in html
            assert "Sun</a> sign:" not in html
            assert "MC</a> sign:" not in html


def test_similar_chart_biography_appends_generated_context_to_existing_bio():
    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        build_similar_chart_biography_text,
    )

    chart = SimpleNamespace(
        biography="Existing biography.",
        from_whence="public figures database",
        alias="Example Alias",
        tags=["actor", "musician", "Actor"],
    )

    assert build_similar_chart_biography_text(compared_chart=chart) == (
        "Existing biography.\n\n"
        "from: public figures database\n"
        "aka: Example Alias\n"
        "tags: actor, musician"
    )


def test_similar_chart_biography_still_uses_generated_context_without_existing_bio():
    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        build_similar_chart_biography_text,
    )

    chart = SimpleNamespace(
        metadata={"from": "custom import", "alias": "Metadata Alias", "tags": "one, two"},
    )

    assert build_similar_chart_biography_text(compared_chart=chart) == (
        "from: custom import\n"
        "aka: Metadata Alias\n"
        "tags: one, two"
    )


def test_perceived_similarity_accuracy_tally_excludes_na_and_averages_absolute_error():
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (  # noqa: PLC0415
        calculate_perceived_similarity_accuracy,
        format_perceived_similarity_accuracy_tally,
    )

    accuracy = calculate_perceived_similarity_accuracy(
        [
            {"predicted_percent": 80, "perceived_percent": 70, "not_applicable": False},
            {"predicted_percent": 25, "perceived_percent": 45, "not_applicable": False},
            {"predicted_percent": 99, "perceived_percent": 0, "not_applicable": True},
        ]
    )

    assert accuracy == 85.0
    assert format_perceived_similarity_accuracy_tally(accuracy) == "Accuracy: 85%"


def test_perceived_similarity_accuracy_tally_returns_empty_without_scored_rows():
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (  # noqa: PLC0415
        calculate_perceived_similarity_accuracy,
        format_perceived_similarity_accuracy_tally,
    )

    assert calculate_perceived_similarity_accuracy([{"predicted_percent": 80, "not_applicable": True}]) is None
    assert format_perceived_similarity_accuracy_tally(None) == "Accuracy: —"


def test_database_distinction_components_render_in_summary_and_export_rows():
    match = SimpleNamespace(
        chart_id=9,
        chart_name="Distinct Chart",
        score=0.91,
        placement_score=0.0,
        aspect_score=0.0,
        distribution_score=0.0,
        dominance_score=None,
        component_scores={
            "distinguishing_factors": 0.75,
            "concentration_flags": 1.0,
            "repeated_hd_gates": 0.5,
        },
        algorithm_mode="database_distinction",
    )

    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        build_similar_charts_export_lines,
        build_similar_charts_export_rows_from_matches,
        format_similarity_component_summary,
        resolve_similarity_component_keys_for_display,
    )

    component_keys = resolve_similarity_component_keys_for_display(
        algorithm_mode="database_distinction",
        similarity_settings=None,
    )
    summary = format_similarity_component_summary(match=match, component_keys=component_keys)
    assert "distinguishing factors 75%" in summary
    assert "concentration flags 100%" in summary
    assert "repeated HD gates 50%" in summary
    assert "placements 0%" not in summary

    rows = build_similar_charts_export_rows_from_matches(
        matches=[match],
        resolve_similarity_band=_band_for_test,
    )
    assert rows[0]["component_summary"] == summary
    plain = "\n".join(build_similar_charts_export_lines(subject_name="Subject", rows=rows, is_markdown=False))
    markdown = "\n".join(build_similar_charts_export_lines(subject_name="Subject", rows=rows, is_markdown=True))
    assert "distinguishing factors 75%" in plain
    assert "repeated HD gates 50%" in markdown
    assert "placements 0.0%" not in plain
