from pathlib import Path

from ephemeraldaddy.core.interpretations import DARK_TEXT, PLANET_COLORS


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_dark_text_colors_follow_canonical_body_palette() -> None:
    dark_bodies = {
        "Pluto",
        "Saturn",
        "Uranus",
        "Rahu",
        "Ketu",
        "Chiron",
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
        "Lilith",
        "Part of Fortune",
        "Fortune",
    }

    assert DARK_TEXT == frozenset(PLANET_COLORS[body].lower() for body in dark_bodies)


def test_position_sign_info_uses_body_color_only_for_plain_format() -> None:
    method = APP_SOURCE.split("    def _show_sign_keyword_info(", 1)[1].split(
        "\n    def ", 1
    )[0]

    assert 'plain_fmt.setForeground(QColor(body_color or "#ffffff"))' in method
    assert "header_fmt.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))" in method
    assert "else SIGN_COLORS.get(sign_key)" in method
    assert "set_chart_info_contrast_background(self.chart_info_output, body_color)" in method


def test_each_summary_target_resets_contrast_before_rendering() -> None:
    method = APP_SOURCE.rsplit("    def _run_with_chart_info_output(", 1)[1].split(
        "\n    def ", 1
    )[0]

    reset = method.index("set_chart_info_contrast_background(target_info_widget)")
    render = method.index("return callback()")
    assert reset < render


def test_direct_chart_info_link_paths_prepare_default_surface() -> None:
    helper = APP_SOURCE.split("    def _prepare_chart_info_replacement(", 1)[1].split(
        "\n    def ", 1
    )[0]
    distinguishing_handler = APP_SOURCE.split(
        "    def _on_distinguishing_factor_link_activated(", 1
    )[1].split("\n    def ", 1)[0]
    analysis_handler = APP_SOURCE.split(
        "    def _on_chart_analysis_above_average_link_activated(", 1
    )[1].split("\n    def ", 1)[0]

    assert 'self._set_chart_info_panel_mode("chart_info")' in helper
    assert "set_chart_info_contrast_background(self.chart_info_output)" in helper
    assert distinguishing_handler.index("self._prepare_chart_info_replacement()") < (
        distinguishing_handler.index('if kind == "planet"')
    )
    assert analysis_handler.index("self._prepare_chart_info_replacement()") < (
        analysis_handler.index('if kind == "sign"')
    )
