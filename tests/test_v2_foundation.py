"""V2 foundations: snapshots, the licence register, geometry, places and connector parsers. No network."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ace_engine.connectors.cap import feed_items, parse_alert
from ace_engine.connectors.hdx_prices import aggregate
from ace_engine.connectors.health_facilities import facility_records, read_xlsx
from ace_engine.connectors.open_meteo import summarise
from ace_engine.countries import COUNTRIES
from ace_engine.geo import centroid, haversine_km, in_polygons, in_ring, simplify
from ace_engine.places import Gazetteer
from ace_engine.snapshots import Snapshot, SnapshotStore, checksum, load_register

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "snapshots"


@pytest.fixture(scope="module")
def store() -> SnapshotStore:
    return SnapshotStore(SNAPSHOTS)


# ---------------------------------------------------------------- snapshots and the licence register

def test_every_snapshot_verifies_and_is_registered(store):
    register = load_register(SNAPSHOTS / "register.yaml")
    found = store.available()
    assert found, "the repository ships snapshots"
    for dataset, country in found:
        snap = store.get(dataset, country)
        assert snap.verify(), f"{dataset}/{country} checksum does not match its records"
        assert snap.source_id in register, f"{dataset}/{country} uses an unregistered source {snap.source_id}"
        assert snap.source and snap.source_url.startswith("http") and snap.licence and snap.retrieved_at


def test_odbl_snapshots_live_in_their_own_store():
    for path in SNAPSHOTS.glob("*/*.json"):
        snap = Snapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))
        assert not snap.odbl, f"{path} is ODbL and must live under snapshots/odbl/"
    for path in SNAPSHOTS.glob("odbl/*/*.json"):
        assert Snapshot.from_dict(json.loads(path.read_text(encoding="utf-8"))).odbl


def test_places_and_facilities_cover_all_13_countries(store):
    for code in COUNTRIES:
        assert store.get("places", code), f"no places for {code}"
        assert store.get("facilities", code), f"no facilities for {code}"
        assert store.get("weather", code), f"no weather for {code}"


def test_snapshot_round_trip_and_validity(tmp_path):
    now = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    snap = Snapshot("weather", "KE", "open_meteo", "Test", "https://example.org", "CC BY 4.0",
                    "2026-11-24T12:00:00Z", [{"a": 1}], valid_until="2026-11-25T00:00:00Z")
    path = snap.write(tmp_path)
    back = SnapshotStore(tmp_path).get("weather", "KE")
    assert path.exists() and back.verify() and back.sha256 == checksum([{"a": 1}])
    assert back.is_valid(now) and not back.is_valid(now + timedelta(days=1))
    back.records.append({"b": 2})
    assert not back.verify()


def test_odbl_snapshot_is_written_to_its_own_folder(tmp_path):
    snap = Snapshot("places", "TZ", "geoboundaries", "Test", "https://example.org",
                    "Open Data Commons Open Database License 1.0", "2026-11-24T12:00:00Z", [])
    assert snap.write(tmp_path) == tmp_path / "odbl" / "places" / "TZ.json"
    assert SnapshotStore(tmp_path).get("places", "TZ") is not None


# ---------------------------------------------------------------- geometry

SQUARE = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]


def test_point_in_polygon_and_holes():
    assert in_ring((0.5, 0.5), SQUARE) and not in_ring((1.5, 0.5), SQUARE)
    hole = [[0.4, 0.4], [0.4, 0.6], [0.6, 0.6], [0.6, 0.4], [0.4, 0.4]]
    assert not in_polygons((0.5, 0.5), [SQUARE, hole]) and in_polygons((0.2, 0.2), [SQUARE, hole])


def test_simplify_keeps_the_shape_of_a_closed_ring():
    ring = [[0, x / 100] for x in range(101)] + [[y / 100, 1] for y in range(101)] + \
           [[1, 1 - x / 100] for x in range(101)] + [[1 - y / 100, 0] for y in range(101)]
    simple = simplify(ring, 0.01)
    assert 4 <= len(simple) <= 8
    assert in_ring((0.5, 0.5), simple)


def test_centroid_and_distance():
    assert centroid([SQUARE]) == (0.5, 0.5)
    assert 110 < haversine_km((0, 0), (1, 0)) < 112


# ---------------------------------------------------------------- places

@pytest.mark.parametrize("country,text,expected", [
    ("KE", "will it rain in Embu", "Embu"), ("NG", "rain in kano", "Kano"), ("TZ", "mvua Mwanza", "Mwanza"),
    ("SN", "pluie a Thies", "Thies"), ("GH", "Accra", "Greater Accra Region"),
    ("NG", "Abuja", "Abuja Federal Capital Territory"), ("RW", "Kigali", "City of Kigali"),
    ("CI", "Abidjan", "District Autonome D'Abidjan"), ("UG", "Gulu", "Gulu"), ("ZA", "Cape Town", "Western Cape"),
])
def test_find_place_by_name(store, country, text, expected):
    assert Gazetteer(store).find(text, country).name == expected


@pytest.mark.parametrize("lat,lon,country,name", [
    (-1.2864, 36.8172, "KE", "Nairobi"), (12.0, 8.52, "NG", "Kano"), (0.3476, 32.5825, "UG", "Kampala"),
    (14.7167, -17.4677, "SN", "Dakar"), (-22.56, 17.08, "NA", "Khomas"), (-17.83, 31.05, "ZW", "Harare"),
    (6.45, 3.39, "NG", "Lagos"), (-29.86, 31.03, "ZA", "KwaZulu-Natal"), (6.1319, 1.2228, "TG", "Maritime Region"),
])
def test_locate_place_by_position(store, lat, lon, country, name):
    place = Gazetteer(store).locate(lat, lon, country)
    assert place.country == country and place.name == name


def test_place_names_stay_inside_the_callers_country(store):
    assert Gazetteer(store).find("Kano", "KE") is None


# ---------------------------------------------------------------- connector parsers (offline)

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Old</title><link>https://example.org/old.xml</link><pubDate>Mon, 16 Nov 2026 12:57:09 +0000</pubDate></item>
<item><title>New</title><link>https://example.org/new.xml</link><pubDate>Tue, 24 Nov 2026 08:00:00 +0000</pubDate></item>
</channel></rss>"""
ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>t</title>
<entry><title>A</title><link rel="alternate" href="https://example.org/a.xml"/><updated>2026-11-20T10:00:00+03:00</updated></entry>
</feed>"""


def cap_alert(msg_type="Alert", expires="2026-11-27T00:00:00+02:00", references="", area="Countrywide",
              polygon="") -> bytes:
    poly = f"<polygon>{polygon}</polygon>" if polygon else ""
    return f"""<?xml version="1.0"?><alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
