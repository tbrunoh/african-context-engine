"""V2 decision services, the hub, the engine, USSD, the API and MCP. Synthetic snapshots, fixed clock, no network."""
from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ace_engine.channels.ussd import UssdApp
from ace_engine.engine import Engine
from ace_engine.mcp_server import build_tools
from ace_engine.models import Channel, GeoPoint, Message, ReplyKind
from ace_engine.server import AceApp
from ace_engine.services import SERVICES, ServiceHub, detect
from ace_engine.services.base import Answer, Query, Refusal, fit
from ace_engine.services.pregnancy import weeks_from
from ace_engine.snapshots import Snapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
KE = "+254711000101"


def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def weather(country="KE", code="KE-14", name="Embu", fresh=True) -> Snapshot:
    days = [["2026-11-25", 0.9, 6.0, 0.4], ["2026-11-26", 0.8, 4.0, 0.0], ["2026-11-27", 0.4, 1.0, 0.0],
            ["2026-11-28", 0.1, 0.0, 0.0], ["2026-11-29", 0.1, 0.0, 0.0], ["2026-11-30", 0.7, 3.0, 0.0],
            ["2026-12-01", 0.7, 3.0, 0.0]]
    until = NOW + timedelta(hours=24) if fresh else NOW - timedelta(hours=1)
    return Snapshot("weather", country, "open_meteo", "ECMWF IFS ensemble forecast (open data), via Open-Meteo",
                    "https://open-meteo.com/", "CC BY 4.0", iso(NOW - timedelta(hours=2)),
                    [{"code": code, "name": name, "lat": -0.5, "lon": 37.5, "days": days}],
                    data_date="2026-11-25", valid_until=iso(until), meta={"model": "ecmwf_ifs025"})


def warnings(country="KE", alerts=None, fresh=True, primary=True) -> Snapshot:
    return Snapshot("warnings", country, "cap", "Kenya Meteorological Department, official CAP warnings",
                    "https://meteo.go.ke/api/cap/rss.xml", "official", iso(NOW - timedelta(hours=1)),
                    alerts or [], valid_until=iso(NOW + timedelta(hours=5 if fresh else -1)),
                    meta={"primary": primary, "newest_item": iso(NOW - timedelta(days=2))})


def alert(**kw) -> dict:
    base = {"id": "a1", "event": "Heavy rain", "headline": "Heavy rainfall alert", "severity": "Severe",
            "urgency": "Expected", "certainty": "Likely", "onset": "2026-11-24T00:00:00+03:00",
            "expires": "2026-11-26T15:00:00+03:00", "area_desc": ["Central Highlands"], "polygons": [],
            "instruction": "Avoid crossing flooded rivers.", "description": "", "language": "en", "url": "u"}
    base.update(kw)
    return base


def prices(country="KE", month="2026-10") -> Snapshot:
    items = [{"commodity": "Maize (white)", "unit": "KG", "pricetype": "Retail", "currency": "KES",
              "series": [["2026-09", 50.0], [month, 55.0]]},
             {"commodity": "Maize flour", "unit": "KG", "pricetype": "Retail", "currency": "KES",
              "series": [[month, 80.0]]},
             {"commodity": "Beans", "unit": "KG", "pricetype": "Retail", "currency": "KES",
              "series": [[month, 150.0]]}]
    return Snapshot("prices", country, "wfp_prices", "WFP Price Database, Kenya food prices, via HDX",
                    "https://data.humdata.org/dataset/wfp-food-prices-for-kenya", "CC BY-IGO",
                    iso(NOW), [{"market": "Embu", "admin1": "Eastern", "lat": -0.53, "lon": 37.45, "id": "1",
                                "items": items}], data_date=month)


def facilities(country="KE") -> Snapshot:
    recs = [["Embu Level 5 Hospital", "Hospital", "MoH", "Embu", -0.534, 37.45],
            ["Kamweli Dispensary", "Dispensary", "MoH", "Embu", -0.531, 37.452],
            ["Far Clinic", "Health Centre", "MoH", "Embu", -0.9, 37.9]]
    return Snapshot("facilities", country, "public_health_facilities", "Maina et al. 2019, via HDX",
                    "https://data.humdata.org/dataset/health-facilities-in-sub-saharan-africa", "CC BY 4.0",
                    iso(NOW), recs, data_date="2019-07-25")


