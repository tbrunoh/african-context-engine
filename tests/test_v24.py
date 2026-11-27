"""ACE 2.4: the public product. Private web sessions, the site, durable state, snapshot sets, MCP over HTTP, the
facility index, four more safety categories, the relevance test, citations and the production factory."""
from __future__ import annotations

import io
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ace_engine import __version__, i18n
from ace_engine.app import UnsafeConfig, check_production, create_app
from ace_engine.channels import UssdApp
from ace_engine.engine import Engine, EngineConfig
from ace_engine.identity import DEV_SALT, ProfileStore, web_country, web_sender
from ace_engine.models import Channel, Message, ReplyKind
from ace_engine.server import AceApp
from ace_engine.stores import CountingHandoffs, FirestoreProfileStore, profile_from_doc, profile_to_doc
from ace_engine.text import SUPPORTED_LANGUAGES

ROOT = Path(__file__).resolve().parents[1]
SALT = "a-test-salt-that-is-long-enough-for-production-use"
TOKEN = "abcdefghijklmnopqrstuvwx"


def call(app, method, path, body=None, headers=None, content_type="application/json"):
    raw = json.dumps(body).encode() if isinstance(body, dict) else (body or b"")
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "", "CONTENT_LENGTH": str(len(raw)),
           "CONTENT_TYPE": content_type, "wsgi.input": io.BytesIO(raw), "wsgi.url_scheme": "http"}
    env.update(headers or {})
    out = {}
    payload = b"".join(app(env, lambda s, h: out.update(status=s, headers=h)))
    return int(out["status"].split()[0]), dict(out["headers"]), out["headers"], payload


@pytest.fixture()
def public(engine):
    return AceApp(engine, api_token="", webhook_secret="", public=True)


# ---------------------------------------------------------------- web sessions


def test_web_sender_has_a_country_and_no_phone_number(engine):
    sender = web_sender("ng", TOKEN)
    assert sender == f"web:NG:{TOKEN}" and web_country(sender) == "NG" and engine.country_for(sender) == "NG"
    with pytest.raises(ValueError):
        web_sender("XX", TOKEN)
    with pytest.raises(ValueError):
        web_sender("NG", "short")
    store = ProfileStore(salt="s")
    assert store.key_for(web_sender("NG", TOKEN)) != store.key_for(web_sender("NG", TOKEN[::-1]))


def test_try_phone_answers_with_a_private_session(public):
    body_in = {"country": "GH", "channel": "sms", "text": "my child drank paraffin"}
    code, h, raw, body = call(public, "POST", "/try/message", body_in)
    data = json.loads(body)
    assert code == 200 and data["kind"] == "emergency" and "193" in data["text"] and data["segments"]
    cookie = h["Set-Cookie"]
    assert cookie.startswith("ace_try=") and "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert "Path=/try" in cookie and "Secure" in cookie and "Max-Age=86400" in cookie
    token = cookie.split(";")[0].split("=", 1)[1]
    # the same browser keeps its session: a two step question works
    ask = {"country": "KE", "channel": "sms", "text": "Will it rain this week?"}
    first = json.loads(call(public, "POST", "/try/message", ask, {"HTTP_COOKIE": f"ace_try={token}"})[3])
    second = json.loads(call(public, "POST", "/try/message", {"country": "KE", "channel": "sms", "text": "Nakuru"},
                             {"HTTP_COOKIE": f"ace_try={token}"})[3])
    assert first["kind"] in ("clarify", "answer") and "Nakuru" in second["text"]


def test_try_ussd_counts_the_screen(public):
    code, h, _, body = call(public, "POST", "/try/ussd", {"country": "ET", "language": "am", "text": ""})
    data = json.loads(body)
    assert code == 200 and not data["end"] and data["limit"] == 80 and data["chars"] <= 80 and data["language"] == "am"


def test_try_needs_json_a_country_and_a_known_language(public):
    assert call(public, "POST", "/try/message", b"country=KE&text=hi", content_type="application/x-www-form-urlencoded")[0] == 400
    assert call(public, "POST", "/try/message", {"channel": "sms", "text": "hi"})[0] == 400
    assert call(public, "POST", "/try/message", {"country": "KE", "language": "xx", "text": "hi"})[0] == 400
    assert call(public, "POST", "/try/message", {"country": "KE", "channel": "fax", "text": "hi"})[0] == 400


