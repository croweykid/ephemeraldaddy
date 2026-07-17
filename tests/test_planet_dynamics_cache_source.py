from pathlib import Path


def test_planet_dynamics_cache_signature_includes_aspects_and_rectified_time():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    method = source.split("def _planet_dynamics_cache_signature", 1)[1].split(
        "def _precompute_planet_dynamics_if_needed", 1
    )[0]

    assert "aspect_signature" in method
    assert 'aspect.get("p1", "")' in method
    assert 'aspect.get("p2", "")' in method
    assert 'aspect.get("type", "")' in method
    assert 'aspect.get("delta", 0.0)' in method
    assert 'getattr(chart, "retcon_time_used", False)' in method
    assert 'getattr(chart, "retcon_hour", None)' in method
    assert 'getattr(chart, "retcon_minute", None)' in method
    assert "_chart_uses_houses(chart)" in method
    assert "bool(chart_uses_houses(chart))" not in method


def test_planet_dynamics_prepare_uses_background_worker_payload():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    assert "class _PlanetDynamicsWorker(QObject)" in source
    worker_source = source.split("class _PlanetDynamicsWorker", 1)[1].split(
        "class _GlobalCloseShortcutFilter", 1
    )[0]
    assert "_calculate_planet_dynamics_scores(self._chart)" in worker_source
    assert "finished = Signal(str, tuple, object)" in worker_source

    precompute_source = source.split("def _precompute_planet_dynamics_if_needed", 1)[1].split(
        "def _forget_planet_dynamics_worker_job", 1
    )[0]
    assert "QThread(self)" in precompute_source
    assert "copy.deepcopy(chart)" in precompute_source
    assert "thread.started.connect(worker.run)" in precompute_source
    assert "self._planet_dynamics_pending_signatures.add(signature)" in precompute_source


def test_planet_dynamics_worker_result_schedules_gui_render_only_after_payload():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    finished_source = source.split("def _on_planet_dynamics_worker_finished", 1)[1].split(
        "def _on_planet_dynamics_worker_failed", 1
    )[0]
    assert 'current_chart = getattr(self, "_latest_chart", None)' in finished_source
    assert "current_chart.planet_dynamics_scores = scores" in finished_source
    assert 'self._schedule_chart_render(current_chart, sections={"planet_dynamics"})' in finished_source
    render_source = source.split("def _render_planet_dynamics", 1)[1].split(
        "def _render_chart_type", 1
    )[0]
    assert "Calculating Body Dynamics in the background" in render_source


def test_pending_planet_dynamics_render_does_not_mark_section_clean():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    flush_source = source.split("def _flush_scheduled_chart_render", 1)[1].split(
        "def _chart_analysis_render_key_for_section", 1
    )[0]
    assert "section_rendered_cleanly = True" in flush_source
    assert "section_rendered_cleanly = self._render_planet_dynamics(chart)" in flush_source
    assert "if section_rendered_cleanly:" in flush_source
    assert "self._mark_chart_analytics_sections_clean({section}, chart)" in flush_source

    render_source = source.split("def _render_planet_dynamics", 1)[1].split(
        "def _render_chart_type", 1
    )[0]
    assert "-> bool" in render_source.splitlines()[0]
    assert "return False" in render_source
    assert "return True" in render_source


def test_planet_dynamics_worker_result_reuses_matching_current_chart_signature():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    finished_source = source.split("def _on_planet_dynamics_worker_finished", 1)[1].split(
        "def _on_planet_dynamics_worker_failed", 1
    )[0]
    assert " is not chart" not in finished_source
    assert 'current_chart = getattr(self, "_latest_chart", None)' in finished_source
    assert "self._planet_dynamics_cache_signature(current_chart) != signature" in finished_source
    assert "current_chart._planet_dynamics_scores_signature = signature" in finished_source
