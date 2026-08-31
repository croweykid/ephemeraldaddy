from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication, QToolButton, QVBoxLayout, QWidget

from ephemeraldaddy.core.perceived_accuracy import get_perceived_accuracy_value
from ephemeraldaddy.gui.features.chart_information.perceived_accuracy import (
    PerceivedAccuracyTarget,
    PerceivedAccuracyThumbs,
    install_chart_editor_module_controls,
)
from ephemeraldaddy.gui.style import (
    DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
    configure_collapsible_header_toggle,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_thumbs_map_toggle_replace_and_clear_states(tmp_path):
    _app()
    uid = "ABCDEF1234567890"
    db_path = tmp_path / "ratings.sqlite"
    control = PerceivedAccuracyThumbs(
        lambda: uid,
        target=PerceivedAccuracyTarget("modules", "dnd_species"),
        db_path=db_path,
    )

    assert control.state is None
    control.positive_button.click()
    assert control.state is True
    assert control.positive_button.isChecked()
    control.negative_button.click()
    assert control.state is False
    assert control.negative_button.isChecked()
    control.negative_button.click()
    assert control.state is None
    assert not control.positive_button.isChecked()
    assert not control.negative_button.isChecked()


def test_retargeting_keeps_property_and_module_namespaces_independent(tmp_path):
    _app()
    uid = "ABCDEF1234567890"
    db_path = tmp_path / "ratings.sqlite"
    control = PerceivedAccuracyThumbs(
        lambda: uid,
        target=PerceivedAccuracyTarget("modules", "same-key"),
        db_path=db_path,
    )
    control.positive_button.click()
    control.retarget(PerceivedAccuracyTarget("properties", "same-key"))
    assert control.state is None
    control.negative_button.click()

    assert get_perceived_accuracy_value(uid, "modules", "same-key", db_path=db_path) is True
    assert get_perceived_accuracy_value(uid, "properties", "same-key", db_path=db_path) is False


def test_missing_uid_or_semantic_target_disables_persistence_control(tmp_path):
    _app()
    control = PerceivedAccuracyThumbs(
        lambda: None,
        target=PerceivedAccuracyTarget("properties", "moon_sign:aries"),
        db_path=tmp_path / "ratings.sqlite",
    )
    assert not control.isEnabled()
    control.retarget(None)
    assert control.state is None


def test_refresh_from_payload_maps_state_without_database_access(monkeypatch, tmp_path):
    _app()
    control = PerceivedAccuracyThumbs(
        lambda: "ABCDEF1234567890",
        target=PerceivedAccuracyTarget("modules", "anagrams"),
        db_path=tmp_path / "ratings.sqlite",
    )
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.chart_information.perceived_accuracy."
        "get_perceived_accuracy_value",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected query")),
    )
    control.refresh_from_payload(
        {"perceived_accuracy": {"modules": {"anagrams": {"value": True}}}}
    )
    assert control.state is True
    assert control.positive_button.isChecked()


def test_installer_finds_nested_semantically_keyed_header():
    _app()
    owner = QWidget()
    child = QWidget(owner)
    QVBoxLayout(owner).addWidget(child)
    child_layout = QVBoxLayout(child)
    toggle = QToolButton(child)
    configure_collapsible_header_toggle(
        toggle,
        title="Copy-editable title",
        expanded=False,
        style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        semantic_key="anagrams",
    )
    child_layout.addWidget(toggle)

    controls = install_chart_editor_module_controls(
        owner,
        chart_uid=lambda: "ABCDEF1234567890",
        visible=True,
    )
    assert set(controls) == {"chart_editor:anagrams"}
    assert controls["chart_editor:anagrams"].parent() is toggle
