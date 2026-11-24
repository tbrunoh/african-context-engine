from pathlib import Path

import pytest

from ace_engine.context import (
    ContextFact,
    ContextQuery,
    ContextStore,
    GeoScope,
    PackError,
    ReviewStatus,
    Tier,
    load_pack,
    parse_pack,
)
from ace_engine.models import GeoPoint

PACK = Path(__file__).resolve().parents[1] / "context_packs" / "examples" / "kenya-maize-demo.yaml"


@pytest.fixture()
def store() -> ContextStore:
    s = ContextStore()
    s.extend(list(load_pack(PACK).facts))
    return s


def test_altitude_scoping_picks_highland_fact(store):
    highland = GeoPoint(-0.42, 36.95, altitude_m=1950)
    ids = [r.fact.id for r in store.query(ContextQuery(topic="pest", subject="maize", location=highland,
                                                       country="KE"))]
    assert "ke-maize-demo/faw-highland-placeholder" in ids
    assert "ke-maize-demo/faw-coastal-placeholder" not in ids
    assert ids[0] == "ke-maize-demo/faw-highland-placeholder"  # more specific ranks first


def test_coastal_location_gets_coastal_fact(store):
    coast = GeoPoint(-4.04, 39.67, altitude_m=50)
    ids = [r.fact.id for r in store.query(ContextQuery(topic="pest", location=coast, country="KE"))]
    assert "ke-maize-demo/faw-coastal-placeholder" in ids
    assert "ke-maize-demo/faw-highland-placeholder" not in ids


def test_month_filter(store):
    in_season = store.query(ContextQuery(topic="planting", month=4))
    off_season = store.query(ContextQuery(topic="planting", month=9))
    assert len(in_season) == 1 and off_season == []


def test_other_country_excluded(store):
    assert store.query(ContextQuery(topic="pest", country="NG")) == []


def test_verified_tier_needs_entitlement():
    s = ContextStore()
    s.add(ContextFact(id="v1", claim="x", topic="pest", vertical="agriculture", source="s",
                      review_status=ReviewStatus.EXPERT_REVIEWED, reviewed_by="r", tier=Tier.VERIFIED))
    assert s.query(ContextQuery(topic="pest")) == []
    assert len(s.query(ContextQuery(topic="pest", include_verified=True))) == 1


def test_radius_scope():
    scope = GeoScope(center=GeoPoint(-1.29, 36.82), radius_km=10)
    assert scope.contains(GeoPoint(-1.30, 36.83))
    assert not scope.contains(GeoPoint(-4.04, 39.67))


def test_pack_validation_rejects_reviewed_fact_without_reviewer():
    raw = {"spec_version": "0.1", "id": "p", "title": "t", "license": "CC-BY-4.0", "maintainers": ["m"],
           "facts": [{"id": "a", "claim": "c", "topic": "t", "vertical": "v", "source": "s",
                      "review_status": "expert_reviewed"}]}
    with pytest.raises(PackError):
        parse_pack(raw)


def test_open_pack_requires_cc_by():
    raw = {"spec_version": "0.1", "id": "p", "title": "t", "license": "proprietary", "maintainers": ["m"],
           "facts": []}
    with pytest.raises(PackError):
        parse_pack(raw)