def test_try_forget_deletes_the_session(public):
    headers = {"HTTP_COOKIE": f"ace_try={TOKEN}"}
    call(public, "POST", "/try/message", {"country": "KE", "channel": "sms", "text": "LANG SW"}, headers)
    sender = web_sender("KE", TOKEN)
    assert public.engine.profiles.peek(sender).language == "sw"
    code, h, _, body = call(public, "POST", "/try/forget", {"country": "KE"}, headers)
    assert code == 200 and public.engine.profiles.peek(sender) is None and "ace_try=" in h["Set-Cookie"]
    assert TOKEN not in h["Set-Cookie"]  # a fresh session after FORGET
    fresh = h["Set-Cookie"].split(";")[0].split("=", 1)[1]
    assert 16 <= len(fresh) <= 64 and all(c.isalnum() or c in "-_" for c in fresh)  # a token, not a tuple


def test_a_public_server_trusts_no_phone_number(public, engine):
    body = {"text": "my child drank paraffin", "phone": "+254711000999", "country": "NG"}
    data = json.loads(call(public, "POST", "/v1/ask", body)[3])
    assert data["kind"] == "emergency" and "999" not in data["text"] and "112" in data["text"]
    assert engine.profiles.peek("+254711000999") is None and len(engine.profiles) == 0
    private = AceApp(engine, api_token="", webhook_secret="")
    call(private, "POST", "/v1/ask", {"text": "LANG SW", "phone": "+254711000999"})
    assert engine.profiles.peek("+254711000999").language == "sw"  # a private server still trusts it


# ---------------------------------------------------------------- the site


def test_automatic_clears_a_picked_language_and_forget_covers_every_country(public):
    from ace_engine import site

    token = "t" * 24
    ask = {"country": "KE", "channel": "sms"}
    assert site.try_message(public, {**ask, "language": "sw", "text": "habari"}, token)["language"] == "sw"
    assert site.try_message(public, {**ask, "language": "auto", "text": "what is the price of maize in Nairobi"},
                            token)["language"] == "en"
    site.try_message(public, {"country": "NG", "channel": "sms", "language": "ha", "text": "sannu"}, token)
    site.try_forget(public, {"country": "KE"}, token)
    assert public.engine.profiles.peek(web_sender("NG", token)) is None


def test_a_public_server_closes_unsigned_gateway_webhooks(engine):
    form = "application/x-www-form-urlencoded"
    app = AceApp(engine, public=True, webhook_secret="", whatsapp_app_secret="")
    for path, body in (("/sms", b"from=%2B254712345678&text=LANG+FR"), ("/ussd", b"phoneNumber=%2B254712345678&text="),
                       ("/voice", b"callerNumber=%2B254712345678")):
        assert call(app, "POST", path, body, content_type=form)[0] == 404, path
    assert call(app, "POST", "/whatsapp", {"entry": []})[0] == 404
    signed = AceApp(engine, public=True, webhook_secret="s" * 32)
    status = call(signed, "POST", "/sms", b"from=%2B254712345678&text=hello", {"QUERY_STRING": "key=" + "s" * 32},
                  content_type=form)[0]
    assert status == 200


