import pycountry
import unicodedata
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLDR_PATH = os.path.join(
    BASE_DIR,
    "data",
    "cldr",
    "cldr-json",
    "cldr-localenames",
    "main"
)

OUTPUT_PATH = "ephemeraldaddy/data/compiled/country_data.json"


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def build_iso_base():
    iso2_to_meta = {}
    alias_to_iso2 = {}

    for country in pycountry.countries:
        iso2 = country.alpha_2

        iso2_to_meta[iso2] = {
            "alpha_2": country.alpha_2,
            "alpha_3": country.alpha_3,
            "numeric": country.numeric,
            "name": country.name,
            "official_name": getattr(country, "official_name", None),
            "common_name": getattr(country, "common_name", None),
        }

        base_aliases = {
            country.alpha_2,
            country.alpha_3,
            country.name,
        }

        if hasattr(country, "official_name"):
            base_aliases.add(country.official_name)

        if hasattr(country, "common_name"):
            base_aliases.add(country.common_name)

        for alias in base_aliases:
            alias_to_iso2[normalize(alias)] = iso2

    return iso2_to_meta, alias_to_iso2


def load_cldr_aliases(cldr_root_path):
    alias_to_iso2 = {}

    for locale in os.listdir(cldr_root_path):
        locale_dir = os.path.join(cldr_root_path, locale)

        if not os.path.isdir(locale_dir):
            continue

        territories_file = os.path.join(locale_dir, "territories.json")
        if not os.path.exists(territories_file):
            continue

        with open(territories_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            territories = data["main"][locale]["localeDisplayNames"]["territories"]
        except KeyError:
            continue

        for iso2, name in territories.items():
            if len(iso2) != 2:
                continue
            alias_to_iso2[normalize(name)] = iso2

    return alias_to_iso2


HUMAN_ALIASES = {
    "america": "US",
    "britain": "GB",
    "holland": "NL",
    "dprk": "KP",
    "nippon": "JP",
    "zhongguo": "CN",
    "turkiye": "TR",
}


COUNTRY_OVERRIDES = {
    "TW": {
        "name": "Taiwan",
        "official_name": "Taiwan",
        "common_name": "Taiwan",
    },
}


def merge_aliases(base_aliases, new_aliases):
    for alias, iso2 in new_aliases.items():
        base_aliases[normalize(alias)] = iso2
    return base_aliases


def main():
    print("Building ISO base...")
    iso_meta, aliases = build_iso_base()

    print("Loading CLDR aliases...")
    cldr_aliases = load_cldr_aliases(CLDR_PATH)

    aliases = merge_aliases(aliases, cldr_aliases)
    aliases = merge_aliases(aliases, HUMAN_ALIASES)

    for iso2, overrides in COUNTRY_OVERRIDES.items():
        if iso2 in iso_meta:
            iso_meta[iso2].update(overrides)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    print("Writing compiled file...")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "iso_meta": iso_meta,
                "aliases": aliases,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("Done.")
    print(f"Total countries: {len(iso_meta)}")
    print(f"Total aliases: {len(aliases)}")


if __name__ == "__main__":
    main()
