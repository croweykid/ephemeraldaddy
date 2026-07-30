from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_primary_window_names_are_database_view_and_chart_entry():
    chrome = _source("ephemeraldaddy/gui/window_chrome.py")
    app = _source("ephemeraldaddy/gui/app.py")

    assert 'window.setWindowTitle(f"{APP_DISPLAY_NAME} | Chart Entry — {chart_name}")' in chrome
    assert 'dialog.setWindowTitle(f"{APP_DISPLAY_NAME} | Database View")' in chrome
    assert 'self.setWindowTitle("Ephemeral Daddy | Database View")' in app
    assert 'setWindowTitle("Natal Chart View")' not in app
    assert "Charts Manager" not in app


def test_help_uses_only_primary_window_names():
    help_source = _source("ephemeraldaddy/gui/help.py")
    about_source = _source("ephemeraldaddy/gui/about.py")

    for legacy_name in ("Manage Charts", "Charts Manager", "Natal Chart View", "Chart View"):
        assert legacy_name not in help_source
        assert legacy_name not in about_source
    assert 'title="Chart Entry"' in help_source
    assert 'title="Database View"' in help_source


def test_similarity_and_rectification_visible_labels_are_canonical():
    chrome = _source("ephemeraldaddy/gui/window_chrome.py")
    similarity_panel = _source(
        "ephemeraldaddy/gui/features/charts/similarities/controller.py"
    )
    twins_window = _source(
        "ephemeraldaddy/gui/features/charts/similar_charts_popout.py"
    )
    rectification = _source("ephemeraldaddy/gui/features/dialogues.py")

    assert '"Chart Similarity"' in chrome
    assert '"🕗 Rectification"' in chrome
    assert "Rectification Engine" not in chrome
    assert 'QLabel("Chart Similarity")' in similarity_panel
    assert 'setWindowTitle(f"Astro Twins — {subject_name}")' in twins_window
    assert "Retcon Engine" not in rectification
    assert 'setWindowTitle("Ephemeral Daddy: Astro App | Rectification")' in rectification