@pytest.mark.parametrize("path", ["/", "/try", "/coverage", "/developers", "/status", "/about"])
def test_every_page_is_served_with_security_headers(public, path):
    code, h, _, body = call(public, "GET", path)
    assert code == 200 and h["Content-Type"].startswith("text/html")
    assert "default-src 'self'" in h["Content-Security-Policy"] and h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY" and b"{{" not in body and __version__.encode() in body
    assert b"style=" not in body  # the content security policy blocks inline styles


def test_the_ace_mark_is_every_icon_a_browser_or_phone_asks_for(public):
    for path, kind in (("/favicon.ico", "image/x-icon"), ("/apple-touch-icon.png", "image/png"),
                       ("/static/icon-192.png", "image/png"), ("/static/icon-512.png", "image/png")):
        status, headers, _, payload = call(public, "GET", path)
        assert status == 200 and headers["Content-Type"] == kind and payload, path
    status, headers, _, payload = call(public, "GET", "/site.webmanifest")
    data = json.loads(payload)
    assert status == 200 and data["short_name"] == "ACE" and data["theme_color"] == "#006B69"
    page = call(public, "GET", "/")[3].decode()
    assert f'href="/favicon.ico?v={__version__}"' in page and 'rel="apple-touch-icon"' in page


def test_static_files_and_no_path_tricks(public):
    code, h, _, body = call(public, "GET", "/static/ace.css")
    assert code == 200 and h["Content-Type"].startswith("text/css") and b"#006B69" in body
    assert call(public, "GET", "/static/site.js")[0] == 200
    assert call(public, "GET", "/static/inter-latin-400-normal.woff2")[1]["Content-Type"] == "font/woff2"
    for bad in ("/static/../site.py", "/static/.hidden", "/static/", "/static/nope.css"):
        assert call(public, "GET", bad)[0] == 404


def test_service_fields_with_the_wrong_type_get_400(public):
    for bad in ({"place": 123}, {"country": ["KE"]}, {"country": "KE", "weeks": "abc"}, {"lat": "x", "lon": 1}):
        status, _, _, payload = call(public, "POST", "/v1/services/pregnancy_companion", bad)
        assert status == 400 and b"must be" in payload, bad


def test_countries_status_and_health(public):
    countries = json.loads(call(public, "GET", "/v1/countries")[3])
    assert len(countries["countries"]) == 34 and len(countries["languages"]) == len(SUPPORTED_LANGUAGES) == 32
    ke = next(c for c in countries["countries"] if c["code"] == "KE")
    assert {"999", "112"} <= {n["number"] for n in ke["emergency"]} and ke["services"]["rain_this_week"]["available"]
    assert countries["languages"]["en"]["preview"] is False and countries["languages"]["sw"]["preview"] is True
    status = json.loads(call(public, "GET", "/v1/status")[3])
    assert status["version"] == __version__ and status["datasets"] and status["snapshot_set"]["set"] == "bundled"
    health = json.loads(call(public, "GET", "/healthz")[3])
    assert health["status"] == "ok" and health["version"] == __version__


def test_paused_site_answers_with_a_notice(engine):
    app = AceApp(engine, api_token="", webhook_secret="", public=True, paused=True)
    code, h, _, body = call(app, "GET", "/try")
    assert code == 503 and b"paused" in body
    assert call(app, "GET", "/healthz")[0] == 200
    assert call(app, "POST", "/v1/ask", {"text": "hello", "country": "KE"})[0] == 503


# ---------------------------------------------------------------- the factory


def test_production_refuses_unsafe_settings():
    assert check_production({"ACE_PSEUDONYM_SALT": SALT}) == []
    assert check_production({"ACE_PSEUDONYM_SALT": DEV_SALT})
    assert check_production({})
    assert check_production({"ACE_PSEUDONYM_SALT": SALT, "AT_API_KEY": "k"})  # a sender with no webhook secret
    assert check_production({"ACE_PSEUDONYM_SALT": SALT, "WHATSAPP_TOKEN": "t"})
    with pytest.raises(UnsafeConfig):
        create_app({"ACE_ENV": "production", "ACE_PSEUDONYM_SALT": "short"})


def test_create_app_builds_a_public_demo(engine):
    app = create_app({"ACE_PUBLIC": "1"}, engine=engine, start_threads=False)
    assert app.public and not app.trust_phone and app.engine is engine


def test_public_demo_switches_tip_off():
    engine = Engine.from_packs(ROOT / "context_packs", config=EngineConfig(tips=False))
    reply = engine.ask("TIP neem leaves help against armyworm", sender="+254711000001")
    assert reply.kind is not ReplyKind.SYSTEM and engine.tips.pending() == []
    help_text = engine.ask("HELP", sender="+254711000001", channel=Channel.API).text
    assert "TIP" not in help_text
    for lang in SUPPORTED_LANGUAGES:
        clarify = engine._clarify(lang, "KE").text
        on = Engine._clarify(Engine.from_packs(ROOT / "context_packs"), lang, "KE").text
        assert len(clarify) < len(on) and clarify.rstrip()[-1] in ".։።۔", (lang, clarify)


# ---------------------------------------------------------------- durable state


class FakeDoc:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def get(self):
        data = self.store.get(self.key)
        return type("Snap", (), {"exists": data is not None, "to_dict": lambda s: dict(data)})()

    def set(self, data, merge=False):
        self.store[self.key] = {**self.store.get(self.key, {}), **data} if merge else dict(data)

    def delete(self):
        self.store.pop(self.key, None)


class FakeFirestore:
    def __init__(self):
        self.data: dict[str, dict] = {}
        self.reads = 0

    def collection(self, name):
        client = self

        class Coll:
            def document(self, key):
                client.reads += 1
                return FakeDoc(client.data, f"{name}/{key}")
        return Coll()


def test_firestore_profiles_persist_expire_and_forget():
    db = FakeFirestore()
    engine = Engine.from_packs(ROOT / "context_packs", profiles=FirestoreProfileStore(db, salt=SALT))
    engine.profiles.begin_request()
    engine.handle(Message(Channel.SMS, "+254711000123", "LANG SW"))
    doc = next(v for k, v in db.data.items() if k.startswith("profiles/"))
    assert doc["language"] == "sw" and "history" not in doc and doc["expires_at"] > datetime.now(timezone.utc)
    assert "+254711000123" not in json.dumps(doc, default=str)  # no phone number in the document
    # another instance reads the same state
    other = Engine.from_packs(ROOT / "context_packs", profiles=FirestoreProfileStore(db, salt=SALT))
    assert other.profiles.peek("+254711000123").language == "sw"
    # an expired document is ignored even before Firestore deletes it
    for v in db.data.values():
        v["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    other.profiles.begin_request()
    assert other.profiles.peek("+254711000123") is None
    # FORGET deletes the document and nothing written later in the message brings it back
    engine.profiles.begin_request()
    engine.handle(Message(Channel.SMS, "+254711000123", "LANG FR"))
    engine.profiles.begin_request()
    engine.handle(Message(Channel.SMS, "+254711000123", "FORGET"))
    assert not [k for k in db.data if k.startswith("profiles/")]


def test_profile_documents_round_trip():
    from ace_engine.identity import Profile
    from ace_engine.models import GeoPoint

    p = Profile(key="k", language="ha", last_location=GeoPoint(12.0, 8.5), last_place=("NG", "KN"),
                pending_service="rain_this_week", pending_text="ruwa", channels=[Channel.SMS, Channel.USSD])
    back = profile_from_doc("k", profile_to_doc(p))
    assert (back.language, back.last_place, back.pending_service, back.channels) == ("ha", ("NG", "KN"), "rain_this_week",
                                                                                      [Channel.SMS, Channel.USSD])
    assert back.last_location.lat == 12.0


def test_counting_sink_keeps_no_words_and_gets_the_country():
    sink = CountingHandoffs()
    engine = Engine.from_packs(ROOT / "context_packs", handoffs=sink)
    engine.handle(Message(Channel.SMS, "+233241000001", "my child drank paraffin"))
    assert sink.counts == {("poisoning", "GH", "sms"): 1}
    assert "paraffin" not in repr(sink.__dict__)


# ---------------------------------------------------------------- thread safety


def test_ussd_screens_never_mix_under_threads():
    engine = Engine.from_packs(ROOT / "context_packs")
    app = UssdApp(engine)
    profile = engine.profiles.get_or_create("+251911000001")
    profile.language = "am"
    wrong: list[str] = []

    def run(phone: str, limit: int) -> None:
        for _ in range(60):
            screen = app.respond(phone, "")
            if len(screen) > limit:
                wrong.append(screen)

    threads = [threading.Thread(target=run, args=(p, lim)) for p, lim in
               [("+251911000001", 80), ("+254711000001", 182)] * 8]
    import sys
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(old)
    assert wrong == []


# ---------------------------------------------------------------- facility index


def test_facility_index_matches_the_boundary_test_and_is_fast():
    from ace_engine.geo import in_polygons
    from ace_engine.services import facility

    engine = Engine.from_packs(ROOT / "context_packs")
    ctx, snap = engine.services.ctx, facility.FacilityService.source(engine.services.ctx, "CD")
    index = facility.area_index(ctx, snap, "CD")
    area = next(rec for rec in ctx.places.areas("CD") if rec["name"] == "Bas-Uele")
    brute = [f for f in snap.records if in_polygons((f[4], f[5]), area["rings"])]
    assert index[area["code"]] == brute and brute
    start = time.perf_counter()
    reply = engine.run_service("nearest_facility", Message(Channel.API, "+243810000001", "Bas-Uele"))
    assert time.perf_counter() - start < 0.3 and reply.citations


# ---------------------------------------------------------------- snapshot sets


def test_publish_checks_and_swaps_snapshot_sets(tmp_path):
    from ace_engine.snapshots.manifest import SnapshotWatcher, check_set, prune, publish, read_manifest

    base = tmp_path / "snapshots"
    base.mkdir()
    first = publish(base, lambda folder: "refreshed")
    assert first["published"] and read_manifest(base)["set"] == first["set"] and first["refresh"] == "refreshed"
    engine = Engine.from_packs(ROOT / "context_packs")
    swapped = []
    watcher = SnapshotWatcher(engine, base, on_swap=swapped.append)
    assert watcher.check_once() and engine.services is swapped[0] and watcher.status()["set"] == first["set"]
    assert not watcher.check_once()  # nothing new

    def corrupt(folder: Path) -> None:
        path = next((folder / "prices").glob("*.json"))
        data = json.loads(path.read_text())
        data["records"] = data["records"][:-1]  # the checksum no longer matches
        path.write_text(json.dumps(data))

    later = datetime.now(timezone.utc) + timedelta(hours=1)
    bad = publish(base, corrupt, now=later)
    assert not bad["published"] and any("checksum" in p for p in bad["problems"])
    assert read_manifest(base)["set"] == first["set"] and check_set(base / first["set"]) == []
    removed = prune(base, keep=first["set"], now=later + timedelta(days=8))
    assert first["set"] not in removed and bad["set"] in removed


def test_a_swapped_set_answers_like_the_bundled_one(tmp_path):
    """A hub swapped in while serving keeps the pack facts and numbers that services cite."""
    from ace_engine.snapshots.manifest import SnapshotWatcher, publish

    base = tmp_path / "snapshots"
    base.mkdir()
    publish(base, lambda folder: "ok")
    engine = Engine.from_packs(ROOT / "context_packs")
    questions = [("my maize leaves have holes and worms", "+254712000000"),
                 ("I am 20 weeks pregnant, what should I know", "+254712000000")]
    before = [engine.ask(text, sender=phone) for text, phone in questions]
    before_contacts = engine.services.ctx.contacts("health_urgent", "KE")
    assert SnapshotWatcher(engine, base).check_once()
    after = [engine.ask(text, sender=phone) for text, phone in questions]
    assert [r.kind for r in after] == [r.kind for r in before] and [r.text for r in after] == [r.text for r in before]
    assert engine.services.ctx.contacts("health_urgent", "KE") == before_contacts and before_contacts


def test_watcher_keeps_the_last_good_set(tmp_path):
    from ace_engine.snapshots.manifest import SnapshotWatcher

    (tmp_path / "manifest.json").write_text(json.dumps({"set": "releases/missing"}))
    engine = Engine.from_packs(ROOT / "context_packs")
    before = engine.services
    watcher = SnapshotWatcher(engine, tmp_path)
    assert not watcher.check_once() and engine.services is before and watcher.status()["error"]


# ---------------------------------------------------------------- safety, relevance and citations


@pytest.mark.parametrize("text, phone", [
    ("our house is on fire", "+254711000001"), ("Nyumba yetu inaungua moto", "+255711000001"),
    ("ma maison brûle", "+221771000001"), ("my child is drowning in the river", "+256771000001"),
    ("he was stabbed and is bleeding", "+234803000001"), ("a car hit my son on the road", "+27820000001"),
    ("Mama amegongwa na gari", "+254711000001"), ("il a été poignardé", "+225070000001"),
    ("the kitchen is on fire", "+254711000001"), ("ma maison est en feu", "+221771000001"),
    ("he was shot in the leg", "+234803000001"), ("a child drowned in the dam", "+256771000001"),
    ("my child is on fire", "+254711000001"), ("our roof is on fire", "+254711000001"),
    ("the house next door is on fire", "+254711000001"), ("the forest is on fire", "+254711000001"),
    ("my clothes are on fire", "+254711000001"), ("my brother was shot", "+234803000001"),
    ("he was shot", "+234803000001"), ("she was shot", "+234803000001"), ("he got shot", "+234803000001"),
    ("they shot my brother", "+234803000001"), ("police shot my son", "+234803000001"),
    ("someone shot my husband", "+234803000001"), ("il a reçu une balle", "+221771000001"),
    ("on a tiré sur mon frère", "+221771000001"), ("she drowned", "+256771000001"), ("he drowned", "+256771000001"),
    ("accident on the highway many injured", "+254711000001"),
    ("boda boda knocked my child, she is bleeding from the head", "+254711000001"),
    ("the boat capsized and people are drowning", "+256771000001"), ("au secours ma maison prend feu", "+221771000001"),
    ("un camion a renversé un enfant sur la route", "+221771000001"),
    ("le feu brûle la cuisine, mes enfants sont dedans", "+221771000001"),
])
def test_four_new_safety_categories(engine, text, phone):
    reply = engine.ask(text, sender=phone)
    assert reply.kind is ReplyKind.EMERGENCY and reply.escalated


def test_a_fire_gets_the_general_emergency_numbers(engine):
    reply = engine.ask("our house is on fire", sender="+254711000001")
    assert reply.escalation_queue == "fire" and "999" in reply.text and "fire" in reply.text.lower()


@pytest.mark.parametrize("text", ["I am drowning in work this week", "my boss fired me", "Where can I buy a fire extinguisher?",
                                  "how do I claim insurance for my car", "this new song is on fire",
                                  "je cherche une assurance incendie", "I was shot a photo for my id",
                                  "the crowd drowned out the speaker", "the company is drowning in debt",
                                  "he shot me a message", "mettre la casserole au feu", "my idea was shot down",
                                  "I shot my first video today", "Où acheter un extincteur ?",
                                  "my phone battery gets hot like it is on fire", "spicy food sets my mouth on fire",
                                  "she got shot of her old car", "the noise drowned his voice"])
def test_lookalikes_do_not_raise_an_alarm(engine, text):
    assert engine.ask(text, sender="+254711000001").kind is not ReplyKind.EMERGENCY


@pytest.mark.parametrize("text", ["where can I donate blood", "how do I fix my car engine", "où donner mon sang"])
def test_off_topic_questions_get_no_fact_on_another_topic(engine, text):
    reply = engine.ask(text, sender="+254711000001")
    assert reply.kind is ReplyKind.CLARIFY and not reply.citations


@pytest.mark.parametrize("text, fact", [
    ("Someone says they sent me money by mistake", "sent-by-mistake"),
    ("how do I report a scam message", "report-333"),
    ("My maize leaves have holes and sawdust", "damage-signs"),
    ("how do I store maize", "drying-moisture"),
    ("my cassava leaves are yellow", "cmd-signs"),
    ("what are pregnancy danger signs", "go-now"),
    ("When are the long rains?", "two-seasons"),
])
def test_scam_and_crop_questions_still_get_their_answers(engine, text, fact):
    reply = engine.ask(text, sender="+254711000001")
    assert reply.kind in (ReplyKind.ANSWER, ReplyKind.SCAM) and any(c.fact_id.endswith(fact) for c in reply.citations)


def test_citations_carry_licence_and_date(engine):
    reply = engine.ask("how do I store maize", sender="+254711000001")
    assert reply.citations and all(c.licence == "CC-BY-4.0" and c.date for c in reply.citations)


def test_the_model_never_runs_for_ussd_or_voice():
    from ace_engine.router import GroundedGenerator

    class Provider:
        name = "fake"
        calls = 0

        def generate(self, system, prompt, timeout_s):
            Provider.calls += 1
            return "Dry maize to about 13 percent moisture before storing it [1]."

    engine = Engine.from_packs(ROOT / "context_packs", composer=GroundedGenerator(Provider()))
    engine.handle(Message(Channel.USSD, "+254711000001", "how do I store maize"))
    engine.handle(Message(Channel.VOICE, "+254711000001", "how do I store maize"))
    assert Provider.calls == 0
    engine.handle(Message(Channel.SMS, "+254711000001", "how do I store maize"))
    assert Provider.calls == 1


def test_every_locale_has_the_new_phrases_and_fire_opener():
    for code, loc in i18n.locales().items():
        for group in ("FIRE", "DROWNING", "STABBING", "ROAD_ACCIDENT"):
            assert loc.phrases.get(f"safety.{group}"), (code, group)
        assert "{numbers}" in loc.templates["safety.OPENERS.fire"], code


# ---------------------------------------------------------------- MCP over HTTP


def test_mcp_over_http_has_health_and_host_checks(engine):
    pytest.importorskip("mcp")
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient

    from ace_engine.mcp_server import http_app

    with TestClient(http_app(engine, ["ace.korext.com"]), base_url="https://ace.korext.com") as client:
        assert client.get("/healthz").json()["version"] == __version__
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        assert client.post("/mcp", json=init, headers=headers).status_code == 200
        assert client.post("/mcp", json=init, headers={**headers, "Host": "evil.example"}).status_code == 421


# ---------------------------------------------------------------- operations


class FakeRun:
    def __init__(self, env, minimum=0, conflicts=0):
        self.env = dict(env)
        self.minimum = minimum
        self.patches = 0
        self.version = 1
        self.conflicts = conflicts

    def get(self, url, timeout=0):
        env = [{"name": k, "value": v} for k, v in self.env.items()]
        body = {"etag": f"e{self.version}", "template": {"containers": [{"env": env}], "revision": "r1",
                                                       "scaling": {"minInstanceCount": self.minimum}}}
        return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: body})()

    def patch(self, url, json=None, params=None, timeout=0):
        if self.conflicts:  # another writer changed the service after our read
            self.conflicts -= 1
            self.version += 1
            return type("R", (), {"status_code": 409, "raise_for_status": lambda s: None})()
        assert json["etag"] == f"e{self.version}"
        self.patches += 1
        self.version += 1
        self.env = {e["name"]: e["value"] for e in json["template"]["containers"][0]["env"]}
        self.minimum = json["template"]["scaling"]["minInstanceCount"]
        return type("R", (), {"status_code": 200, "raise_for_status": lambda s: None})()


def test_paused_mcp_answers_503_and_health_still_answers(engine):
    pytest.importorskip("mcp")
    from starlette.testclient import TestClient

    from ace_engine.mcp_server import http_app

    client = TestClient(http_app(engine, ["ace.korext.com"], paused=True), base_url="https://ace.korext.com")
    assert client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).status_code == 503
    assert client.get("/healthz").json()["status"] == "paused"