@pytest.fixture()
def snaps() -> SnapshotStore:
    """The repository's places (static boundaries) with synthetic, fixed time data on top."""
    store = SnapshotStore(ROOT / "snapshots")
    embu = next(r for r in store.get("places", "KE").records if r["name"] == "Embu")
    store.put(weather(code=embu["code"]))
    store.put(warnings())
    store.put(prices())
    store.put(facilities())
    return store


@pytest.fixture()
def engine(snaps) -> Engine:
    eng = Engine.from_packs(ROOT / "context_packs", snapshots=snaps)
    eng.services.clock = lambda: NOW
    return eng


def run(engine, sid, text="", country="KE", lang="en", max_chars=1500, location=None, params=None):
    return engine.services.run(sid, text, country, lang, max_chars, location=location, params=params)


def at(engine, sid, place="Embu", country="KE", lang="en", max_chars=1500):
    hub = engine.services
    q = Query(text=place, country=country, language=lang, place=hub.places.find(place, country),
              max_chars=max_chars, now=NOW)
    return SERVICES[sid].answer(q, hub.ctx)


# ---------------------------------------------------------------- routing

@pytest.mark.parametrize("text,sid", [
    ("Will it rain in Embu this week?", "rain_this_week"), ("mvua wiki hii", "rain_this_week"),
    ("Va-t-il pleuvoir ?", "rain_this_week"), ("any weather warning for Mombasa", "official_warnings"),
    ("nearest hospital", "nearest_facility"), ("zahanati iko wapi", "nearest_facility"),
    ("price of maize in Kano", "market_prices"), ("bei ya mahindi", "market_prices"), ("prix du riz", "market_prices"),
    ("I am 22 weeks pregnant", "pregnancy_companion"), ("when is my next antenatal visit", "pregnancy_companion"),
    ("my cassava leaves are yellow", "pest_check"), ("How do I store maize?", None), ("Hello", None),
])
def test_detect(text, sid):
    assert detect(text) == sid


def test_weeks_parsing():
    assert weeks_from("I am 22 weeks pregnant") == 22 and weeks_from("wiki 30") == 30
    assert weeks_from("enceinte de 18 semaines") == 18 and weeks_from("6 months pregnant") == 26
    assert weeks_from("no number here") is None


def test_fit_keeps_the_first_piece_and_adds_what_fits():
    assert fit(["a b c", "dd", "e" * 50], 9) == "a b c dd"


# ---------------------------------------------------------------- rain

def test_rain_speaks_in_chances_with_the_date(engine):
    r = at(engine, "rain_this_week")
    assert isinstance(r, Answer) and r.preview
    assert r.text["en"].startswith("Rain near Embu: likely Wed to Thu; possible Fri; mostly dry Sat to Sun")
    assert "Heavy rain (20 mm or more) possible Wed" in r.text["en"] and "ECMWF forecast of 24 Nov" in r.text["en"]
    assert "Jumatano" in r.text["sw"] and "probable" in r.text["fr"]
    assert r.citations[0].licence == "CC BY 4.0" and r.citations[0].fact_id == "snapshot:weather/KE"


def test_rain_refuses_a_stale_forecast(engine, snaps):
    snaps.put(weather(code=engine.services.places.find("Embu", "KE").code, fresh=False))
    r = at(engine, "rain_this_week")
    assert isinstance(r, Refusal) and r.reason == "stale" and "Kenya Meteorological Department" in r.text["en"]


def test_rain_asks_for_the_place_in_the_local_word(engine):
    r = run(engine, "rain_this_week", "rain this week").result
    assert r.reason == "needs_place" and "county" in r.text["en"] and "kaunti" in r.text["sw"]
    assert "state" in run(engine, "rain_this_week", "rain", country="NG").result.text["en"]


# ---------------------------------------------------------------- warnings

