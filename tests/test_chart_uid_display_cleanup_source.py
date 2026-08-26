from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
SIMILAR_EXPORT_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/similar_charts_popout.py"
).read_text(encoding="utf-8")
TOTAL_EXPORT_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/total_chart_exporter.py"
).read_text(encoding="utf-8")


def test_related_chart_lookup_copy_does_not_offer_uids():
    assert 'setPlaceholderText("Existing chart name or alias")' in APP_SOURCE
    assert "existing chart name, alias, or UID" not in APP_SOURCE
    assert "chart name, alias, or Chart UID" not in APP_SOURCE
    reminds_method = APP_SOURCE.split("    def _update_reminds_me_of_completer", 1)[1].split(
        "\n    def ", 1
    )[0]
    assert "build_related_chart_choice_map" in reminds_method
    assert "chart_uids.get(chart_id)," not in reminds_method


def test_similar_chart_exports_never_render_uid_fields():
    for source in (SIMILAR_EXPORT_SOURCE, TOTAL_EXPORT_SOURCE):
        assert "| Chart UID |" not in source
        assert "row.get('chart_uid'" not in source
        assert "row['chart_uid']" not in source
        assert "Chart ID" in source


def test_display_chart_ids_are_derived_from_current_render_order():
    assert "self._display_chart_id_by_chart_uid = {}" in APP_SOURCE
    assert "self._display_chart_id_by_chart_uid[item_chart_uid] = display_position" in APP_SOURCE
    assert '"display_chart_id": self._database_view_display_chart_id(chart_uid)' in APP_SOURCE
    assert "def _database_view_display_chart_ids_by_uid" in APP_SOURCE
