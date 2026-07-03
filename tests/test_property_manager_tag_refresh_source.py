from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROPERTY_MANAGER_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/property_manager.py").read_text(
    encoding="utf-8"
)


def test_property_manager_dialog_does_not_refresh_visible_tag_pickers_mid_rename():
    launch_body = PROPERTY_MANAGER_SOURCE.split("def launch", 1)[1].split(
        "def load_usage", 1
    )[0]
    assert "refresh_tag_completers=False" in launch_body
    assert "self._host._update_tag_completers()" in launch_body
