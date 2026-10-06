"""UID-owned acknowledgement of Database View refresh snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, MutableMapping


@dataclass(frozen=True, eq=False)
class PendingChartChange:
    """Each recorded change has a distinct identity, including repeated edits."""

    refresh_metrics: bool

    def __bool__(self) -> bool:
        return self.refresh_metrics


@dataclass(frozen=True)
class PendingChartRefreshSnapshot:
    changed_uids: Mapping[str, PendingChartChange]
    full_refresh_token: object | None


def acknowledge_refresh_snapshot(
    pending: MutableMapping[str, PendingChartChange],
    full_refresh_token: object | None,
    snapshot: PendingChartRefreshSnapshot,
) -> bool:
    """Remove captured work; return whether its full-refresh flag can be cleared.

    Comparing change identities keeps newer work even when the same UID and
    metrics requirement were recorded again while a refresh was pending.
    """
    for uid, captured_change in snapshot.changed_uids.items():
        if pending.get(uid) is captured_change:
            pending.pop(uid)
    return (
        snapshot.full_refresh_token is not None
        and full_refresh_token is snapshot.full_refresh_token
    )
