from pathlib import Path


def _app_source() -> str:
    return Path("ephemeraldaddy/gui/app.py").read_text()


def _popout_source() -> str:
    return Path("ephemeraldaddy/gui/features/charts/similar_charts_popout.py").read_text()


def _worker_source() -> str:
    return Path("ephemeraldaddy/gui/features/charts/similar_charts_worker.py").read_text()


def test_similar_charts_candidates_skip_hidden_charts_unless_show_hidden_enabled():
    source = _popout_source()
    method = source.split("def load_similar_chart_candidates", 1)[1].split(
        "def format_similar_chart_name_parts_html", 1
    )[0]

    assert "hidden_chart_ids: set[int] | None = None" in method
    assert "include_hidden_charts: bool = True" in method
    assert "if not include_hidden_charts and chart_id in hidden_ids:" in method
    assert "continue" in method.split("if not include_hidden_charts and chart_id in hidden_ids:", 1)[1]


def test_similar_charts_app_passes_current_hidden_chart_visibility_to_candidates():
    source = _app_source()
    load_method = source.split("def _load_similar_chart_candidates", 1)[1].split(
        "def _similar_charts_visible_candidate_rows", 1
    )[0]
    visible_rows_method = source.split("def _similar_charts_visible_candidate_rows", 1)[1].split(
        "def _similar_charts_popout_database_row_signatures", 1
    )[0]
    popout_method = source.split("def _show_similar_charts_popout", 1)[1].split(
        "def _export_similar_charts_popout_share", 1
    )[0]

    assert 'hidden_chart_ids=set(getattr(self, "_hidden_chart_ids", set()))' in load_method
    assert 'include_hidden_charts=bool(getattr(self, "_show_hidden_charts", False))' in load_method
    assert 'if getattr(self, "_show_hidden_charts", False):' in visible_rows_method
    assert 'if chart_id not in hidden_chart_ids:' in visible_rows_method
    assert "chart_rows = self._similar_charts_visible_candidate_rows(chart_rows)" in popout_method
    assert popout_method.index("chart_rows = self._similar_charts_visible_candidate_rows(chart_rows)") < popout_method.index("row_signatures =")


def test_chart_view_similar_charts_worker_receives_hidden_chart_visibility():
    app_source = _app_source()
    start_method = app_source.split("def _start_similar_charts_worker", 1)[1].split(
        "def _forget_similar_charts_worker_job", 1
    )[0]
    worker_source = _worker_source()

    assert 'hidden_chart_ids=set(getattr(self, "_hidden_chart_ids", set()))' in start_method
    assert 'include_hidden_charts=bool(getattr(self, "_show_hidden_charts", False))' in start_method
    assert "hidden_chart_ids: set[int] | None = None" in worker_source
    assert "self._hidden_chart_ids = set(hidden_chart_ids or set())" in worker_source
    assert "include_hidden_charts=self._include_hidden_charts" in worker_source
    assert "load_charts_by_ids=load_charts" in worker_source
