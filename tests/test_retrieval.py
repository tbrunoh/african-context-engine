from __future__ import annotations

from datetime import date

import pytest
from conftest import minimal_pack

from ace_engine.context import ContextQuery, ContextStore, ReviewStatus, parse_pack
from ace_engine.models import GeoPoint
from ace_engine.text import contains_phrase, guess_language, terms, wants_action


def ids(results):
    return [r.fact.id.split("/")[1] for r in results]


@pytest.mark.parametrize("question, expected", [
    ("armyworm is eating my maize leaves", "damage-signs"),
    ("viwavijeshi kwenye mahindi", "damage-signs"),
    ("how do I scout for armyworm", "scouting-w-pattern"),
    ("what is push pull", "push-pull"),
    ("what moisture should maize be before storage", "drying-moisture"),
    ("hermetic bags weevils", "hermetic-storage"),
    ("aflasafe", "aflasafe"),
    ("pregnancy danger signs", "go-now"),
    ("dalili za hatari mjamzito", "go-now"),
    ("safaricom called me from another number", "official-number"),
    ("pesa zimetumwa kimakosa", "sent-by-mistake"),
    ("when are the long rains", "two-seasons"),
    ("gender violence helpline", "gbv-helpline"),
])
def test_questions_find_the_right_fact(engine, question, expected):
    results = engine.store.query(ContextQuery(text=question, country="KE", limit=3))
    assert expected in ids(results), (question, ids(results))


def test_off_topic_question_returns_nothing(engine):
    assert engine.store.query(ContextQuery(text="price of tomatoes in Nairobi", country="KE")) == []


def test_action_questions_prefer_action_facts(engine):
    plain = engine.store.query(ContextQuery(text="armyworm maize", country="KE", limit=3))
    action = engine.store.query(ContextQuery(text="armyworm maize", country="KE", limit=3, prefer_kind="action"))
    assert sum(r.fact.kind == "action" for r in action) > sum(r.fact.kind == "action" for r in plain)


def _store(*facts):
    pack = minimal_pack()
    pack["facts"] = [{**pack["facts"][0], **f} for f in facts]
    store = ContextStore()
    store.extend(parse_pack(pack).facts)
    return store


def test_drafts_are_withheld_by_default():
    store = _store({"id": "a", "review_status": "draft", "claim": "maize tip"})
    assert store.query(ContextQuery(text="maize")) == []
    assert store.query(ContextQuery(text="maize", min_review=ReviewStatus.DRAFT))


def test_expired_facts_are_withheld():
    store = _store({"id": "a", "claim": "maize tip", "expires": "2026-01-01"})
    assert store.query(ContextQuery(text="maize", today=date(2026, 6, 1))) == []
    assert store.query(ContextQuery(text="maize", today=date(2025, 6, 1)))


def test_verified_tier_needs_entitlement():
    pack = minimal_pack(tier="verified", license="LicenseRef-ACE-Verified")
    store = ContextStore()
    store.extend(parse_pack(pack).facts)
    assert store.query(ContextQuery(text="maize water")) == []
    assert store.query(ContextQuery(text="maize water", include_verified=True))


def test_altitude_and_county_scoping():
    store = _store(
        {"id": "highland", "claim": "maize highland advice", "scope": {"altitude_min_m": 1800}},
        {"id": "lowland", "claim": "maize lowland advice", "scope": {"altitude_max_m": 1000}},
        {"id": "nyeri", "claim": "maize nyeri advice", "scope": {"admin_areas": ["Nyeri"]}},
    )
    high = store.query(ContextQuery(text="maize advice", location=GeoPoint(-0.4, 36.9, 2000)))
    assert "highland" in ids(high) and "lowland" not in ids(high)
    other_county = store.query(ContextQuery(text="maize advice", admin_area="Kisumu"))
    assert "nyeri" not in ids(other_county)


def test_season_filter():
    store = _store({"id": "rainy", "claim": "maize rainy season advice", "months": [3, 4, 5]})
    assert store.query(ContextQuery(text="maize", month=4))
    assert store.query(ContextQuery(text="maize", month=8)) == []


def test_country_filter(engine):
    assert engine.store.query(ContextQuery(text="armyworm", country="NG")) == []


def test_text_helpers():
    assert terms("The farmers are scouting fields") == ["farmer", "scout", "field"]
    assert guess_language("Mahindi yangu yana viwavi, nifanye nini?") == "sw"
    assert guess_language("What should I do about my maize?") == "en"
    assert contains_phrase("My husband BEATS me!", "husband beats")
    assert not contains_phrase("drinking water", "drink")
    assert wants_action("nifanye nini na viwavi")
    assert not wants_action("what is armyworm")
