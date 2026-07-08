"""Shared helpers for appwide database-norm cache freshness decisions.

The cache users in Database Analytics and Chart View Predictions intentionally
serve stale-but-present norm payloads while background refreshes catch up.  This
module keeps the changed-chart accounting and 10% freshness policy in one place
so individual panels do not invent subtly different invalidation rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

DATABASE_NORMS_CACHE_FILENAME = ".database_norms_cache.json"
DATABASE_NORMS_STALE_RATIO = 0.10


@dataclass(frozen=True)
class DatabaseNormsFreshness:
    """Summary of whether a persisted norm snapshot matches current chart rows."""

    saved_chart_count: int
    current_chart_count: int
    changed_uid_count: int
    refresh_threshold: int

    @property
    def is_exact(self) -> bool:
        return self.changed_uid_count == 0

    @property
    def is_fresh(self) -> bool:
        return self.changed_uid_count < self.refresh_threshold

    @property
    def is_stale(self) -> bool:
        return not self.is_exact and not self.is_fresh

    @property
    def requires_full_refresh(self) -> bool:
        return self.changed_uid_count >= self.refresh_threshold


def database_norms_refresh_threshold(chart_count: int) -> int:
    """Return the changed-chart count that should trigger background refresh."""
    return max(1, int(max(0, int(chart_count)) * DATABASE_NORMS_STALE_RATIO))


def _token_map(tokens: Any) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for item in tokens or ():
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        uid, token = item
        mapped[str(uid)] = str(token)
    return mapped


def changed_database_norm_uids(
    saved_tokens: Any,
    current_tokens: Sequence[tuple[str, str]],
) -> set[str]:
    """Return chart UIDs whose persisted row token is new, deleted, or changed."""
    saved_map = _token_map(saved_tokens)
    current_map = _token_map(current_tokens)
    return {
        uid
        for uid in (set(saved_map) | set(current_map))
        if saved_map.get(uid) != current_map.get(uid)
    }


def database_norms_freshness(
    saved_tokens: Any,
    current_tokens: Sequence[tuple[str, str]],
) -> DatabaseNormsFreshness:
    """Evaluate the appwide stale/fresh policy for a persisted norm snapshot."""
    saved_map = _token_map(saved_tokens)
    current_map = _token_map(current_tokens)
    changed_count = len(changed_database_norm_uids(saved_tokens, current_tokens))
    threshold = database_norms_refresh_threshold(max(len(saved_map), len(current_map)))
    return DatabaseNormsFreshness(
        saved_chart_count=len(saved_map),
        current_chart_count=len(current_map),
        changed_uid_count=changed_count,
        refresh_threshold=threshold,
    )


def analytical_mapping_signature(value: Mapping[str, Any] | None, *, strip_uids: bool = False) -> dict[str, Any]:
    """Remove display-only metadata from a trait/profile-like mapping."""
    if not isinstance(value, Mapping):
        return {}
    excluded = {"name", "color", "description", "motivation", "quotes", "archived", "samples"}
    if strip_uids:
        excluded.update({"uid", "trait_uid"})
    return {str(key): item for key, item in value.items() if str(key) not in excluded}