def test_warning_found_by_area_name_is_passed_on_in_the_authoritys_words(engine, snaps):
    snaps.put(warnings(alerts=[alert(area_desc=["Embu, Meru and Tharaka counties"])]))
    r = at(engine, "official_warnings")
    assert isinstance(r, Answer)
    assert "Official warning for Embu from Kenya Meteorological Department" in r.text["en"]
    assert "Heavy rainfall alert" in r.text["sw"] and "Avoid crossing flooded rivers." in r.text["en"]


def test_warning_list_dashes_are_tidied_and_french_names_the_source(engine, snaps):
    snaps.put(warnings(alerts=[alert(area_desc=["Embu"], instruction="Communities are advised to: - stay inside. "
                                                                     "-avoid open areas -avoid rivers")]))
    r = at(engine, "official_warnings")
    assert "advised to: stay inside. avoid open areas; avoid rivers" in r.text["en"]
    assert "(source : Kenya Meteorological Department)" in r.text["fr"]


def test_warning_found_by_polygon_and_nationwide(engine, snaps):
    square = [[-1.0, 37.0], [-1.0, 38.0], [0.0, 38.0], [0.0, 37.0], [-1.0, 37.0]]
    snaps.put(warnings(alerts=[alert(polygons=[square])]))
    assert isinstance(at(engine, "official_warnings"), Answer) and "Official" in at(engine, "official_warnings").text["en"]
    snaps.put(warnings(alerts=[alert(area_desc=["Countrywide"])]))
    assert "Heavy rainfall alert" in at(engine, "official_warnings").text["en"]


def test_no_warning_is_said_only_when_the_feed_was_checked(engine, snaps):
    r = at(engine, "official_warnings")
    assert isinstance(r, Answer) and r.text["en"].startswith("No official warning from Kenya Meteorological Department")
    snaps.put(warnings(fresh=False))
    r = at(engine, "official_warnings")
    assert isinstance(r, Refusal) and r.reason == "stale" and "cannot tell" in r.text["en"]


def test_a_stale_mirror_is_never_read_as_no_warning(engine, snaps):
    snap = warnings(primary=False)
    snap.meta["newest_item"] = iso(NOW - timedelta(days=200))
    snaps.put(snap)
    assert at(engine, "official_warnings").reason == "stale"


def test_warning_gap_is_named_for_rwanda_and_namibia(engine):
    for country, authority in (("RW", "Rwanda Meteorology Agency"), ("NA", "Namibia Meteorological Service")):
        r = run(engine, "official_warnings", "warnings", country=country).result
        assert r.reason == "gap" and authority in r.text["en"]


# ---------------------------------------------------------------- facilities

def test_nearest_facility_by_position_ends_with_the_emergency_number(engine):
    r = run(engine, "nearest_facility", "nearest clinic", location=GeoPoint(-0.53, 37.45)).result
    assert isinstance(r, Answer)
    assert r.text["en"].startswith("Nearest public facilities: Kamweli Dispensary (dispensary, 0.2 km)")
    assert "Emergency: 999, 112, 1199." in r.text["en"] and "2019" in r.text["en"]
    assert "Far Clinic" not in r.text["en"]


def test_facility_by_area_lists_hospitals_inside_it(engine):
    r = at(engine, "nearest_facility")
    assert r.text["en"].startswith("Public hospitals in Embu: Embu Level 5 Hospital")


@pytest.mark.parametrize("country,numbers", [("TG", None), ("SN", "15, 1515"), ("CI", "185"), ("BW", "997"),
                                             ("NA", "10111")])
def test_facility_never_guesses_an_emergency_number(engine, snaps, country, numbers):
    snaps.put(facilities(country))
    r = run(engine, "nearest_facility", "nearest clinic", country=country, location=GeoPoint(-0.53, 37.45)).result
    text = r.text["en"]
    if numbers is None:  # Togo publishes no medical emergency number ACE can source
        assert "call your local emergency number" in text and "112" not in text
    else:
        assert numbers in text and (country == "NA" or "112" not in text)


def test_facility_ranks_bigger_hospitals_first():
    from ace_engine.services.facility import tier
    kinds = ["district hospital", "hospital", "national referral hospital", "regional hospital"]
    assert sorted(kinds, key=tier) == ["national referral hospital", "regional hospital", "district hospital", "hospital"]


