from __future__ import annotations

from pathlib import Path

from ephemeraldaddy.gui.features.database_view import performance


def test_database_view_open_timing_records_stable_workflow_metric(monkeypatch) -> None:
    clock = iter((10.0, 10.125))
    monkeypatch.setattr(performance, "perf_counter", lambda: next(clock))
    recorded: list[tuple[str, float, dict[str, object]]] = []

    timing = performance.DatabaseViewOpenTiming(
        recorder=lambda operation, elapsed_ms, **details: recorded.append(
            (operation, elapsed_ms, details)
        )
    )
    timing.complete(was_visible=False, refresh_reason="initial_population")

    assert recorded == [
        (
            "database_view.open_to_visible",
            125.0,
            {
                "status": "ok",
                "was_visible": False,
                "refresh_reason": "initial_population",
            },
        )
    ]


def test_database_view_open_timing_only_records_once(monkeypatch) -> None:
    clock = iter((20.0, 20.050))
    monkeypatch.setattr(performance, "perf_counter", lambda: next(clock))
    recorded: list[str] = []
    timing = performance.DatabaseViewOpenTiming(
        recorder=lambda operation, _elapsed_ms, **_details: recorded.append(operation)
    )

    timing.complete(was_visible=True, refresh_reason="none")
    timing.complete(was_visible=True, refresh_reason="none")

    assert recorded == ["database_view.open_to_visible"]


def test_database_view_timer_starts_before_cold_dialog_construction() -> None:
    app_source = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    method = app_source.split("    def on_manage_charts(", 1)[1].split(
        "    def _hide_chart_view_while_database_view_is_open", 1
    )[0]

    confirmation = method.index("confirm_manage_charts_open")
    timing_start = method.index("database_view_open_timing = DatabaseViewOpenTiming()")
    dialog_construction = method.index("self._get_or_create_manage_charts_dialog()")
    controller_handoff = method.index("open_timing=database_view_open_timing")

    assert confirmation < timing_start < dialog_construction < controller_handoff
