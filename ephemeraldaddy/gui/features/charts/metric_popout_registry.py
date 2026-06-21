"""Registry for Chart View metric popout figures and info-panel behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from matplotlib.figure import Figure

Chart = Any
Owner = Any
Axis = Any
Canvas = Any
InfoPanel = Any

DrawMetric = Callable[[Owner, Axis, Chart], None]
ConfigureInfo = Callable[[Owner, Canvas, InfoPanel, Chart], None]


def _call_draw(method_name: str) -> DrawMetric:
    def _draw(owner: Owner, ax: Axis, chart: Chart) -> None:
        getattr(owner, method_name)(ax, chart)

    return _draw


@dataclass(frozen=True)
class MetricPanelSpec:
    """One registered metric-popout chart and its interactive info behavior."""

    key: str
    title: str
    draw: DrawMetric
    popout_size: tuple[float, float] = (8.5, 4.6)
    configure_info: ConfigureInfo | None = None
    placeholder: str | None = None
    aliases: tuple[str, ...] = ()
    cache_key: str | None = None

    @property
    def titles(self) -> tuple[str, ...]:
        return (self.title, *self.aliases)


def _artist_gid(event: object) -> str | None:
    artist = getattr(event, "artist", None)
    artist_gid = artist.get_gid() if artist is not None else None
    return artist_gid if isinstance(artist_gid, str) and artist_gid else None


def _configure_gid_info(
    expected_keys: set[str],
    builders: dict[str, Callable[[Owner, Chart, str], str]],
    *,
    int_keys: set[str] | None = None,
) -> ConfigureInfo:
    int_keys = int_keys or set()

    def _configure(owner: Owner, canvas: Canvas, info_panel: InfoPanel, chart: Chart) -> None:
        def _on_pick(event: object) -> None:
            artist_gid = _artist_gid(event)
            if artist_gid is None or ":" not in artist_gid:
                return
            chart_key, raw_value = artist_gid.split(":", 1)
            if chart_key not in expected_keys:
                return
            if chart_key in int_keys:
                try:
                    value: Any = int(raw_value)
                except ValueError:
                    return
            else:
                value = raw_value
            info_panel.setHtml(builders[chart_key](owner, chart, value))

        canvas.mpl_connect("pick_event", _on_pick)

    return _configure


def _configure_nakshatra(owner: Owner, canvas: Canvas, info_panel: InfoPanel, chart: Chart) -> None:
    def _on_pick(event: object) -> None:
        nakshatra_name = _artist_gid(event)
        if nakshatra_name is None:
            return
        info_panel.setHtml(owner._build_nakshatra_popout_info(chart, nakshatra_name))

    canvas.mpl_connect("pick_event", _on_pick)


def _configure_enneagram(owner: Owner, canvas: Canvas, info_panel: InfoPanel, chart: Chart) -> None:
    from ephemeraldaddy.gui.features.charts.enneagram_predictions import connect_enneagram_popout_pick_handler

    connect_enneagram_popout_pick_handler(
        canvas,
        info_panel,
        build_info_html=lambda enneagram_type: owner._build_enneagram_popout_info(
            enneagram_type,
            chart=chart,
        ),
    )


def _configure_dnd(owner: Owner, canvas: Canvas, info_panel: InfoPanel, chart: Chart) -> None:
    from ephemeraldaddy.gui.features.charts.dnd_predictions import connect_dnd_statblock_popout_pick_handler

    connect_dnd_statblock_popout_pick_handler(
        canvas,
        info_panel,
        build_info_html=lambda stat_key: owner._build_dnd_statblock_popout_info(
            stat_key,
            chart=chart,
        ),
    )


def _configure_gender_guesser(owner: Owner, canvas: Canvas, info_panel: InfoPanel, chart: Chart) -> None:
    del owner, canvas
    from ephemeraldaddy.gui.features.charts.algorithmic_transparency import build_gender_guesser_breakdown_text

    info_panel.setPlainText(build_gender_guesser_breakdown_text(chart))


def _configure_body_dynamics(owner: Owner, canvas: Canvas, info_panel: InfoPanel, chart: Chart) -> None:
    def _on_pick(event: object) -> None:
        artist_gid = _artist_gid(event)
        if artist_gid is None or not artist_gid.startswith("dynamics:"):
            return
        _, metric, target = artist_gid.split(":", 2)
        info_panel.setHtml(owner._build_body_dynamics_popout_info(chart, metric, target))

    canvas.mpl_connect("pick_event", _on_pick)


METRIC_PANEL_SPECS: tuple[MetricPanelSpec, ...] = (
    MetricPanelSpec(
        key="signs",
        title="Signs",
        draw=_call_draw("_draw_sign_tally"),
        popout_size=(8.5, 4.2),
        placeholder="Click a bar or label to view interpretation details.",
        configure_info=_configure_gid_info(
            {"sign"},
            {"sign": lambda owner, chart, value: owner._build_sign_popout_info(chart, value)},
        ),
        cache_key="chart-analysis:dominant_signs",
    ),
    MetricPanelSpec(
        key="bodies",
        title="Bodies",
        draw=_call_draw("_draw_planet_tally"),
        popout_size=(8.5, 4.2),
        placeholder="Click a bar or label to view interpretation details.",
        configure_info=_configure_gid_info(
            {"body"},
            {"body": lambda owner, chart, value: owner._build_body_popout_info(chart, value)},
        ),
        cache_key="chart-analysis:dominant_planets",
    ),
    MetricPanelSpec(
        key="houses",
        title="Houses",
        draw=_call_draw("_draw_house_tally"),
        popout_size=(8.5, 4.2),
        placeholder="Click a bar or label to view interpretation details.",
        configure_info=_configure_gid_info(
            {"house"},
            {"house": lambda owner, chart, value: owner._build_house_popout_info(chart, value)},
            int_keys={"house"},
        ),
        cache_key="chart-analysis:dominant_houses",
    ),
    MetricPanelSpec(
        key="enneagram",
        title="Enneagram",
        draw=_call_draw("_draw_enneagram_predictions"),
        popout_size=(8.5, 4.2),
        placeholder="Click an Enneagram bar to view type motivation and interpretation details.",
        configure_info=_configure_enneagram,
    ),
    MetricPanelSpec(
        key="dnd_statblock",
        title="D&D Statblock",
        draw=_call_draw("_draw_dnd_statblock_predictions"),
        popout_size=(8.5, 4.2),
        placeholder="Click a stat bar to view what that D&D ability score suggests.",
        configure_info=_configure_dnd,
    ),
    MetricPanelSpec(
        key="elements",
        title="Elements",
        aliases=("Dominant Elements",),
        draw=_call_draw("_draw_element_tally"),
        popout_size=(8.0, 5.4),
        placeholder="Click an element label or pie segment to view interpretation details.",
        configure_info=_configure_gid_info(
            {"element"},
            {"element": lambda owner, chart, value: owner._build_element_popout_info(chart, value)},
        ),
        cache_key="chart-analysis:dominant_elements",
    ),
    MetricPanelSpec(
        key="nakshatras",
        title="Nakshatra Prevalence",
        aliases=("Dominant Nakshatras",),
        draw=_call_draw("_draw_nakshatra_wordcloud"),
        popout_size=(9.0, 6.6),
        placeholder="Click a nakshatra label or bar to view its description.",
        configure_info=_configure_nakshatra,
        cache_key="chart-analysis:nakshatra_prevalence",
    ),
    MetricPanelSpec(
        key="modes",
        title="Modes",
        aliases=("Dominant Modes", "Modal Prevalence"),
        draw=_call_draw("_draw_modal_distribution"),
        popout_size=(8.0, 5.4),
        placeholder="Click a mode label or pie segment to view interpretation details.",
        configure_info=_configure_gid_info(
            {"mode"},
            {"mode": lambda owner, chart, value: owner._build_mode_popout_info(chart, value)},
        ),
        cache_key="chart-analysis:modal_distribution",
    ),
    MetricPanelSpec(
        key="gender_guesser",
        title="Gender Guesser",
        draw=_call_draw("_draw_gender_guesser"),
        popout_size=(8.0, 4.2),
        configure_info=_configure_gender_guesser,
    ),
    MetricPanelSpec(
        key="body_dynamics",
        title="Body Dynamics",
        draw=_call_draw("_draw_planet_dynamics"),
        popout_size=(8.5, 5.0),
        placeholder="Click a bar section to view a plain-English score breakdown.",
        configure_info=_configure_body_dynamics,
        cache_key="chart-analysis:body_dynamics",
    ),
)

METRIC_PANEL_SPECS_BY_TITLE: dict[str, MetricPanelSpec] = {
    title: spec for spec in METRIC_PANEL_SPECS for title in spec.titles
}


def metric_panel_spec_for_title(title: str) -> MetricPanelSpec | None:
    return METRIC_PANEL_SPECS_BY_TITLE.get(str(title or ""))


def build_metric_popout_figure(owner: Owner, title: str, chart: Chart, *, background_color: str) -> Figure:
    spec = metric_panel_spec_for_title(title)
    figure = Figure(figsize=spec.popout_size if spec is not None else (8.5, 4.6))
    figure.patch.set_facecolor(background_color)
    ax = figure.add_subplot(111)
    ax.set_facecolor(background_color)
    if spec is not None:
        spec.draw(owner, ax, chart)
    return figure


def configure_metric_popout_info(owner: Owner, title: str, canvas: Canvas, info_panel: InfoPanel, chart: Chart) -> None:
    spec = metric_panel_spec_for_title(title)
    if spec is None:
        return
    if spec.placeholder:
        info_panel.setPlaceholderText(spec.placeholder)
    if spec.configure_info is not None:
        spec.configure_info(owner, canvas, info_panel, chart)