def test_facility_source_artefacts_are_repaired():
    from ace_engine.connectors.health_facilities import clean_text
    assert clean_text("Bafilo Centre Hospitalier Pr\u251c\u2310fectoral") == "Bafilo Centre Hospitalier Préfectoral"
    assert clean_text("St. Mary'S  Lacor Hospital") == "St. Mary's Lacor Hospital"
    assert clean_text("O'Brien Clinic") == "O'Brien Clinic"


# ---------------------------------------------------------------- prices

def test_price_prefers_the_food_itself_and_compares_months(engine):
    r = at(engine, "market_prices", place="maize Embu")
    assert r.text["en"] == ("Maize (white) at Embu: KES 55 per KG in Oct 2026, up 10% on Sep 2026. WFP prices.")


def test_price_speaks_the_food_and_unit_in_the_persons_language(engine):
    r = at(engine, "market_prices", place="maize Embu")
    assert r.text["sw"].startswith("Mahindi (nyeupe) soko la Embu: KES 55 kwa KG")
    assert r.text["fr"].startswith("Maïs (blanc) au marché d'Embu : KES 55 le KG")
    from ace_engine.services.prices import food_name, unit_name
    assert food_name("Sorghum (red)", "fr") == "Sorgho (rouge)" and food_name("Gari", "sw") == "Gari"
    assert unit_name("90 KG", "fr") == "les 90 KG" and unit_name("KG", "fr") == "le KG"


def test_price_without_a_food_lists_staples(engine):
    r = at(engine, "market_prices", place="Embu")
    assert r.text["en"].startswith("Latest WFP prices at Embu: Maize (white) KES 55 per KG (Oct 2026); Maize flour")


def test_old_prices_are_refused_and_botswana_is_a_gap(engine, snaps):
    snaps.put(prices(month="2026-03"))
    r = at(engine, "market_prices", place="maize Embu")
    assert isinstance(r, Refusal) and r.reason == "stale" and "Mar 2026, too old to use" in r.text["en"]
    r = run(engine, "market_prices", "maize", country="BW").result
    assert r.reason == "gap" and "Botswana" in r.text["en"] and "pour le Botswana" in r.text["fr"]


# ---------------------------------------------------------------- pregnancy and pests

@pytest.mark.parametrize("weeks,expected", [
    (8, "go for your first antenatal check now"), (22, "next antenatal check is due at 26 weeks"),
    (30, "check is due now. The next is at 34 weeks"), (42, "past the last planned check"),
])
def test_pregnancy_schedule(engine, weeks, expected):
    r = run(engine, "pregnancy_companion", params={"weeks": weeks}).result
    assert expected in r.text["en"] and "999" in r.text["en"]
    assert {c.fact_id for c in r.citations} == {"africa-antenatal-care/eight-contacts",
                                                 "africa-maternal-danger-signs/go-now"}


def test_pregnancy_asks_for_weeks_and_still_gives_danger_signs(engine):
    r = run(engine, "pregnancy_companion", "when is my clinic").result
    assert r.reason == "needs_weeks" and "Go to a facility NOW" in r.text["en"]


@pytest.mark.parametrize("text,problem", [
    ("maize leaves with holes and sawdust", "fall_armyworm"), ("maize leaves yellow and drying", "maize_lethal_necrosis"),
    ("cassava leaves curled", "cassava_mosaic"), ("migomba majani njano", "banana_xanthomonas_wilt"),
    ("tomate feuilles avec galeries", "tomato_leaf_miner"),
])
def test_pest_check_names_the_likely_problem(engine, text, problem):
    r = run(engine, "pest_check", text).result
    assert isinstance(r, Answer) and r.data["problem"] == problem and len(r.citations) == 2


def test_pest_check_does_not_repeat_the_signs_label(engine):
    r = run(engine, "pest_check", "maize leaves with holes and sawdust").result
    assert "check these signs: windowpane" in r.text["en"] and "Armyworm signs" not in r.text["en"]
    r = run(engine, "pest_check", "banana leaves wilting", lang="fr").result
    assert "du flétrissement" in r.text["fr"] and "de le " not in r.text["fr"]


