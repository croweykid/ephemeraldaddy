import io
import pytest
from datetime import date
from ephemeraldaddy.io.web_profile.csv_io import load_seeds, parse_pasted_names, export_failures
from ephemeraldaddy.io.web_profile.models import BatchImportRow, ValidatedPlace
from ephemeraldaddy.io.web_profile.lookup_service import WebProfileLookupService


def test_pasted_names_preserve_order_and_duplicates():
    assert [s.name for s in parse_pasted_names('A\n\nB\nA')] == ['A','B','A']


def test_csv_metadata_case_insensitive_and_failure_round_trip():
    seeds=load_seeds(io.StringIO('NAME,Alias,FROM,TAGS,Notes\nA,Al,web,"x, x, y",note\n'))
    assert (seeds[0].alias,seeds[0].from_whence,seeds[0].tags,seeds[0].notes)==('Al','web',('x','y'),'note')
    row=BatchImportRow('A','A',birth_date='bad',notes='edited')
    out=io.StringIO(); export_failures([row],out)
    assert 'edited' in out.getvalue() and 'Birth date is invalid' in out.getvalue()


def test_place_edit_invalidates_coordinates_and_selection():
    row=BatchImportRow('A','A','2000-01-01','', 'Here',place=ValidatedPlace('Here',1,2),included=True)
    row.set_birth_place('Elsewhere')
    assert row.place is None and not row.included


def test_astrotheme_birth_data_wins_and_wikipedia_enriches():
    service=WebProfileLookupService(astro_search=lambda n:'astro',astro_parse=lambda u:{'name':'Resolved','birth_year':2000,'birth_month':1,'birth_day':2,'time_unknown':False,'birth_hour':3,'birth_minute':4,'birth_place':'Here','profile_url':u},wiki_resolve=lambda n:{'status':'single','title':'Wiki'},wiki_birth=lambda t:{'birth_year':1999,'birth_month':9,'birth_day':9,'birth_place':'Wrong'},wiki_blurb=lambda t:{'text':'Bio'},wiki_match=lambda o,d:None)
    row=service.lookup(parse_pasted_names('A')[0])
    assert (row.birth_date,row.birth_time,row.birth_place,row.biography)==('2000-01-02','03:04','Here','Bio')


def test_wikipedia_ambiguity_blocks_without_unique_date_match():
    service=WebProfileLookupService(astro_search=lambda n:(_ for _ in ()).throw(ValueError('no')),astro_parse=None,wiki_resolve=lambda n:{'status':'multiple','options':['A','B']},wiki_birth=lambda t:{},wiki_blurb=lambda t:{},wiki_match=lambda o,d:None)
    row=service.lookup(parse_pasted_names('A')[0])
    assert 'Multiple Wikipedia entries' in row.error_text and not row.importable


def test_wikipedia_candidates_are_dated_before_matching():
    from ephemeraldaddy.gui.wikipedia_blurb_getter import unique_title_matching_birth_date
    service = WebProfileLookupService(
        astro_search=lambda name: 'astro',
        astro_parse=lambda url: dict(birth_year=2000, birth_month=1, birth_day=2, time_unknown=True),
        wiki_resolve=lambda name: dict(status='multiple', options=['Wrong', 'Right']),
        wiki_birth=lambda title: dict(birth_year=2000, birth_month=1, birth_day=2 if title == 'Right' else 3),
        wiki_match=unique_title_matching_birth_date,
        wiki_blurb=lambda title: dict(text='Matched biography'),
    )
    row = service.lookup(parse_pasted_names('A')[0])
    assert row.biography == 'Matched biography'
    assert row.sources[-1].endswith('/Right')
    assert not row.blocking_errors


def test_place_error_is_cleared_without_removing_other_errors():
    row = BatchImportRow('A', 'A', '2000-01-01', birth_place='Wrong')
    row.blocking_errors = ['Birth place could not be resolved: unavailable', 'Other issue']
    row.set_birth_place('Correct')
    row.place = ValidatedPlace('Correct', 1, 2)
    assert row.validation_errors() == ['Other issue']


def test_failures_csv_round_trip_retains_resolved_fields_and_requires_new_place_validation():
    row = BatchImportRow('Requested', 'Repaired', '2000-01-02', '03:04', 'Edited place',
                         biography='Edited biography', sources=['https://one.example', 'https://two.example'],
                         alias='Alias', from_whence='Web', tags=['x', 'y'], notes='Edited notes', data_rating='AA')
    row.blocking_errors = ['Birth place could not be resolved: temporary outage']
    stream = io.StringIO()
    export_failures([row], stream)
    stream.seek(0)
    seed, = load_seeds(stream)
    restored = seed.to_row()
    assert seed.restored
    for field in ('name', 'birth_date', 'birth_time', 'birth_place', 'biography', 'sources',
                  'alias', 'from_whence', 'tags', 'notes', 'data_rating'):
        assert getattr(restored, field) == getattr(row, field)
    assert restored.blocking_errors == []
    assert restored.place is None and not restored.included
    assert restored.validation_errors() == ['Birth place has not been validated.']


def test_name_only_csv_still_uses_profile_lookup():
    seed, = load_seeds(io.StringIO('name,notes\nA,note\n'))
    assert not seed.restored


