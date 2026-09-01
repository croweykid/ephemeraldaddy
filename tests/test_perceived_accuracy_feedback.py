from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication, QToolButton, QVBoxLayout, QWidget

from ephemeraldaddy.core.perceived_accuracy import get_perceived_accuracy_value
from ephemeraldaddy.gui.features.chart_information.perceived_accuracy import (
    PerceivedAccuracyTarget,
    PerceivedAccuracyThumbs,
    install_chart_editor_module_controls,
    property_target_from_entry,
    set_chart_information_control_mode,
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
    control.refresh()

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
    control.refresh()
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


def test_statblock_has_chart_scoped_singleton_property_target():
    assert property_target_from_entry(
        {"kind": "statblock", "profile_lines": ["STR 12"]}
    ) == PerceivedAccuracyTarget("properties", "dnd_statblock")


def test_decan_property_target_distinguishes_decan_boundaries():
    first = property_target_from_entry(
        {"kind": "decan_keyword", "body": "Moon", "sign": "Aries", "decan": 1}
    )
    second = property_target_from_entry(
        {"kind": "decan_keyword", "body": "Moon", "sign": "Aries", "decan": 2}
    )
    assert first is not None
    assert second is not None
    assert first.key != second.key


def test_aspect_property_target_includes_sign_and_house_context():
    base = {"kind": "aspect", "p1": "Sun", "p2": "Moon", "type": "square"}
    first = property_target_from_entry(
        {**base, "sign1": "Aries", "sign2": "Cancer", "house1": 1, "house2": 4}
    )
    second = property_target_from_entry(
        {**base, "sign1": "Taurus", "sign2": "Leo", "house1": 2, "house2": 5}
    )
    assert first is not None
    assert second is not None
    assert first.key != second.key


def test_non_chart_info_mode_preserves_target_while_hiding_control(tmp_path):
    _app()
    control = PerceivedAccuracyThumbs(
        lambda: "ABCDEF1234567890",
        target=PerceivedAccuracyTarget("properties", "moon_sign:aries"),
        db_path=tmp_path / "ratings.sqlite",
    )
    set_chart_information_control_mode(
        control, mode="biography", preference_visible=True
    )
    assert control.target == PerceivedAccuracyTarget("properties", "moon_sign:aries")
    assert control.isHidden()
    set_chart_information_control_mode(
        control, mode="chart_info", preference_visible=True
    )
    assert control.target == PerceivedAccuracyTarget("properties", "moon_sign:aries")
    assert not control.isHidden()


def test_constructor_defers_persistence_read(monkeypatch):
    _app()
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.chart_information.perceived_accuracy."
        "get_perceived_accuracy_value",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected query")),
    )
    control = PerceivedAccuracyThumbs(
        lambda: "ABCDEF1234567890",
        target=PerceivedAccuracyTarget("modules", "anagrams"),
    )
    assert control.state is None
    assert not control.isEnabled()


def test_hidden_and_unchanged_retargets_do_not_query(monkeypatch):
    _app()
    original = PerceivedAccuracyTarget("properties", "moon_sign:aries")
    control = PerceivedAccuracyThumbs(
        lambda: "ABCDEF1234567890",
        target=original,
    )
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.chart_information.perceived_accuracy."
        "get_perceived_accuracy_value",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected query")),
    )
    control.retarget(original)
    control.hide()
    control.retarget(PerceivedAccuracyTarget("properties", "mars_sign:taurus"))
    assert control.target == PerceivedAccuracyTarget("properties", "mars_sign:taurus")
    assert not control.isEnabled()
