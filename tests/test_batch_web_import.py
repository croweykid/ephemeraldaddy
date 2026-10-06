import io
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
