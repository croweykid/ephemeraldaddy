from __future__ import annotations

from datetime import date
from urllib.parse import quote

from .models import BatchImportRow, BatchImportSeed


class WebProfileLookupService:
    """Sequential provider coordinator; provider callables are injectable for tests."""

    def __init__(self, *, astro_search=None, astro_parse=None, wiki_resolve=None, wiki_birth=None, wiki_blurb=None, wiki_match=None):
        if astro_search is None:
            from ephemeraldaddy.gui.astrotheme_search import search_astrotheme_profile_url as astro_search, parse_astrotheme_profile as astro_parse
        if wiki_resolve is None:
            from ephemeraldaddy.gui.wikipedia_search import resolve_wikipedia_page_options as wiki_resolve, parse_wikipedia_available_birth_data as wiki_birth
        if wiki_blurb is None:
            from ephemeraldaddy.gui.wikipedia_blurb_getter import fetch_wikipedia_blurb as wiki_blurb, unique_title_matching_birth_date as wiki_match
        self.astro_search, self.astro_parse = astro_search, astro_parse
        self.wiki_resolve, self.wiki_birth = wiki_resolve, wiki_birth
        self.wiki_blurb, self.wiki_match = wiki_blurb, wiki_match

    def lookup(self, seed: BatchImportSeed) -> BatchImportRow:
        row = BatchImportRow(seed.name, seed.name, alias=seed.alias, from_whence=seed.from_whence, tags=list(seed.tags), notes=seed.notes)
        factual_date = None
        try:
            url = self.astro_search(seed.name)
            profile = self.astro_parse(url)
            row.name = str(profile.get("name") or seed.name)
            factual_date = date(int(profile["birth_year"]), int(profile["birth_month"]), int(profile["birth_day"]))
            row.birth_date = factual_date.isoformat()
            row.birth_time = "" if profile.get("time_unknown") else f'{int(profile["birth_hour"]):02d}:{int(profile["birth_minute"]):02d}'
            row.birth_place = str(profile.get("birth_place") or "")
            row.data_rating = str(profile.get("data_rating") or "")
            row.biography = str(profile.get("biography") or "")
            row.sources.append(str(profile.get("profile_url") or url))
        except Exception as exc:
            row.warnings.append(f"Astrotheme: {exc}")

        try:
            resolution = self.wiki_resolve(seed.name)
            status = resolution.get("status")
            title = resolution.get("title")
            if status == "multiple":
                options = list(resolution.get("options") or [])
                title = self.wiki_match(options, factual_date) if factual_date else None
                if not title:
                    row.blocking_errors.append("Multiple Wikipedia entries found: " + "; ".join(options))
                    return row
            if status == "not_found":
                if not factual_date: row.blocking_errors.append("No Astrotheme profile or Wikipedia article found.")
                return row
            if title:
                if not factual_date:
                    birth = self.wiki_birth(title)
                    year, month, day = birth.get("birth_year"), birth.get("birth_month"), birth.get("birth_day")
                    if year and month and day: row.birth_date = date(int(year), int(month), int(day)).isoformat()
                    row.birth_place = str(birth.get("birth_place") or row.birth_place)
                    row.name = str(title)
                    row.birth_time = ""
                row.sources.append("https://en.wikipedia.org/wiki/" + quote(str(title).replace(" ", "_")))
                try:
                    blurb = self.wiki_blurb(str(title))
                    text = getattr(blurb, "text", None) or (blurb.get("text") if isinstance(blurb, dict) else None)
                    if text: row.biography = str(text)
                except Exception as exc:
                    row.warnings.append(f"Wikipedia biography: {exc}")
        except Exception as exc:
            row.warnings.append(f"Wikipedia: {exc}")
            if not factual_date: row.blocking_errors.append("No profile could be resolved.")
        return row
