from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_primary_window_names_are_database_view_and_chart_editor():
    chrome = _source("ephemeraldaddy/gui/window_chrome.py")
    app = _source("ephemeraldaddy/gui/app.py")

    assert 'window.setWindowTitle(f"{APP_DISPLAY_NAME} | Chart Editor — {chart_name}")' in chrome
    assert 'dialog.setWindowTitle(f"{APP_DISPLAY_NAME} | Database View")' in chrome
    assert 'self.setWindowTitle("Ephemeral Daddy | Database View")' in app
    assert 'setWindowTitle("Natal Chart View")' not in app
    assert "Charts Manager" not in app


def test_help_uses_only_primary_window_names():
    help_source = _source("ephemeraldaddy/gui/help.py")
    about_source = _source("ephemeraldaddy/gui/about.py")

    for legacy_name in (
        "Manage Charts",
        "Charts Manager",
        "Natal Chart View",
        "Chart View",
        "Chart Entry",
    ):
        assert legacy_name not in help_source
        assert legacy_name not in about_source
    assert 'title="Chart Editor"' in help_source
    assert 'title="Database View"' in help_source


def test_similarity_modules_and_rectification_visible_labels_are_canonical():
    chrome = _source("ephemeraldaddy/gui/window_chrome.py")
    similarity_panel = _source(
        "ephemeraldaddy/gui/features/charts/similarities/controller.py"
    )
    twins_window = _source(
        "ephemeraldaddy/gui/features/charts/similar_charts_popout.py"
    )
    rectification = _source("ephemeraldaddy/gui/features/dialogues.py")

    assert '"Similarities Analysis"' in chrome
    assert 'QLabel("Similarities Analysis")' in similarity_panel
    assert '"👯 Astro Twin"' in chrome
    assert 'setWindowTitle(f"Astro Twin — {subject_name}")' in twins_window
    assert '"🕗 Rectification Engine"' in chrome
    assert "Retcon Engine" not in rectification
    assert 'setWindowTitle("Ephemeral Daddy: Astro App | Rectification Engine")' in rectification


def test_astro_twin_calculator_and_similarities_analysis_remain_distinct():
    app = _source("ephemeraldaddy/gui/app.py")
    dev_tools = _source("ephemeraldaddy/gui/dev_tools.py")

    assert '"Show Similarities Analysis"' in app
    assert '"Astro Twin Calculator"' in app
    assert '"Choose which algorithm generates Astro Twin Calculator results:"' in dev_tools
    assert "Chart Similarity" not in app
    assert "Astro Twins" not in app
