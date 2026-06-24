from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py")


def test_placeholder_chart_type_is_set_before_alternate_chart_uid_lookup():
    source = APP_SOURCE.read_text(encoding="utf-8")
    method_source = source.split("    def _build_placeholder_chart", 1)[1].split(
        "    def _build_chart_from_inputs", 1
    )[0]

    chart_type_assignment = method_source.index(
        "placeholder.chart_type = _normalize_gui_source(self.chart_source_combo.currentData())"
    )
    alternate_uid_assignment = method_source.index(
        "placeholder.alternate_chart_uid = self._current_alternate_chart_uid_for_save(placeholder.chart_type)"
    )

    assert chart_type_assignment < alternate_uid_assignment
