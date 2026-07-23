from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROPERTY_MANAGER_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/property_manager.py").read_text(
    encoding="utf-8"
)
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text(encoding="utf-8")


def test_property_manager_tracks_and_refreshes_open_widgets():
    assert "self._open_widgets" in PROPERTY_MANAGER_SOURCE
    assert "def refresh_open_widgets" in PROPERTY_MANAGER_SOURCE
    assert "dialog.refresh_usage()" in PROPERTY_MANAGER_SOURCE
    assert "self._track_widget(dialog)" in PROPERTY_MANAGER_SOURCE


def test_batch_tag_updates_refresh_open_property_manager_widgets():
    finalize_body = APP_SOURCE.split("def _finalize_batch_tag_updates", 1)[1].split(
        "def _bind_batch_enter_apply", 1
    )[0]
    assert "coordinator = getattr(self, \"_property_manager_coordinator\", None)" in finalize_body
    assert "coordinator.refresh_open_widgets()" in finalize_body


def test_metadata_label_dialog_exposes_usage_refresh_entrypoint():
    assert "def refresh_usage(self) -> None:" in DEV_TOOLS_SOURCE
    assert "self._reload_usage()" in DEV_TOOLS_SOURCE
