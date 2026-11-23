"""Regression guards for compact, editable Chart View quote cards."""

from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
).read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    return SOURCE.split(start, 1)[1].split(end, 1)[0]


def test_quote_editors_use_fixed_content_height_and_reflow_on_resize():
    editor_class = _section("class _AutoHeightQuoteEdit(QTextEdit):", "\ndef _build_chart_quote_editor(")
    builder = _section("def _build_chart_quote_editor(", "\ndef render_chart_view_quotes(")
    assert "QSizePolicy.Expanding, QSizePolicy.Fixed" in editor_class
    assert "self.setLineWrapMode(QTextEdit.WidgetWidth)" in editor_class
    assert "self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)" in editor_class
    assert "self.textChanged.connect(self._sync_height)" in editor_class
    assert "def resizeEvent(self, event)" in editor_class
    assert "document.setTextWidth(viewport.width())" in editor_class
    assert "document.size().height()" in editor_class
    assert "self.setFixedHeight(needed_height)" in editor_class
    assert "editor = _AutoHeightQuoteEdit()" in builder
    assert "editor.setMinimumHeight(56)" not in builder


def test_quote_list_stacks_in_a_scrolling_viewport_when_too_tall():
    setup = _section("def setup_chart_view_quotes_section(", "\ndef setup_chart_view_tags_section(")
    assert "owner.chart_quotes_list_layout.setSpacing(6)" in setup
    assert "owner.chart_quotes_list_layout.setAlignment(Qt.AlignTop)" in setup
    assert "owner.chart_quotes_list_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)" in setup
    assert "owner.chart_quotes_scroll_area = QScrollArea()" in setup
    assert "owner.chart_quotes_scroll_area.setWidgetResizable(True)" in setup
    assert "owner.chart_quotes_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in setup
    assert "owner.chart_quotes_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)" in setup
    assert "owner.chart_quotes_scroll_area.setWidget(owner.chart_quotes_list_widget)" in setup
    assert "quotes_content_layout.addWidget(owner.chart_quotes_scroll_area, 1)" in setup
    assert setup.index("quotes_content_layout.addLayout(quote_row)") < setup.index("quotes_content_layout.addWidget(owner.chart_quotes_scroll_area, 1)")
    assert "quotes_content_layout.addWidget(owner.chart_quotes_list_widget, 0, Qt.AlignTop)" not in setup


def test_quote_editing_still_marks_metadata_dirty_and_persists_text():
    builder = _section("def _build_chart_quote_editor(", "\ndef render_chart_view_quotes(")
    getter = _section("def get_chart_view_quotes(", "\ndef set_chart_view_quote_state(")
    assert "editor.textChanged.connect(owner._mark_lucygoosey)" in builder
    assert "editor.toPlainText().strip()" in getter
