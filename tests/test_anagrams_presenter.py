import sys
import types
from types import SimpleNamespace


def _install_pyside_stubs():
    pyside = types.ModuleType("PySide6")
    qt_core = types.ModuleType("PySide6.QtCore")
    qt_gui = types.ModuleType("PySide6.QtGui")
    qt_widgets = types.ModuleType("PySide6.QtWidgets")

    class _SignalBlocker:
        def __init__(self, *_args, **_kwargs):
            pass

    class _Qt:
        DownArrow = 1
        RightArrow = 2
        PointingHandCursor = 3
        RichText = 4
        TextBrowserInteraction = 5
        TextSelectableByMouse = 6
        AlignLeft = 7
        AlignRight = 8

    class _Widget:
        def __init__(self, *_args, **_kwargs):
            pass

    class _SizePolicy:
        Expanding = 1
        Maximum = 2

    qt_core.QSignalBlocker = _SignalBlocker
    qt_core.Qt = _Qt
    qt_gui.QIcon = _Widget
    for name in (
        "QComboBox",
        "QFrame",
        "QLabel",
        "QVBoxLayout",
        "QWidget",
        "QHBoxLayout",
        "QToolButton",
    ):
        setattr(qt_widgets, name, _Widget)
    qt_widgets.QSizePolicy = _SizePolicy

    sys.modules.setdefault("PySide6", pyside)
    sys.modules.setdefault("PySide6.QtCore", qt_core)
    sys.modules.setdefault("PySide6.QtGui", qt_gui)
    sys.modules.setdefault("PySide6.QtWidgets", qt_widgets)


def _install_style_stub():
    style = types.ModuleType("ephemeraldaddy.gui.style")
    style.DATABASE_ANALYTICS_DROPDOWN_STYLE = ""
    style.DATABASE_ANALYTICS_SUBHEADER_STYLE = ""
    style.DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE = ""
    style.ABC_PANEL_SECTION_CONTENT_MARGINS = (0, 0, 0, 0)
    style.ABC_PANEL_SECTION_CONTENT_SPACING = 0
    style.ABC_PANEL_SECTION_FRAME_MARGINS = (0, 0, 0, 0)
    style.ABC_PANEL_SECTION_FRAME_SPACING = 0
    style.ABC_PANEL_SECTION_FRAME_STYLE = ""

    def apply_button_cursor(*_args, **_kwargs):
        pass

    def apply_shared_dropdown_style(*_args, **_kwargs):
        pass

    def configure_collapsible_header_toggle(*_args, **_kwargs):
        pass

    style.apply_button_cursor = apply_button_cursor
    style.apply_shared_dropdown_style = apply_shared_dropdown_style
    style.configure_collapsible_header_toggle = configure_collapsible_header_toggle
    sys.modules.setdefault("ephemeraldaddy.gui.style", style)


_install_pyside_stubs()
_install_style_stub()
from ephemeraldaddy.gui.features.charts import anagrams


class FakeWidget:
    def __init__(self):
        self.update_geometry_calls = 0
        self.adjust_size_calls = 0

    def updateGeometry(self):
        self.update_geometry_calls += 1

    def adjustSize(self):
        self.adjust_size_calls += 1


class FakeLabel(FakeWidget):
    def __init__(self, text=""):
        super().__init__()
        self.text = text
        self.visible = True

    def setText(self, text):
        self.text = text

    def clear(self):
        self.text = ""

    def setVisible(self, visible):
        self.visible = visible


class FakeDropdown:
    def __init__(self):
        self.items = []
        self.current_index = -1

    def clear(self):
        self.items.clear()

    def addItem(self, label, data):
        self.items.append((label, data))

    def findData(self, data):
        for index, (_label, item_data) in enumerate(self.items):
            if item_data == data:
                return index
        return -1

    def setCurrentIndex(self, index):
        self.current_index = index

    def setMinimumWidth(self, _width):
        pass

    def sizeHint(self):
        return SimpleNamespace(width=lambda: 100)



def test_render_anagrams_html_can_show_multiple_inline_definitions():
    rendered = anagrams.render_anagrams_html(
        "Listen",
        ["listen", "silent"],
        clicked_definitions={
            "listen": "to hear attentively",
            "silent": "making no sound",
        },
    )

    assert 'href="define:listen"' in rendered
    assert 'href="define:silent"' in rendered
    assert "Click a word to show or hide its definition" in rendered
    assert "listen</a><span" in rendered
    assert "to hear attentively" in rendered
    assert "silent</a><span" in rendered
    assert "making no sound" in rendered


