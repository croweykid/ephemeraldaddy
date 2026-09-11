from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py")
SETTINGS_SOURCE = Path("ephemeraldaddy/gui/features/similarities/settings.py")


def test_similarity_settings_are_owned_by_similarity_workflow() -> None:
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    settings_source = SETTINGS_SOURCE.read_text(encoding="utf-8")

    assert "def _load_similarity_calculator_settings(" not in app_source
    assert "def _save_similarity_calculator_settings(" not in app_source
    assert "def load_similarity_calculator_settings(" in settings_source
    assert "def save_similarity_calculator_settings(" in settings_source
    assert "class SettingsStore(Protocol):" in settings_source
