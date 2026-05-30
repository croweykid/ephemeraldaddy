import sys
from types import ModuleType, SimpleNamespace


def _install_pyside_stubs():
    pyside = ModuleType("PySide6")
    qtcore = ModuleType("PySide6.QtCore")
    qtgui = ModuleType("PySide6.QtGui")
    qtwidgets = ModuleType("PySide6.QtWidgets")

    class _QEventLoop:
        AllEvents = object()

    class _Qt:
        WindowModal = object()

        def __getattr__(self, _name):
            return object()

    class _QSize:
        def __init__(self, *_args, **_kwargs):
            pass

    class _QApplication:
        @staticmethod
        def processEvents(*_args, **_kwargs):
            return None

    class _Widget:
        Expanding = object()
        Preferred = object()

        def __init__(self, *_args, **_kwargs):
            pass

        def __getattr__(self, _name):
            def _method(*_args, **_kwargs):
                return None
            return _method

    qtcore.QEventLoop = _QEventLoop
    qtcore.Qt = _Qt()
    qtcore.QSize = _QSize
    qtgui.QIcon = _Widget
    qtwidgets.QApplication = _QApplication
    qtwidgets.QAbstractButton = _Widget
    qtwidgets.QComboBox = _Widget
    qtwidgets.QListView = _Widget
    qtwidgets.QListWidget = _Widget
    qtwidgets.QProgressDialog = _Widget
    qtwidgets.QSizePolicy = _Widget
    qtwidgets.QToolButton = _Widget
    qtwidgets.QWidget = _Widget
    sys.modules.setdefault("PySide6", pyside)
    sys.modules.setdefault("PySide6.QtCore", qtcore)
    sys.modules.setdefault("PySide6.QtGui", qtgui)
    sys.modules.setdefault("PySide6.QtWidgets", qtwidgets)


_install_pyside_stubs()

from ephemeraldaddy.gui.features.charts.similarities_analysis import (  # noqa: E402
    build_dissimilarity_export_sections,
)


class FakeDissimilarityProvider:
    def __init__(self, charts):
        self.charts = charts

    def _get_chart_for_filter(self, chart_id):
        return self.charts.get(chart_id)

    def _similarities_body_label(self, body):
        return body

    def _dominant_sign_top_three_labels(self, dominant_weights):
        return set()

    def _dominant_planet_top_three_labels(self, dominant_weights):
        return set()

    def _dominant_house_top_three_labels(self, dominant_weights):
        return set()

    def _extract_human_design_profile(self, chart):
        return [], [], [], [], "", ""

    def _chart_human_design_profile(self, chart):
        return ""

    def _similarity_matching_chart_names(self, section_title, label, chart_ids):
        return ""


def _chart(*, birthtime_unknown, positions, houses=None, bazi_year_pillar=""):
    return SimpleNamespace(
        birthtime_unknown=birthtime_unknown,
        retcon_time_used=False,
        positions=positions,
        houses=houses or [],
        aspects=[],
        dominant_sign_weights={},
        dominant_planet_weights={},
        bazi_year_pillar=bazi_year_pillar,
        bazi_month_pillar="",
        bazi_day_pillar="",
        bazi_hour_pillar="",
    )


def test_dissimilarity_export_sections_exclude_timed_only_contrasts_for_mixed_pair():
    provider = FakeDissimilarityProvider(
        {
            1: _chart(
                birthtime_unknown=False,
                positions={"Sun": 15.0, "Moon": 95.0, "AS": 20.0},
                houses=[index * 30.0 for index in range(12)],
            ),
            2: _chart(
                birthtime_unknown=True,
                positions={"Sun": 45.0, "Moon": 95.0},
            ),
        }
    )

    sections = dict(
        build_dissimilarity_export_sections(
            provider,
            selected_chart_ids=[1, 2],
            db_chart_ids=[1, 2],
            db_total_count=2,
        )
    )

    position_labels = {label for label, *_rest in sections["Signs in positions in contrast"]}
    position_owners = {label: owner for label, *_rest, owner in sections["Signs in positions in contrast"]}
    house_position_labels = {label for label, *_rest in sections["Houses in positions in contrast"]}
    house_sign_labels = {label for label, *_rest in sections["Signs in houses in contrast"]}

    assert position_labels == {"Sun in Aries", "Sun in Taurus"}
    assert position_owners == {"Sun in Aries": "chart_1", "Sun in Taurus": "chart_2"}
    assert "AS in Aries" not in position_labels
    assert house_position_labels == set()
    assert house_sign_labels == set()


def test_dissimilarity_export_sections_include_unique_bazi_signs():
    provider = FakeDissimilarityProvider(
        {
            1: _chart(birthtime_unknown=True, positions={"Sun": 15.0}, bazi_year_pillar="Snake"),
            2: _chart(birthtime_unknown=True, positions={"Sun": 15.0}, bazi_year_pillar="Rat"),
        }
    )

    sections = dict(
        build_dissimilarity_export_sections(
            provider,
            selected_chart_ids=[1, 2],
            db_chart_ids=[1, 2],
            db_total_count=2,
        )
    )

    bazi_matches = sections["BaZi signs in contrast"]
    assert {label for label, *_rest in bazi_matches} == {"Rat", "Snake"}
    assert {label: owner for label, *_rest, owner in bazi_matches} == {
        "Snake": "chart_1",
        "Rat": "chart_2",
    }