def test_chart_identity_options_split_comma_delimited_name_and_alias():
    chart = SimpleNamespace(name="First Name, Second Name", alias="Alias One, Alias Two")

    assert anagrams.chart_identity_options(chart) == [
        ("First Name", "name:0", "First Name"),
        ("Second Name", "name:1", "Second Name"),
        ("Alias One", "alias:0", "Alias One"),
        ("Alias Two", "alias:1", "Alias Two"),
    ]


def test_presenter_dropdown_uses_actual_name_and_alias_values():
    dropdown = FakeDropdown()
    widgets = anagrams.AnagramsSectionWidgets(
        summary_label=FakeLabel(),
        list_label=FakeLabel(),
        definition_label=FakeLabel(),
        export_button=object(),
        source_dropdown=dropdown,
        container=FakeWidget(),
    )
    presenter = anagrams.AnagramsPresenter(widgets)
    chart = SimpleNamespace(name="Name A, Name B", alias="Alias A, Alias B")

    presenter.sync_source_options(chart)

    assert dropdown.items == [
        ("Name A", "name:0"),
        ("Name B", "name:1"),
        ("Alias A", "alias:0"),
        ("Alias B", "alias:1"),
    ]


def test_definition_clicked_toggles_inline_detail_and_rerenders_word_list(monkeypatch):
    list_label = FakeLabel("original clickable word list")
    definition_label = FakeLabel()
    definition_label.visible = False
    widgets = anagrams.AnagramsSectionWidgets(
        summary_label=FakeLabel(),
        list_label=list_label,
        definition_label=definition_label,
        export_button=object(),
        source_dropdown=FakeDropdown(),
        container=FakeWidget(),
    )
    presenter = anagrams.AnagramsPresenter(widgets)
    presenter.state.current_words = ["listen"]
    presenter.state.current_chart_text = "Listen"

    monkeypatch.setattr(anagrams, "fetch_word_definition", lambda _word: "to hear attentively")

    assert presenter.definition_clicked("define:listen") is True
    assert "listen</a><span" in list_label.text
    assert "to hear attentively" in list_label.text
    assert definition_label.visible is False
    assert definition_label.text == ""
    assert presenter.state.clicked_definitions == {"listen": "to hear attentively"}

    assert presenter.definition_clicked("define:listen") is True
    assert "to hear attentively" not in list_label.text
    assert presenter.state.clicked_definitions == {}
    assert definition_label.update_geometry_calls == 2
    assert widgets.container.update_geometry_calls == 4

class FakeDefinitionResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeDefinitionSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, **_kwargs):
        self.urls.append(url)
        return self.responses.pop(0)


def test_fetch_word_definition_ignores_dictionary_api_spelling_substitutions(monkeypatch):
    anagrams.fetch_word_definition.cache_clear()
    session = FakeDefinitionSession(
        [
            FakeDefinitionResponse(
                200,
                [
                    {
                        "word": "antitumor",
                        "meanings": [
                            {"definitions": [{"definition": "Acting against tumors."}]}
                        ],
                    }
                ],
            ),
            FakeDefinitionResponse(200, []),
        ]
    )
    monkeypatch.setattr(anagrams, "_DEFINITION_HTTP_SESSION", session)

    try:
        assert anagrams.fetch_word_definition("antirumor") == "Definition unavailable."
    finally:
        anagrams.fetch_word_definition.cache_clear()


def test_fetch_word_definition_ignores_datamuse_spelling_suggestions(monkeypatch):
    anagrams.fetch_word_definition.cache_clear()
    session = FakeDefinitionSession(
        [
            FakeDefinitionResponse(404, {}),
            FakeDefinitionResponse(
                200,
                [{"word": "antitumor", "defs": ["adj\tActing against tumors."]}],
            ),
        ]
    )
    monkeypatch.setattr(anagrams, "_DEFINITION_HTTP_SESSION", session)

    try:
        assert anagrams.fetch_word_definition("antirumor") == "Definition unavailable."
    finally:
        anagrams.fetch_word_definition.cache_clear()
