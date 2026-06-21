from ephemeraldaddy.gui.features.charts.metric_popout_registry import (
    METRIC_PANEL_SPECS_BY_TITLE,
    build_metric_popout_figure,
    metric_panel_spec_for_title,
)


class DummyOwner:
    def __init__(self):
        self.drawn = []

    def _draw_house_tally(self, ax, chart):
        self.drawn.append(("houses", chart))
        ax.set_title("houses")


def test_metric_panel_spec_aliases_resolve_to_same_spec():
    assert metric_panel_spec_for_title("Modes") is metric_panel_spec_for_title("Dominant Modes")
    assert metric_panel_spec_for_title("Nakshatra Prevalence") is metric_panel_spec_for_title("Dominant Nakshatras")
    assert metric_panel_spec_for_title("Elements") is metric_panel_spec_for_title("Dominant Elements")


def test_registered_metric_popout_figure_uses_spec_size_and_draw_callback():
    owner = DummyOwner()
    chart = object()

    figure = build_metric_popout_figure(owner, "Houses", chart, background_color="#101010")

    assert owner.drawn == [("houses", chart)]
    assert tuple(round(value, 1) for value in figure.get_size_inches()) == (8.5, 4.2)
    assert figure.axes[0].get_title() == "houses"


def test_all_registered_metric_titles_have_unique_lookup_entries():
    registered_titles = {title for title, spec in METRIC_PANEL_SPECS_BY_TITLE.items() if title in spec.titles}

    assert registered_titles == set(METRIC_PANEL_SPECS_BY_TITLE)
    assert "Body Dynamics" in registered_titles
