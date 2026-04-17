from __future__ import annotations

import re
from typing import Any


HTTP_URL_PATTERN = re.compile(r"http://\S+", re.IGNORECASE)


def move_alias_to_from_whence(chart: Any) -> bool:
    alias_value = str(getattr(chart, "alias", "") or "").strip()
    if not alias_value:
        return False
    chart.from_whence = alias_value
    chart.alias = ""
    return True


def migrate_comment_urls_to_source(chart: Any) -> int:
    comments = str(getattr(chart, "comments", "") or "")
    if not comments:
        return 0

    matches = [match.group(0) for match in HTTP_URL_PATTERN.finditer(comments)]
    if not matches:
        return 0

    existing_source = str(getattr(chart, "chart_data_source", "") or "").strip()
    source_parts = [part.strip() for part in existing_source.splitlines() if part.strip()]
    for url in matches:
        if url not in source_parts:
            source_parts.append(url)

    updated_comments = comments
    for url in matches:
        updated_comments = updated_comments.replace(url, "")

    chart.chart_data_source = "\n".join(source_parts)
    chart.comments = updated_comments
    return len(matches)
