import re

US_STATE_ABBREVIATIONS = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
    "AS": "American Samoa",
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "PR": "Puerto Rico",
    "UM": "United States Minor Outlying Islands",
    "VI": "U.S. Virgin Islands",
}

_STATE_NAME_TO_ABBREV = {name.lower(): abbrev for abbrev, name in US_STATE_ABBREVIATIONS.items()}
_STATE_NAME_TO_ABBREV.update(
    {
        "us virgin islands": "VI",
        "u.s. virgin islands": "VI",
        "virgin islands": "VI",
    }
)
_TOKEN_SPLIT_PATTERN = re.compile(r"[,\s/|]+")
_ZIP_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")


def normalize_us_state(raw_value: str) -> str | None:
    cleaned = (raw_value or "").strip()
    if not cleaned:
        return None

    upper_cleaned = cleaned.upper()
    if upper_cleaned in US_STATE_ABBREVIATIONS:
        return upper_cleaned

    if cleaned.lower() in _STATE_NAME_TO_ABBREV:
        return _STATE_NAME_TO_ABBREV[cleaned.lower()]

    tokens = [token.strip() for token in _TOKEN_SPLIT_PATTERN.split(cleaned) if token.strip()]
    if not tokens:
        return None

    for token in tokens:
        upper_token = token.upper()
        if upper_token in US_STATE_ABBREVIATIONS:
            return upper_token

    without_zip = _ZIP_PATTERN.sub(" ", cleaned).strip()
    if without_zip and without_zip.lower() in _STATE_NAME_TO_ABBREV:
        return _STATE_NAME_TO_ABBREV[without_zip.lower()]

    lowered = [token.lower() for token in tokens if not token.isdigit()]
    for size in (3, 2, 1):
        if len(lowered) < size:
            continue
        for idx in range(0, len(lowered) - size + 1):
            phrase = " ".join(lowered[idx : idx + size])
            match = _STATE_NAME_TO_ABBREV.get(phrase)
            if match:
                return match

    return None
