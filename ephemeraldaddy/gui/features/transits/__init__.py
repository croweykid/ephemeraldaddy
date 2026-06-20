"""Transit View feature helpers and controllers."""

from .cache import TransitWindowCache

__all__ = ["TransitPanelController", "TransitWindowCache"]


def __getattr__(name: str):
    if name == "TransitPanelController":
        from .controller import TransitPanelController

        return TransitPanelController
    raise AttributeError(name)
