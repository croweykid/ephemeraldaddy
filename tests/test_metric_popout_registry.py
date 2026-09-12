from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.metric_popout_registry import (
    METRIC_PANEL_SPECS_BY_TITLE,
    build_metric_popout_figure,
    configure_metric_popout_info,
    metric_panel_spec_for_title,
)


class DummyOwner:
    def __init__(self):
        self.drawn = []
        self._chart_analysis_chart_dropdowns = {}

    def _draw_house_tally(self, ax, chart):
        self.drawn.append(("houses", chart))
        ax.set_title("houses")


class DummyCanvas:
    def __init__(self):
        self.callbacks = {}

    def mpl_connect(self, event_name, callback):
        self.callbacks[event_name] = callback
        return 1


class DummyInfoPanel:
    def __init__(self):
        self.placeholder = ""
        self.html = ""

    def setPlaceholderText(self, text):
        self.placeholder = text

    def setHtml(self, html):
        self.html = html


class DummyArtist:
    def __init__(self, gid):
        self._gid = gid

    def get_gid(self):
        return self._gid


class DummyPickEvent:
    def __init__(self, gid):
        self.artist = DummyArtist(gid)


def _timed_chart():
    return SimpleNamespace(
        birthtime_unknown=False,
        retcon_time_used=False,
        houses=[float(degree) for degree in range(0, 360, 30)],
        positions={
            "Sun": 15.0,
            "Moon": 45.0,
            "Mercury": 105.0,
            "Venus": 195.0,
            "Mars": 285.0,
        },
        aspects=[],
    )


def test_metric_panel_spec_aliases_resolve_to_same_spec():
    assert metric_panel_spec_for_title("Modes") is metric_panel_spec_for_title("Dominant Modes")
    assert metric_panel_spec_for_title("Nakshatra Prevalence") is metric_panel_spec_for_title("Dominant Nakshatras")
    assert metric_panel_spec_for_title("Enneagram") is metric_panel_spec_for_title("💭Enneagram")


def test_elements_and_dominant_elements_preserve_legacy_popout_sizes():
    assert metric_panel_spec_for_title("Elements").popout_size == (8.5, 4.6)
    assert metric_panel_spec_for_title("Dominant Elements").popout_size == (8.0, 5.4)


def test_registered_metric_popout_figure_uses_spec_size_and_draw_callback():
    owner = DummyOwner()
    chart = object()

    figure = build_metric_popout_figure(owner, "Houses", chart, background_color="#101010")

    assert owner.drawn == [("houses", chart)]
    assert tuple(round(value, 1) for value in figure.get_size_inches()) == (8.5, 4.2)
    assert figure.axes[0].get_title() == "houses"


def test_quadrants_popout_is_registered_and_draws_pickable_quadrants():
    owner = DummyOwner()
    chart = _timed_chart()

    spec = metric_panel_spec_for_title("Quadrants")
    figure = build_metric_popout_figure(owner, "Quadrants", chart, background_color="#101010")
    ax = figure.axes[0]

    assert spec is not None
    assert spec.key == "quadrants"
    assert spec.configure_info is not None
    assert ax.get_title() == "Quadrants — Object Count"
    assert [bar.get_gid() for bar in ax.patches] == [
        "quadrant:I",
        "quadrant:II",
        "quadrant:III",
        "quadrant:IV",
    ]
    assert all(bar.get_picker() is True for bar in ax.patches)
    assert [label.get_gid() for label in ax.get_xticklabels()] == [
        "quadrant:I",
        "quadrant:II",
        "quadrant:III",
        "quadrant:IV",
    ]
    assert all(label.get_picker() is True for label in ax.get_xticklabels())


def test_quadrants_popout_pick_updates_interpretation_panel():
    owner = DummyOwner()
    chart = _timed_chart()
    canvas = DummyCanvas()
    info_panel = DummyInfoPanel()

    configure_metric_popout_info(owner, "Quadrants", canvas, info_panel, chart)
    canvas.callbacks["pick_event"](DummyPickEvent("quadrant:I"))

    assert "Click a quadrant" in info_panel.placeholder
    assert "Quadrant I" in info_panel.html
    assert "Personal Identity" in info_panel.html
    assert "Houses 1–3" in info_panel.html


def test_all_registered_metric_titles_have_unique_lookup_entries():
    registered_titles = {title for title, spec in METRIC_PANEL_SPECS_BY_TITLE.items() if title in spec.titles}

    assert registered_titles == set(METRIC_PANEL_SPECS_BY_TITLE)
    assert "Body Dynamics" in registered_titles
    assert "Quadrants" in registered_titles
