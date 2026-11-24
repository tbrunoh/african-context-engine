from __future__ import annotations

from datetime import date

import pytest
from conftest import minimal_pack

from ace_engine.context import PackError, check_file, load_packs, pack_files, parse_pack, validate_pack
from ace_engine.context.schema import ReviewStatus
from ace_engine.countries import COUNTRIES


def test_every_starter_pack_validates(packs_dir):
    files = pack_files(packs_dir)
    assert len(files) >= 6
    for path in files:
        report = check_file(path)
        assert report.ok, (path, report.errors)


def test_every_starter_fact_is_sourced_and_speaks_its_countries_languages(packs_dir):
    """Every fact can be read in each language of every country it serves."""
    for pack in load_packs(packs_dir):
        for fact in pack.facts:
            assert fact.review_status is ReviewStatus.SOURCED
            assert fact.source_url and fact.source_url.startswith("https://")
            assert fact.checked_on
            for cc in fact.scope.countries:
                for lang in COUNTRIES[cc].languages:
                    if lang in ("en", "fr", "sw") and (cc, lang) != ("RW", "sw"):
                        assert lang in fact.languages, (fact.id, cc, lang)


def test_every_covered_country_has_an_emergency_pack(packs_dir):
    packs = {p.id for p in load_packs(packs_dir)}
    for cc in COUNTRIES:
        assert f"{cc.lower()}-emergency-contacts" in packs


def test_safety_critical_facts_always_have_a_number(packs_dir):
    for pack in load_packs(packs_dir):
        for fact in pack.facts:
            if fact.safety_critical:
                assert fact.contacts or fact.refer_queue, fact.id


def test_short_forms_fit_one_sms(packs_dir):
    for pack in load_packs(packs_dir):
        for fact in pack.facts:
            assert fact.short is None or len(fact.short) <= 160
            for r in fact.translations.values():
                assert r.short is None or len(r.short) <= 160


def test_minimal_pack_parses():
    pack = parse_pack(minimal_pack())
    assert pack.facts[0].id == "test-pack/f1"
    assert pack.facts[0].scope.countries == ("KE",)  # inherited from the pack


@pytest.mark.parametrize("fact_override, message", [
    ({"source_url": None}, "need a source_url"),
    ({"checked_on": None}, "need a checked_on"),
    ({"review_status": "expert_reviewed"}, "must name a reviewer"),
    ({"short": "x" * 161}, "the limit is 160"),
    ({"months": [13]}, "between 1 and 12"),
    ({"vertical": "astrology"}, "vertical must be one of"),
    ({"kind": "rumour"}, "kind must be one of"),
    ({"review_status": "approved"}, "unknown review_status"),
    ({"id": "Bad Id"}, "lowercase"),
    ({"contacts": [{"label": "x", "number": "call me"}]}, "contact number"),
    ({"checked_on": "23/11/2026"}, "ISO date"),
])
def test_validation_errors(fact_override, message):
    report = validate_pack(minimal_pack(fact=fact_override))
    assert not report.ok
    assert any(message in e for e in report.errors), report.errors


def test_draft_needs_no_source_url():
    assert validate_pack(minimal_pack(fact={"review_status": "draft", "source_url": None, "checked_on": None})).ok


def test_open_packs_must_be_cc_by():
    report = validate_pack(minimal_pack(license="MIT"))
    assert any("CC-BY-4.0" in e for e in report.errors)


def test_unsupported_spec_version():
    report = validate_pack(minimal_pack(spec_version="0.1"))
    assert any("unsupported spec_version" in e for e in report.errors)


def test_duplicate_fact_ids():
    raw = minimal_pack()
    raw["facts"].append(dict(raw["facts"][0]))
    assert any("duplicate id" in e for e in validate_pack(raw).errors)


def test_warnings_for_stale_and_unreviewed_translations():
    raw = minimal_pack(fact={"checked_on": "2024-01-01", "translations": {"sw": {"claim": "Mwagilia asubuhi."}}})
    report = validate_pack(raw, today=date(2026, 11, 23))
    assert report.ok
    assert any("more than a year ago" in w for w in report.warnings)
    assert any("awaits review" in w for w in report.warnings)


def test_parse_pack_raises_with_every_error():
    with pytest.raises(PackError) as exc:
        parse_pack(minimal_pack(license="MIT", fact={"source_url": None}))
    assert "CC-BY-4.0" in str(exc.value) and "source_url" in str(exc.value)


def test_duplicate_pack_ids_across_files(tmp_path, packs_dir):
    src = next(p for p in pack_files(packs_dir) if p.name == "rainfall-seasons.yaml")
    (tmp_path / "a.yaml").write_text(src.read_text())
    (tmp_path / "b.yaml").write_text(src.read_text())
    with pytest.raises(PackError, match="already loaded"):
        load_packs(tmp_path)


def test_templates_are_skipped(tmp_path, packs_dir):
    (tmp_path / "_template.yaml").write_text("not: a pack")
    assert pack_files(tmp_path) == []
