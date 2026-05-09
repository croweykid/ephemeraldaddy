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

    def configure_collapsible_header_toggle(*_args, **_kwargs):
        pass

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
    def clear(self):
        pass

    def addItem(self, *_args):
        pass

    def findData(self, _data):
        return 0

    def setCurrentIndex(self, _index):
        pass

    def setMinimumWidth(self, _width):
        pass

    def sizeHint(self):
        return SimpleNamespace(width=lambda: 100)



def test_render_anagrams_html_keeps_definitions_out_of_clickable_list():
    rendered = anagrams.render_anagrams_html("Listen", ["listen", "silent"])

    assert 'href="define:listen"' in rendered
    assert 'href="define:silent"' in rendered
    assert "Click a word to fetch its definition" in rendered
    assert " — " not in rendered


def test_definition_clicked_updates_stable_detail_without_rerendering_word_list(monkeypatch):
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
    assert list_label.text == "original clickable word list"
    assert definition_label.visible is True
    assert "listen" in definition_label.text
    assert "to hear attentively" in definition_label.text
    assert presenter.state.clicked_definitions == {"listen": "to hear attentively"}
    assert definition_label.update_geometry_calls == 1
    assert widgets.container.update_geometry_calls == 1
