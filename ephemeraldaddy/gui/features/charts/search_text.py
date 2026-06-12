"""Helpers for Database View free-text search matching."""

from __future__ import annotations


def database_search_text_is_active(search_text: str | None) -> bool:
    """Return whether the Database View free-text search should filter rows.

    Do not trim whitespace here: leading, trailing, and repeated spaces are part
    of the user's query and should participate in matching.
    """

    return bool(search_text)


def database_search_text_matches(search_text: str | None, value: str | None) -> bool:
    """Return whether ``value`` contains ``search_text`` case-insensitively.

    Whitespace is intentionally preserved so a query such as ``"Al "`` only
    matches strings containing that trailing space, rather than behaving like
    ``"Al"``.
    """

    if not database_search_text_is_active(search_text) or not value:
        return False
    return str(search_text).casefold() in str(value).casefold()
