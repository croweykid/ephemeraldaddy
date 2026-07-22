from pathlib import Path


SOURCE_PATH = Path("ephemeraldaddy/gui/galaxy_explainer.py")


def _guide_source() -> str:
    source = SOURCE_PATH.read_text()
    start = source.index("def show_guide_to_the_galaxy")
    return source[start:]


def test_guide_intro_blurb_is_paginated_by_paragraph_with_arrows():
    source = _guide_source()

    assert "intro_pages = (" in source
    assert "previous_intro_button = QToolButton" in source
    assert 'previous_intro_button.setText("‹")' in source
    assert "next_intro_button = QToolButton" in source
    assert 'next_intro_button.setText("›")' in source
    assert "def refresh_intro_page" in source
    assert "def move_intro_page" in source
    assert "APPWIDE_BODY_TEXT_MAX_LINE_CHARS" in source
    assert "max-width: {APPWIDE_BODY_TEXT_MAX_LINE_CHARS}ch" in source


def test_guide_intro_blurb_keeps_scrollable_text_browser_and_reduced_height():
    source = _guide_source()

    assert "subhead = QTextBrowser" in source
    assert "subhead_frame.setMinimumHeight(100)" in source
    assert "subhead_frame.setMaximumHeight(100)" in source
    assert "subhead.setMinimumHeight(100)" in source
    assert "subhead.setMaximumHeight(100)" in source


def test_guide_bottom_panels_are_controlled_by_button_panel():
    source = _guide_source()

    assert "panel_buttons.setMinimumHeight(100)" in source
    assert 'geocentric_button = QPushButton("Geocentric Model"' in source
    assert 'accuracy_scores_button = QPushButton("Accuracy Scores"' in source
    assert 'interval_button = QPushButton("Interval Calculator"' in source
    assert 'database_stats_button = QPushButton("Database Statistics"' in source
    assert "left_stack = QStackedWidget" in source
    assert "right_stack = QStackedWidget" in source
    assert 'accuracy_panel.setHtml("<h2>Accuracy Scores</h2><p>Coming soon!</p>")' in source
    assert 'database_stats_panel.setHtml("<h2>Database Statistics</h2><p>Coming soon!</p>")' in source


def test_guide_window_does_not_add_redundant_bottom_close_button():
    source = _guide_source()

    tail = source[source.index("calculate_button.clicked.connect(refresh_ranges)"):]
    assert "QDialogButtonBox(QDialogButtonBox.Close" not in tail
    assert "layout.addWidget(buttons)" not in tail
