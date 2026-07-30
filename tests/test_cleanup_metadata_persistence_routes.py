from types import SimpleNamespace

from ephemeraldaddy.gui.cleanup_metadata import (
    ACTION_ALIAS_TO_FROM,
    ACTION_CLEAN_BIRTHPLACE,
    ACTION_GET_BIO,
    import_biography_from_lookup,
    run_metadata_migration,
)


def _callbacks(chart):
    nonastral_writes = []
    astro_writes = []
    return (
        lambda uid: chart,
        lambda uid, patch: nonastral_writes.append((uid, patch)),
        lambda uid, value: astro_writes.append((uid, value)),
        nonastral_writes,
        astro_writes,
    )


def test_alias_cleanup_uses_uid_nonastral_patch_only():
    chart = SimpleNamespace(alias="Former Name", from_whence="")
    load, nonastral, astro, nonastral_writes, astro_writes = _callbacks(chart)

    outcome, changed_uids = run_metadata_migration(
        chart_uids=["CHART-UID"],
        action=ACTION_ALIAS_TO_FROM,
        load_chart_by_uid=load,
        update_nonastral_by_uid=nonastral,
        update_astro_by_uid=astro,
    )

    assert outcome.updated_chart_count == 1
    assert changed_uids == {"CHART-UID"}
    assert nonastral_writes == [
        ("CHART-UID", {"alias": "", "from_whence": "Former Name"})
    ]
    assert astro_writes == []


def test_birthplace_cleanup_uses_uid_astro_route_only():
    chart = SimpleNamespace(birth_place="Paris, France, Europe")
    load, nonastral, astro, nonastral_writes, astro_writes = _callbacks(chart)

    outcome, changed_uids = run_metadata_migration(
        chart_uids=["CHART-UID"],
        action=ACTION_CLEAN_BIRTHPLACE,
        load_chart_by_uid=load,
        update_nonastral_by_uid=nonastral,
        update_astro_by_uid=astro,
        lookup_location_label=lambda query: "Paris, FR",
    )

    assert outcome.updated_chart_count == 1
    assert changed_uids == {"CHART-UID"}
    assert nonastral_writes == []
    assert astro_writes == [("CHART-UID", chart)]
    assert chart.birth_place == "Paris, FR"


def test_biography_lookup_happens_before_unchanged_comparison():
    chart = SimpleNamespace(name="Someone", biography="Existing")

    assert not import_biography_from_lookup(
        chart, lookup_biography_by_name=lambda _name: "Existing"
    )


def test_biography_import_uses_nonastral_patch():
    chart = SimpleNamespace(name="Someone", biography="")
    load, nonastral, astro, nonastral_writes, astro_writes = _callbacks(chart)

    run_metadata_migration(
        chart_uids=["CHART-UID"],
        action=ACTION_GET_BIO,
        load_chart_by_uid=load,
        update_nonastral_by_uid=nonastral,
        update_astro_by_uid=astro,
        lookup_biography_by_name=lambda _name: "Imported biography",
    )

    assert nonastral_writes == [
        ("CHART-UID", {"biography": "Imported biography"})
    ]
    assert astro_writes == []
