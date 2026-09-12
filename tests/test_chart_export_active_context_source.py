"""Regression contracts for Chart Editor and Database View export routing."""

from pathlib import Path


APP_SOURCE = (
    Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"
).read_text()


def _method(name: str, *, last: bool = False) -> str:
    marker = f"    def {name}("
    start = APP_SOURCE.rindex(marker) if last else APP_SOURCE.index(marker)
    end = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if end == -1 else APP_SOURCE[start:end]


def test_active_context_export_keeps_shared_chart_export_delegate():
    active_context_router = _method("_run_chart_action_from_active_context")
    export_delegate = _method("_export_chart", last=True)
    chart_editor_action = _method("on_export_chart")

    assert 'elif action_name == "export_chart":' in active_context_router
    assert "self._export_chart(chart)" in active_context_router
    assert "self._export_chart(self._latest_chart)" in chart_editor_action
    assert "self._chart_markdown_export_controller.export(chart)" in export_delegate
