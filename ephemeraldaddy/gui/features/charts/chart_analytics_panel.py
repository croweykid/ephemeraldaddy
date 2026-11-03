"""Chart View chart analytics panel rendering helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable


if TYPE_CHECKING:
    from ephemeraldaddy.core.chart import Chart

BODY_DYNAMICS_AXIS_LABEL_COLORS: dict[str, str] = {
    "enabler": "#6be39d",
    "antagonist": "#ff6b6b",
    "escalator": "#ffbd59",
}


def normalize_body_dynamics_role_label(value: object) -> str | None:
    """Normalize stored/UI Body Dynamics labels into chart-axis role keys."""
    text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    if not text:
        return None
    if text in {"enabler", "enabling", "enabling influence"}:
        return "enabler"
    if text in {"antagonist", "antagonizer", "antagonizing", "antagonizing influence"}:
        return "antagonist"
    if text.startswith("escalat") or " escalating" in f" {text}":
        return "escalator"
    return None


def _body_dynamics_role_from_scores(body_scores: dict[str, Any] | None) -> str:
    """Classify one body's dynamics scores into an axis-label role."""
    scores = body_scores or {}
    enabling = float(scores.get("enabling", 0.0))
    antagonizing = float(scores.get("antagonizing", 0.0))
    escalating = float(scores.get("escalating", 0.0))
    if escalating > enabling and escalating > antagonizing:
        return "escalator"
    if antagonizing > enabling:
        return "antagonist"
    return "enabler"


def body_dynamics_roles_for_chart(chart: Chart) -> dict[str, str]:
    """Resolve selected-mode roles before coloring Dominant Bodies labels."""
    from ephemeraldaddy.core.db import current_body_dynamics_roles_for_chart

    return current_body_dynamics_roles_for_chart(chart)

def dominant_body_axis_label_color(role: str | None) -> str | None:
    """Return the Chart View Dominant Bodies axis-label color for a role."""
    return BODY_DYNAMICS_AXIS_LABEL_COLORS.get(role or "")


def style_dominant_body_axis_labels(ax: Any, chart: Chart, bodies: Iterable[str]) -> None:
    """Color and preserve pick metadata for Dominant Bodies X-axis labels."""
    body_dynamics_roles = body_dynamics_roles_for_chart(chart)
    for tick_label, body in zip(ax.get_xticklabels(), bodies, strict=True):
        tick_label.set_gid(f"body:{body}")
        tick_label.set_picker(5)
        role_color = dominant_body_axis_label_color(body_dynamics_roles.get(body))
        if role_color:
            tick_label.set_color(role_color)