def test_pest_check_never_prescribes(engine):
    for text in ("maize leaves with holes", "cassava curled", "tomato tunnels"):
        out = run(engine, "pest_check", text).result.text["en"].lower()
        assert "ml" not in out.split() and "litre" not in out and "rate" not in out.split()


# ---------------------------------------------------------------- engine, USSD, API, MCP

def test_engine_routes_and_remembers_the_pending_service(engine):
    first = engine.ask("will it rain this week?", sender=KE)
    assert first.kind is ReplyKind.CLARIFY and "county" in first.text
    second = engine.ask("Embu", sender=KE)
    assert second.kind is ReplyKind.ANSWER and second.text.startswith("Rain near Embu")
    assert second.actions[0]["service"] == "rain_this_week" and second.actions[0]["preview"] is True


def test_an_unrelated_reply_releases_the_pending_service(engine):
    engine.ask("rain this week", sender=KE)
    assert engine.ask("How do I store maize after harvest?", sender=KE).actions == []


def test_safety_rail_still_runs_before_every_service(engine):
    assert engine.ask("rain this week and my wife is pregnant and bleeding", sender=KE).kind is ReplyKind.EMERGENCY
    reply = engine.run_service("pregnancy_companion", Message(channel=Channel.USSD, sender=KE, text="bleeding"))
    assert reply.kind is ReplyKind.EMERGENCY


def test_v1_engine_without_snapshots_is_unchanged():
    v1 = Engine.from_packs(ROOT / "context_packs", snapshots=None)
    assert v1.services is None and detect("rain in Embu") == "rain_this_week"
    assert v1.ask("rain in Embu").actions == []


def test_ussd_services_menu_and_flow(engine):
    app = UssdApp(engine)
    menu = app.respond(KE, "")
    assert "1 Rain this week" in menu and "6 Crop problem check" in menu and "7 Topics" in menu
    assert app.respond(KE, "1") == "CON Type your county:"
    answer = app.respond(KE, "1*Embu")
    assert answer.startswith("CON Rain near Embu") and len(answer) <= 182
    assert app.respond(KE, "7").startswith("CON Topics\n1 ")
    assert "Kliniki" not in app.respond("+255711000101", "5")  # Swahili default in Tanzania asks weeks
    assert app.respond(KE, "5*bleeding").startswith("END ")


def test_api_services_routes(engine):
    app = AceApp(engine, api_token="", webhook_secret="")

    def call(method, path, body=None):
        raw = json.dumps(body or {}).encode()
        env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "", "CONTENT_LENGTH": str(len(raw)),
               "wsgi.input": io.BytesIO(raw)}
        out = {}
        data = b"".join(app(env, lambda s, h: out.update(status=s)))
        return out["status"], json.loads(data)

    status, listing = call("GET", "/v1/services")
    assert status.startswith("200") and {s["id"] for s in listing["services"]} == set(SERVICES)
    assert listing["services"][1]["coverage"]["RW"]["available"] is False
    status, res = call("POST", "/v1/services/market_prices", {"country": "KE", "place": "Embu", "food": "maize"})
    assert res["outcome"] == "answer" and res["place"]["name"] == "Embu" and res["citations"]
    status, res = call("POST", "/v1/services/nearest_facility", {"country": "KE", "text": "my child drank paraffin"})
    assert res["outcome"] == "emergency"


def test_mcp_exposes_every_service(engine):
    tools = build_tools(engine)
    for name in (*SERVICES, "service_coverage"):
        assert name in tools
    res = tools["market_prices"]("KE", "Embu", "beans")
    assert res["outcome"] == "answer" and "Beans" in res["text"]
    assert tools["service_coverage"]()["market_prices"]["BW"]["available"] is False


def test_hub_rejects_unknown_service_and_country(snaps):  # noqa: D103
    hub = ServiceHub(snaps)
    with pytest.raises(ValueError):
        hub.call("weather_magic", "KE")
    with pytest.raises(ValueError):
        hub.call("rain_this_week", "XX")
