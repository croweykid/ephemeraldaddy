"""Similarities Analysis feature package.

This package centralizes the UI/controller surface for the Manage Charts
Similarities Analysis panel while preserving the existing calculation helpers
in their original modules during the migration.
"""

from .controller import SimilaritiesController

__all__ = ["SimilaritiesController"]
