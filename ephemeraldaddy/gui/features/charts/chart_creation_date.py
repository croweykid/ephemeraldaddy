"""Format persisted chart creation timestamps for the Chart View header."""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo


def format_chart_created_at(created_at: str | None, *, display_tz: tzinfo | None = None) -> str:
    """Return a local-date label, or an empty string for an absent/invalid timestamp."""
    if not created_at or not str(created_at).strip():
        return ""
    try:
        saved_at = datetime.fromisoformat(str(created_at).strip().replace("Z", "+00:00"))
    except ValueError:
        return ""
    # Persisted timestamps are UTC. Treat legacy naive timestamps as UTC too.
    if saved_at.tzinfo is None:
        saved_at = saved_at.replace(tzinfo=timezone.utc)
    local_date = saved_at.astimezone(display_tz)
    return f"Created {local_date:%b} {local_date.day}, {local_date.year}"
