from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
TRAITS_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/settings/traits_manager.py"
).read_text(encoding="utf-8")
RELAYS_SOURCE = (ROOT / "ephemeraldaddy/gui/worker_ui_relays.py").read_text(
    encoding="utf-8"
)


def test_similar_charts_terminal_callbacks_cross_gui_owned_qobject_relay() -> None:
    assert "SimilarChartsUiRelay(" in APP_SOURCE
    assert (
        "worker.finished.connect(similar_ui_relay.handle_finished, Qt.QueuedConnection)"
        in APP_SOURCE
    )
    assert (
        "worker.failed.connect(similar_ui_relay.handle_failed, Qt.QueuedConnection)"
        in APP_SOURCE
    )


def test_planet_dynamics_terminal_callbacks_cross_gui_owned_qobject_relay() -> None:
    assert "PlanetDynamicsUiRelay(" in APP_SOURCE
    assert (
        "worker.finished.connect(planet_dynamics_ui_relay.handle_finished, Qt.QueuedConnection)"
        in APP_SOURCE
    )
    assert (
        "worker.failed.connect(planet_dynamics_ui_relay.handle_failed, Qt.QueuedConnection)"
        in APP_SOURCE
    )


def test_trait_reassessment_terminal_callbacks_cross_gui_owned_qobject_relay() -> None:
    assert "TraitReassessmentUiRelay(" in TRAITS_SOURCE
    assert (
        "worker.finished.connect(ui_relay.handle_finished, Qt.QueuedConnection)"
        in TRAITS_SOURCE
    )
    assert (
        "worker.failed.connect(ui_relay.handle_failed, Qt.QueuedConnection)"
        in TRAITS_SOURCE
    )
    assert (
        "worker.finished.connect(reassessment_finished, Qt.QueuedConnection)"
        not in TRAITS_SOURCE
    )
    assert (
        "worker.failed.connect(reassessment_failed, Qt.QueuedConnection)"
        not in TRAITS_SOURCE
    )


def test_gui_relays_are_qobjects_with_typed_slots() -> None:
    assert "super().__init__(parent)" in RELAYS_SOURCE
    for decorator in (
        "@Slot(str, object)",
        "@Slot(str, str)",
        "@Slot(int, str, str, object)",
        "@Slot(int, str, str, str)",
        "@Slot(object)",
        "@Slot(str)",
    ):
        assert decorator in RELAYS_SOURCE