def test_spend_guard_turns_the_model_off_then_pauses():
    from ace_engine.ops import guard

    assert guard.decide(40, 60) == {"ACE_LLM_DISABLED": None, "ACE_PAUSED": None}
    assert guard.decide(55, 60) == {"ACE_LLM_DISABLED": "1", "ACE_PAUSED": None}
    assert guard.decide(61, 60) == {"ACE_LLM_DISABLED": "1", "ACE_PAUSED": "1"}
    run = FakeRun({"ACE_PUBLIC": "1"})
    env = {"ACE_GUARD_PROJECT": "p", "ACE_GUARD_SERVICES": "ace-web"}
    guard.handle({"costAmount": 56, "budgetAmount": 60}, http=run, env=env)
    assert run.env == {"ACE_PUBLIC": "1", "ACE_LLM_DISABLED": "1"}
    guard.handle({"costAmount": 56, "budgetAmount": 60}, http=run, env=env)
    assert run.patches == 1  # no new revision when nothing changes
    guard.handle({"costAmount": 1, "budgetAmount": 60}, http=run, env=env)  # a new month
    assert run.env == {"ACE_PUBLIC": "1"}


def test_pause_scales_to_zero_and_a_new_month_restores_the_minimum():
    from ace_engine.ops import guard

    run = FakeRun({"ACE_PUBLIC": "1"}, minimum=1, conflicts=1)
    env = {"ACE_GUARD_PROJECT": "p", "ACE_GUARD_SERVICES": "ace-web", "ACE_GUARD_MIN_INSTANCES": "ace-web=1"}
    guard.handle({"costAmount": 61, "budgetAmount": 60}, http=run, env=env)
    assert run.env["ACE_PAUSED"] == "1" and run.minimum == 0 and run.patches == 1  # retried after the conflict
    guard.handle({"costAmount": 1, "budgetAmount": 60}, http=run, env=env)
    assert "ACE_PAUSED" not in run.env and run.minimum == 1


def test_paused_and_held_settings_reach_the_app():
    from ace_engine.app import composer_from_env

    base = {"ACE_LLM_BASE_URL": "https://example.org/v1", "ACE_LLM_MODEL": "m"}
    assert composer_from_env(base) is not None
    assert composer_from_env({**base, "ACE_LLM_DISABLED": "1"}) is None
    assert composer_from_env({**base, "ACE_LLM_HELD": "1"}) is None