def test_mixed_csv_restoration_depends_on_each_rows_repair_data():
    seeds = load_seeds(io.StringIO(
        'name,birth_date,birth_time,birth_place,bio,sources,error,notes\n'
        'Template,,,,,,,Keep metadata\n'
        'Unknown clock,,unknown,,,,,\n'
        'Repaired,2000-01-02,,Here,,,,\n'
        'Biography only,,,,Manual biography,,,\n'
        'Failed lookup,,,,,,No profile could be resolved.,\n'
    ))
    assert [seed.restored for seed in seeds] == [False, False, True, False, False]
    assert seeds[0].notes == 'Keep metadata'


def test_lookup_failure_csv_does_not_suppress_retry():
    row = BatchImportRow('Misspelled', 'Misspelled', lookup_errors=['No profile could be resolved.'])
    stream = io.StringIO()
    export_failures([row], stream)
    stream.seek(0)
    seed, = load_seeds(stream)
    assert not seed.restored


@pytest.mark.parametrize("field,value", [
    ("bio", "Manual biography"),
    ("sources", "https://example.org"),
    ("data_rating", "AA"),
    ("birth_date", "2000-01-02"),
    ("birth_place", "Here"),
    ("birth_time", "03:04"),
])
def test_partial_csv_data_keeps_lookup_enabled(field, value):
    seed, = load_seeds(io.StringIO(f"name,{field}\nA,{value}\n"))
    assert not seed.restored
    attribute = "biography" if field == "bio" else field
    expected = (value,) if field == "sources" else value
    assert getattr(seed, attribute) == expected


@pytest.mark.parametrize("day,place,restored", [
    ("", "", False),
    ("2000-01-02", "", False),
    ("bad", "Here", False),
    ("2000-02-30", "Here", False),
    ("2000-01-02", "   ", False),
    ("2000-01-02", "Here", True),
])
def test_csv_restoration_requires_valid_date_and_place(day, place, restored):
    seed, = load_seeds(io.StringIO(
        f"name,birth_date,birth_place,birth_time\nA,{day},{place},unknown\n"
    ))
    assert seed.restored is restored


@pytest.mark.parametrize("astro_place", ["", "   "])
def test_wikipedia_backfills_missing_place_without_replacing_astrotheme_data(astro_place):
    calls = []
    def wiki_birth(title):
        calls.append(title)
        # A malformed Wikipedia date must not interfere with place enrichment.
        return dict(birth_year="bad", birth_month=9, birth_day=9, birth_place="Wiki place")
    service = WebProfileLookupService(
        astro_search=lambda name: "astro",
        astro_parse=lambda url: dict(
            name="Resolved", birth_year=2000, birth_month=1, birth_day=2,
            time_unknown=False, birth_hour=3, birth_minute=4,
            birth_place=astro_place, data_rating="AA",
        ),
        wiki_resolve=lambda name: dict(status="single", title="Wiki"),
        wiki_birth=wiki_birth,
        wiki_blurb=lambda title: dict(text="Bio"),
        wiki_match=lambda options, day: None,
    )
    row = service.lookup(parse_pasted_names("A")[0])
    assert calls == ["Wiki"]
    assert (row.name, row.birth_date, row.birth_time, row.birth_place, row.data_rating) == (
        "Resolved", "2000-01-02", "03:04", "Wiki place", "AA"
    )
    assert row.biography == "Bio"
    row.place = ValidatedPlace("Wiki place", 1, 2)
    assert row.importable


def test_wikipedia_supplies_birth_data_when_astrotheme_is_unavailable():
    def unavailable(name):
        raise ValueError("No Astrotheme profile")
    service = WebProfileLookupService(
        astro_search=unavailable, astro_parse=lambda url: {},
        wiki_resolve=lambda name: dict(status="single", title="Wiki"),
        wiki_birth=lambda title: dict(
            birth_year=2000, birth_month=1, birth_day=2, birth_place="Wiki place"
        ),
        wiki_blurb=lambda title: dict(text="Bio"),
        wiki_match=lambda options, day: None,
    )
    row = service.lookup(parse_pasted_names("A")[0])
    assert (row.name, row.birth_date, row.birth_time, row.birth_place) == (
        "Wiki", "2000-01-02", "", "Wiki place"
    )


def test_manual_repair_clears_lookup_diagnostics_only_when_fields_are_valid():
    row = BatchImportRow('A', 'A', lookup_errors=['No profile could be resolved.'])
    row.set_birth_fields('Repaired', 'bad', 'unknown', 'Here')
    row.place = ValidatedPlace('Here', 1, 2)
    assert not row.importable and row.lookup_errors
    row.set_birth_fields('Repaired', '2000-01-01', 'unknown', 'Here')
    assert row.importable and not row.lookup_errors
    assert 'Original lookup: No profile' in row.error_text


def test_ambiguity_requires_actual_manual_edit_even_with_valid_provider_fields():
    row = BatchImportRow('A', 'A', '2000-01-01', '', 'Here',
                         place=ValidatedPlace('Here', 1, 2), lookup_errors=['Ambiguous profile'])
    row.set_birth_fields('A', '2000-01-01', 'unknown', 'Here')
    assert not row.importable and not row.manually_repaired
    row.set_birth_fields('Correct person', '2000-01-01', 'unknown', 'Here')
    assert row.importable
    row.blocking_errors.append('Other issue')
    assert not row.importable
