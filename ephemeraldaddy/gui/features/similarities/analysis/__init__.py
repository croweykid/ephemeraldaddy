"""Database View Similarities Analysis panel and calculations."""

__all__ = ["SimilaritiesController"]


def __getattr__(name: str):
    if name == "SimilaritiesController":
        from .cohort_controller import SimilaritiesController

        return SimilaritiesController
    raise AttributeError(name)
