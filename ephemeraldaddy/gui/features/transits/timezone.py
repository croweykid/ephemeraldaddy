"""Timezone policy for user-entered transit dates and their presentation."""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def local_transit_timezone() -> datetime.tzinfo:
    """Return the local timezone, preserving its DST rules when discoverable.

    ``datetime.now().astimezone().tzinfo`` is only the offset in effect at the
    instant it is called on some platforms.  Applying that fixed offset to a
    user-selected date in another DST season changes the instant represented by
    the transit controls.  Prefer the host's IANA zone and retain the fixed
    offset only as a last-resort fallback.
    """

    candidates: list[str] = []
    configured = os.environ.get("TZ", "").strip().removeprefix(":")
    if configured:
        candidates.append(configured)

    try:
        localtime_target = Path("/etc/localtime").resolve()
        parts = localtime_target.parts
        zoneinfo_index = parts.index("zoneinfo")
        candidates.append("/".join(parts[zoneinfo_index + 1 :]))
    except (OSError, RuntimeError, ValueError):
        pass

    try:
        candidates.append(Path("/etc/timezone").read_text(encoding="utf-8").strip())
    except OSError:
        pass

    for candidate in candidates:
        if not candidate or candidate.startswith("/"):
            continue
        try:
            return ZoneInfo(candidate)
        except (ZoneInfoNotFoundError, ValueError):
            continue

    return datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
