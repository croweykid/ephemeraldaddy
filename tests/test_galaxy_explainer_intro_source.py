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
    assert "subhead.setHtml(intro_pages" in source


def test_guide_intro_blurb_keeps_scrollable_text_browser_and_taller_min_height():
    source = _guide_source()

    assert "subhead = QTextBrowser" in source
    assert "subhead_frame.setMinimumHeight(146)" in source
    assert "subhead.setMinimumHeight(146)" in source
    assert "subhead.setMaximumHeight(96)" not in source


def test_guide_window_does_not_add_redundant_bottom_close_button():
    source = _guide_source()

    tail = source[source.index("calculate_button.clicked.connect(refresh_ranges)"):]
    assert "QDialogButtonBox(QDialogButtonBox.Close" not in tail
    assert "layout.addWidget(buttons)" not in tail
