#!/usr/bin/env python3
"""
Personal-use Astrotheme batch lookup:
- Input: newline-delimited names (names.txt)
- Output: CSV with url + birth date/time/place
- Unknowns are written as "?" (no blanks, no Ns)

Run:
  python astrotheme_lookup.py names.txt results.csv

Deps:
  pip install requests beautifulsoup4 rapidfuzz lxml
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

SEARCH_URL = "https://www.astrotheme.com/celebrities/recherche.php"
USER_AGENT = "Mozilla/5.0 (compatible; personal-use script; +https://chatgpt.com)"
REQUEST_DELAY_SEC = 1.1
CACHE_FILE = "astrotheme_cache.json"
UNKNOWN = "?"


@dataclass
class Candidate:
    name: str
    url: str


@dataclass
class Result:
    input_name: str
    matched_name: str
    astrotheme_url: str
    birth_date: str          # YYYY-MM-DD or "?"
    birth_time: str          # HH:MM (24h) or "?"
    birth_place: str         # string or "?"
    time_known: str          # "Y" or "?"
    confidence: int          # 0..100
    notes: str


def normalize_name(s: str) -> str:
    s = s.strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^\w\s'-]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def score_match(input_name: str, cand_name: str) -> int:
    a = normalize_name(input_name)
    b = normalize_name(cand_name)
    if a == b:
        return 1000
    ratio = fuzz.token_set_ratio(a, b)   # 0..100
    partial = fuzz.partial_ratio(a, b)   # 0..100
    return int(ratio * 7 + partial * 3)  # ~0..1000


def http_get(session: requests.Session, url: str, params: Optional[dict] = None) -> str:
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.text


def search_candidates(session: requests.Session, name: str) -> List[Candidate]:
    html = http_get(session, SEARCH_URL, params={"nom": name})
    soup = BeautifulSoup(html, "lxml")

    candidates: List[Candidate] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)
        if not text:
            continue

        if href.startswith("/"):
            href = "https://www.astrotheme.com" + href

        if "astrotheme.com" not in href:
            continue

        if "/astrology/" in href and href.endswith(".php"):
            candidates.append(Candidate(name=text, url=href))

    seen = set()
    uniq: List[Candidate] = []
    for c in candidates:
        if c.url in seen:
            continue
        seen.add(c.url)
        uniq.append(c)
    return uniq


MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def parse_born_line(text: str) -> Tuple[str, str, str, bool, str]:
    """
    Returns: (birth_date_iso_or_empty, birth_time_hhmm_or_empty, birth_place_or_empty, time_known_bool, notes)
    Unknown fields remain "" here; caller converts "" to "?".
    """
    t = " ".join(text.split())
    notes = ""

    # Date: "2 January 1960"
    birth_date = ""
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", t)
    if m:
        dd = int(m.group(1))
        mon = MONTHS.get(m.group(2).lower())
        yyyy = m.group(3)
        if mon:
            birth_date = f"{yyyy}-{mon}-{dd:02d}"
        else:
            notes += "Unrecognized month; "
    else:
        # Date: "January 2, 1960"
        m2 = re.search(r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b", t)
        if m2:
            mon = MONTHS.get(m2.group(1).lower())
            dd = int(m2.group(2))
            yyyy = m2.group(3)
            if mon:
                birth_date = f"{yyyy}-{mon}-{dd:02d}"
            else:
                notes += "Unrecognized month; "

    # Time: "at 3:15 PM" or "at 03:15"
    time_known = False
    birth_time = ""
    tm = re.search(r"\bat\s+(\d{1,2})[:h](\d{2})\s*(AM|PM)?\b", t, flags=re.IGNORECASE)
    if tm:
        hh = int(tm.group(1))
        mm = int(tm.group(2))
        ampm = tm.group(3)
        if ampm:
            ampm = ampm.upper()
            if ampm == "PM" and hh != 12:
                hh += 12
            if ampm == "AM" and hh == 12:
                hh = 0
        birth_time = f"{hh:02d}:{mm:02d}"
        time_known = True
    else:
        if re.search(r"\btime\s+unknown\b|\bunknown\s+time\b", t, flags=re.IGNORECASE):
            time_known = False

    # Place: after ", in ..."
    birth_place = ""
    pm = re.search(r"\b,\s*in\s+(.+?)(?:\.\s*$|$)", t, flags=re.IGNORECASE)
    if pm:
        birth_place = pm.group(1).strip()

    if not birth_date:
        notes += "Date not parsed; "
    if not birth_place:
        notes += "Place not parsed; "

    return birth_date, birth_time, birth_place, time_known, notes.strip(" ;")


def extract_birth_data(session: requests.Session, url: str) -> Tuple[str, str, str, bool, str]:
    html = http_get(session, url)
    soup = BeautifulSoup(html, "lxml")

    blocks = []
    for el in soup.select("h1,h2,p,div,td"):
        txt = el.get_text(" ", strip=True)
        if txt and re.search(r"\bBorn\b", txt):
            blocks.append(txt)

    blocks.sort(key=len)

    for txt in blocks[:40]:
        bd, bt, pl, known, notes = parse_born_line(txt)
        if bd or pl or bt:
            return bd, bt, pl, known, notes

    alltxt = soup.get_text(" ", strip=True)
    idx = alltxt.lower().find("born")
    snippet = alltxt[idx: idx + 300] if idx >= 0 else ""
    if snippet:
        return parse_born_line(snippet)
    return "", "", "", False, "No 'Born' snippet found"


def load_cache(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path: Path, cache: Dict[str, Any]) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def qmark(s: str) -> str:
    return s if s else UNKNOWN


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python astrotheme_lookup.py names.txt results.csv", file=sys.stderr)
        sys.exit(2)

    names_file = Path(sys.argv[1])
    out_csv = Path(sys.argv[2])
    cache_path = Path(CACHE_FILE)

    names = [ln.strip() for ln in names_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    cache = load_cache(cache_path)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: List[Result] = []

    for i, name in enumerate(names, start=1):
        key = normalize_name(name)

        if key in cache:
            results.append(Result(**cache[key]))
            continue

        if i > 1:
            time.sleep(REQUEST_DELAY_SEC)

        try:
            cands = search_candidates(session, name)
            if not cands:
                r = Result(
                    input_name=name,
                    matched_name=UNKNOWN,
                    astrotheme_url=UNKNOWN,
                    birth_date=UNKNOWN,
                    birth_time=UNKNOWN,
                    birth_place=UNKNOWN,
                    time_known=UNKNOWN,
                    confidence=0,
                    notes="No candidates found"
                )
                results.append(r)
                cache[key] = asdict(r)
                continue

            scored = [(score_match(name, c.name), c) for c in cands]
            scored.sort(key=lambda x: x[0], reverse=True)
            best_score, best = scored[0]

            notes = ""
            if len(scored) > 1 and scored[1][0] >= best_score - 80:
                top3 = ", ".join([f"{c.name}({s})" for s, c in scored[:3]])
                notes = f"Ambiguous match; top: {top3}"

            bd, bt, pl, known, parse_notes = extract_birth_data(session, best.url)
            if parse_notes:
                notes = (notes + "; " + parse_notes).strip("; ")

            r = Result(
                input_name=name,
                matched_name=qmark(best.name),
                astrotheme_url=qmark(best.url),
                birth_date=qmark(bd),
                birth_time=qmark(bt),
                birth_place=qmark(pl),
                time_known="Y" if known else UNKNOWN,
                confidence=min(100, best_score // 10),
                notes=notes if notes else ""
            )

            results.append(r)
            cache[key] = asdict(r)

        except requests.HTTPError as e:
            r = Result(
                input_name=name,
                matched_name=UNKNOWN,
                astrotheme_url=UNKNOWN,
                birth_date=UNKNOWN,
                birth_time=UNKNOWN,
                birth_place=UNKNOWN,
                time_known=UNKNOWN,
                confidence=0,
                notes=f"HTTP error: {e}"
            )
            results.append(r)
            cache[key] = asdict(r)
        except Exception as e:
            r = Result(
                input_name=name,
                matched_name=UNKNOWN,
                astrotheme_url=UNKNOWN,
                birth_date=UNKNOWN,
                birth_time=UNKNOWN,
                birth_place=UNKNOWN,
                time_known=UNKNOWN,
                confidence=0,
                notes=f"Error: {type(e).__name__}: {e}"
            )
            results.append(r)
            cache[key] = asdict(r)

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "input_name", "matched_name", "astrotheme_url",
            "birth_date", "birth_time", "birth_place",
            "time_known", "confidence", "notes"
        ])
        for r in results:
            w.writerow([
                qmark(r.input_name),
                qmark(r.matched_name),
                qmark(r.astrotheme_url),
                qmark(r.birth_date),
                qmark(r.birth_time),
                qmark(r.birth_place),
                r.time_known if r.time_known else UNKNOWN,
                r.confidence,
                r.notes if r.notes else ""
            ])

    save_cache(cache_path, cache)
    print(f"Wrote {len(results)} rows to {out_csv} and updated {cache_path}")


if __name__ == "__main__":
    main()
