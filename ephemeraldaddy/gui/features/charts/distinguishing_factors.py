"""Compatibility facade; remove after remaining chart-info imports migrate."""
from ephemeraldaddy.analysis import distinguishing_factors as _analysis
for _name in dir(_analysis):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_analysis, _name)

def build_distinguishing_factors_html(*args, **kwargs):
    from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR
    kwargs.setdefault("highlight_color", CHART_DATA_HIGHLIGHT_COLOR)
    return _analysis.build_distinguishing_factors_html(*args, **kwargs)
