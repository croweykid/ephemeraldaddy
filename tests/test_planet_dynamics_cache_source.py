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
    worker_source = Path(
        "ephemeraldaddy/gui/features/chart_editor/body_dynamics_worker.py"
    ).read_text()
    assert "class _PlanetDynamicsWorker(QObject)" not in source
    assert "class PlanetDynamicsWorker(QObject)" in worker_source
    assert "calculate_planet_dynamics_scores(self._chart)" in worker_source
    # assert "class _PlanetDynamicsWorker(QObject)" in source
    # worker_source = source.split("class _PlanetDynamicsWorker", 1)[1].split(
    #     "class _ComboItemColorDelegate", 1
    # )[0]
    # assert "_calculate_planet_dynamics_scores(self._chart)" in worker_source
    assert "finished = Signal(str, tuple, object)" in worker_source
    assert "failed = Signal(str, tuple, str)" in worker_source
    interruption_check = (
        "if QThread.currentThread().isInterruptionRequested():\n"
        "                return"
    )
    assert interruption_check in worker_source
    assert worker_source.index(interruption_check) < worker_source.index(
        "calculate_planet_dynamics_scores(self._chart)"
    )
    assert "self.failed.emit(self._request_id, self._signature, str(exc))" in worker_source

    precompute_source = source.split("def _precompute_planet_dynamics_if_needed", 1)[1].split(
        "def _forget_planet_dynamics_worker_job", 1
    )[0]
    assert "QThread(self)" in precompute_source
    assert "PlanetDynamicsWorker(request_id, signature, copy.deepcopy(chart))" in precompute_source
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


def _dynamics_app_method(name: str):
    """Execute one instance method without importing the full Qt application."""
    import ast
    from collections.abc import Mapping
    from types import SimpleNamespace

    source = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    methods = [
        node
        for cls in tree.body
        if isinstance(cls, ast.ClassDef)
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(methods) == 1, f"Expected exactly one {name} method"
    mode = {"selected": "Osculating Lilith"}
    namespace = {
        "Chart": object,
        "Mapping": Mapping,
        "_chart_uses_houses": lambda chart: bool(getattr(chart, "houses", None)),
        "load_lilith_mode": lambda settings: mode["selected"],
        "getattr": getattr,
    }
    exec(
        compile(
            ast.Module(body=[methods[0]], type_ignores=[]),
            "ephemeraldaddy/gui/app.py",
            "exec",
        ),
        namespace,
    )
    return namespace[name], mode


def test_lilith_mode_change_invalidates_existing_body_dynamics_signature():
    from types import SimpleNamespace

    signature_for, mode = _dynamics_app_method("_planet_dynamics_cache_signature")
    owner = SimpleNamespace(_settings=object())
    chart = SimpleNamespace(
        positions={"Sun": 12.0, "Moon": 42.0},
        houses=[float(i * 30) for i in range(12)],
        aspects=[{"p1": "Sun", "p2": "Moon", "type": "sextile", "delta": 0.0}],
    )

    signature_osculating = signature_for(owner, chart)
    chart.planet_dynamics_scores = {"Sun": {"enabling": 2.0}}
    chart._planet_dynamics_scores_signature = signature_osculating
    mode["selected"] = "Mean Lilith"
    signature_mean = signature_for(owner, chart)
    assert signature_mean != signature_osculating
    assert signature_mean[0] == "Mean Lilith"
    assert chart._planet_dynamics_scores_signature != signature_mean

    mode["selected"] = "Natural Lilith"
    signature_natural = signature_for(owner, chart)
    assert signature_natural not in {signature_mean, signature_osculating}


def test_old_mode_body_dynamics_worker_result_is_discarded():
    from types import SimpleNamespace

    signature_for, mode = _dynamics_app_method("_planet_dynamics_cache_signature")
    finish, _ = _dynamics_app_method("_on_planet_dynamics_worker_finished")
    # This worker callback uses the same runtime signature method as the owner.
    chart = SimpleNamespace(
        positions={"Sun": 12.0},
        houses=[],
        aspects=[],
        planet_dynamics_scores={},
        _planet_dynamics_scores_signature=None,
    )
    renders = []
    owner = SimpleNamespace(
        _settings=object(),
        _latest_chart=chart,
        _planet_dynamics_pending_signatures=set(),
        _schedule_chart_render=lambda *args, **kwargs: renders.append((args, kwargs)),
    )
    owner._planet_dynamics_cache_signature = lambda value: signature_for(owner, value)
    stale_signature = signature_for(owner, chart)
    owner._planet_dynamics_pending_signatures.add(stale_signature)
    mode["selected"] = "Mean Lilith"

    finish(owner, "previous-request", stale_signature, {"Sun": {"enabling": 99.0}}, chart)
    assert chart.planet_dynamics_scores == {}
    assert chart._planet_dynamics_scores_signature is None
    assert renders == []
    assert stale_signature not in owner._planet_dynamics_pending_signatures

    current_signature = signature_for(owner, chart)
    owner._planet_dynamics_pending_signatures.add(current_signature)
    finish(owner, "current-request", current_signature, {"Sun": {"enabling": 3.0}}, chart)
    assert chart.planet_dynamics_scores["Sun"]["enabling"] == 3.0
    assert chart._planet_dynamics_scores_signature == current_signature
    assert len(renders) == 1


def test_lilith_switch_clears_body_dynamics_scores_as_well_as_other_weight_caches():
    source = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    method = source.split("def _handle_selected_lilith_mode_changed", 1)[1].split(
        "def _handle_lilith_calculation_method_changed", 1
    )[0]
    assert '"planet_dynamics_scores"' in method
    assert "chart._planet_dynamics_scores_signature = None" in method