<identifier>id-{msg_type}</identifier><sender>met@example.org</sender><sent>2026-11-21T00:00:00+02:00</sent>
<status>Actual</status><msgType>{msg_type}</msgType><scope>Public</scope><references>{references}</references>
<info><language>en</language><event>Thunderstorms</event><urgency>Expected</urgency><severity>Moderate</severity>
<certainty>Likely</certainty><expires>{expires}</expires><senderName>Met Service</senderName>
<headline>Thunderstorms expected</headline><instruction>Avoid shelter under trees.</instruction>
<area><areaDesc>{area}</areaDesc>{poly}</area></info></alert>""".encode()


def test_feed_items_read_rss_and_atom_newest_first():
    assert [u for u, _ in feed_items(RSS)] == ["https://example.org/new.xml", "https://example.org/old.xml"]
    assert feed_items(ATOM)[0][0] == "https://example.org/a.xml"


def test_parse_alert_keeps_the_authoritys_words():
    rec = parse_alert(cap_alert(polygon="0,0 0,1 1,1 1,0 0,0"), "https://example.org/a.xml")
    assert rec["headline"] == "Thunderstorms expected" and rec["instruction"] == "Avoid shelter under trees."
    assert rec["area_desc"] == ["Countrywide"] and rec["polygons"]


def test_parse_alert_drops_tests_and_marks_cancels():
    assert parse_alert(cap_alert().replace(b"<status>Actual", b"<status>Exercise"), "u") is None
    assert parse_alert(cap_alert(msg_type="Cancel", references="met@example.org,id-Alert,2026"), "u")["cancel"]


def test_wfp_aggregate_prefers_retail_and_keeps_recent_months():
    rows = []
    for month in ("2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"):
        for ptype, price in (("Retail", 50), ("Wholesale", 4000)):
            rows.append({"date": f"{month}-15", "admin1": "A", "admin2": "B", "market": "Town", "market_id": "1",
                         "latitude": "0.1", "longitude": "37.1", "category": "cereals and tubers",
                         "commodity": "Maize", "unit": "KG", "priceflag": "actual", "pricetype": ptype,
                         "currency": "KES", "price": str(price)})
    rows.append({**rows[0], "category": "non-food", "commodity": "Soap"})
    markets, latest = aggregate(rows)
    assert latest == "2026-12" and len(markets) == 1
    item = markets[0]["items"][0]
    assert item["pricetype"] == "Retail" and len(item["series"]) == 6 and item["series"][-1] == ["2026-12", 50.0]
    assert all(i["commodity"] != "Soap" for i in markets[0]["items"])


def test_open_meteo_summary_states_chances():
    daily = {"time": ["2026-11-25"], "precipitation_sum": [0.0],
             **{f"precipitation_sum_member{i:02d}": [25.0 if i <= 30 else 0.0] for i in range(1, 51)}}
    day = summarise(daily)[0]
    assert day[0] == "2026-11-25" and day[1] == round(30 / 51, 2) and day[3] == round(30 / 51, 2)


def test_xlsx_reader_and_facility_records():
    sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             '<row r="1">' + "".join(f'<c r="{c}1" t="inlineStr"><is><t>{h}</t></is></c>' for c, h in zip(
                 "ABCDEFGH", ("Country", "Admin1", "Facility_n", "Facility_t", "Ownership", "Lat", "Long",
                              "LL_source"), strict=False))
             + '</row><row r="2">' + "".join(f'<c r="{c}2" t="inlineStr"><is><t>{v}</t></is></c>' for c, v in zip(
                 "ABCDE", ("Kenya", "Embu", "Embu Hospital", "Hospital", "MoH"), strict=False)) +
             '<c r="F2"><v>-0.53</v></c><c r="G2"><v>37.45</v></c></row></sheetData></worksheet>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    rows = read_xlsx(buf.getvalue())
    assert facility_records(rows, "Kenya") == [["Embu Hospital", "Hospital", "MoH", "Embu", -0.53, 37.45]]
    assert facility_records(rows, "Ghana") == []
