"""Release 2.4.1: a place ACE does not know, the spend cap, and the HTTPS redirect. No network."""
from __future__ import annotations

import base64
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from test_v2_services import KE, NOW, facilities, prices, warnings, weather

from ace_engine.engine import Engine
from ace_engine.models import Channel, Message
from ace_engine.ops import edge, guard, meter
from ace_engine.services import unknown_place
from ace_engine.snapshots import SnapshotStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def engine() -> Engine:
    store = SnapshotStore(ROOT / "snapshots")
    embu = next(r for r in store.get("places", "KE").records if r["name"] == "Embu")
    for snap in (weather(code=embu["code"]), warnings(), prices(), facilities()):
        store.put(snap)
    eng = Engine.from_packs(ROOT / "context_packs", snapshots=store)
    eng.services.clock = lambda: NOW
    return eng


def say(engine, text, sender=KE):
    return engine.handle(Message(Channel.SMS, sender, text))


# ---------------------------------------------------------------- a place ACE does not know


def test_an_unknown_place_is_asked_about_not_swapped_for_the_last_one(engine):
    assert "Embu" in say(engine, "rain this week in Embu").text
    reply = say(engine, "will it rain in Gotham this week")
    assert reply.text.startswith("Gotham? Which county are you in?") and "Embu" in reply.text  # Embu is the example
    assert reply.actions[0]["outcome"] == "needs_place" and reply.actions[0]["data"]["unknown_place"] == "Gotham"
    answer = say(engine, "Embu")  # the question waits for the place
    assert answer.actions[0]["outcome"] == "answer" and answer.text.startswith("Rain near Embu")


def test_a_known_place_and_a_follow_up_with_no_place_still_answer(engine):
    say(engine, "rain this week in Embu")
    assert say(engine, "rain this week").text.startswith("Rain near Embu")
    assert say(engine, "rain in my county").text.startswith("Rain near Embu")
    assert say(engine, "nearest hospital in Embu").actions[0]["outcome"] == "answer"


def test_unknown_places_in_other_languages(engine):
    say(engine, "mvua wiki hii huko Embu")
    assert say(engine, "mvua wiki hii huko Gotham").text.startswith("Gotham? Uko kaunti gani?")
    assert unknown_place("pluie à Gotham cette semaine") == "Gotham"
    assert unknown_place("chuva em Gotham") == "Gotham"
    assert unknown_place("hali ya hewa katika Gotham") == "Gotham"
    assert unknown_place("hospital near Kibera") == "Kibera"
    assert unknown_place("rain in Gotham Heights town") == "Gotham Heights"


@pytest.mark.parametrize("text", [
    "rain in the next days", "rain in my area", "rain in the morning", "rain in 3 days", "prices in shillings",
    "rain in June", "hospital in an emergency", "weather at home", "hospital near me", "pluie cette semaine",
    "pluie à la maison", "mvua na upepo", "no rain in sight", "prices in bulk", "rain in Kenya",
])
def test_everyday_words_after_in_are_not_places(text):
    assert unknown_place(text) is None


def test_the_api_still_asks_for_a_place_it_cannot_find(engine):
    out = engine.services.call("rain_this_week", country="KE", place="Gotham")
    assert out["outcome"] == "needs_place"


# ---------------------------------------------------------------- the HTTPS redirect


def test_the_redirect_map_is_applied_on_every_run():
    setup = (ROOT / "deploy" / "gcp" / "setup.sh").read_text()
    assert "name: ace-redirect" in setup  # 2.4.2 moved the redirect itself into ace-web: see test_v242.py
    assert "if ! exists gc compute url-maps describe ace-redirect" not in setup  # every run applies it
    smoke = (ROOT / "deploy" / "gcp" / "smoke.py").read_text()
    assert 'f"https://{host}/try?x=1"' in smoke


# ---------------------------------------------------------------- the spend cap: the estimate

CFG = meter.Config(project="p")
LATE = datetime(2026, 11, 28, 6, tzinfo=timezone.utc)   # 22:00 on 27 November in Pacific time


def test_fixed_charges_fall_as_the_levels_rise():
    month = [meter.hourly_fixed(CFG, level) * 744 for level in range(5)]
    assert 44 < month[0] < 46 and month[0] == month[1]   # about $45 a month at demonstration traffic
    assert month[2] < month[1] and month[4] < month[2]   # no warm instance, then no forwarding rules
    assert month[3] > month[2]                            # the closing rule itself costs $1 a month


def test_the_level_rises_with_spending_and_resets_with_the_month():
    assert meter.estimate(CFG, {}, LATE)["level"] == 0
    heavy = {"llm_input_tokens": 2e6, "llm_output_tokens": 0.8e6, "llm_requests": 3000, "llm_counted": 3000}
    assert meter.estimate(CFG, heavy, LATE)["level"] == 1          # about $13 of Gemini
    assert meter.estimate(CFG, {"lb_requests": 1.6e7}, LATE)["level"] == 2
    flood = {"lb_requests": 1.94e7}
    assert meter.estimate(CFG, flood, LATE)["level"] == 3
    assert meter.estimate(CFG, {"lb_requests": 3e7}, LATE)["level"] == 4
    december = datetime(2026, 12, 1, 9, tzinfo=timezone.utc)
    assert meter.estimate(CFG, {}, december)["level"] == 0
    assert meter.estimate(CFG, {}, LATE, floor=70)["level"] == 4    # a billed amount is a floor under the estimate


def test_gemini_is_priced_by_counted_tokens_and_uncounted_calls_at_the_ceiling():
    counted = meter.variable_cost({"llm_requests": 10, "llm_counted": 10, "llm_input_tokens": 8000,
                                   "llm_output_tokens": 2500})["gemini"]
    assert counted == round((8000 * meter.PRICE["llm_input_token"] + 2500 * meter.PRICE["llm_output_token"])
                            * meter.VARIABLE_MARGIN, 4)
    uncounted = meter.variable_cost({"llm_requests": 12, "llm_counted": 10, "llm_input_tokens": 8000,
                                     "llm_output_tokens": 2500})["gemini"]
    assert uncounted == round(counted + 2 * meter.llm_request_cost() * meter.VARIABLE_MARGIN, 4)


def test_the_month_follows_pacific_time():
    start = meter.month_start(datetime(2026, 12, 1, 7, tzinfo=timezone.utc))  # still 30 November in California
    assert (start.month, start.day) == (11, 1)
    end = meter.month_end(datetime(2026, 11, 15, tzinfo=timezone.utc))
    assert (end.month, end.day, end.hour) == (12, 1, 0)


# ---------------------------------------------------------------- the spend cap: a fake Google Cloud


class Resp:
    def __init__(self, body=None, status=200):
        self.body, self.status_code = body if body is not None else {}, status
        self.content = b"{}"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.body


class FakeCloud:
    """Cloud Run, Compute Engine, Cloud Monitoring and Firestore, as far as the guard uses them."""

    def __init__(self, usage=None, tokens=None, broken=(), level=None):
        self.usage = usage or {}
        self.tokens = tokens
        self.broken = set(broken)
        self.level = level  # the month's level the guard keeps in Firestore
        self.services = {"ace-web": {"env": {"ACE_PUBLIC": "1"}, "min": 1}, "ace-mcp": {"env": {}, "min": 0}}
        self.armor = [{"priority": 1000}, {"priority": 2147483647}]
        self.rules = {"ace-https-rule": {}, "ace-http-rule": {}}
        self.log = []

    def get(self, url, params=None, timeout=0):
        if "monitoring.googleapis.com" in url:
            metric = params["filter"].split('"')[1]
            if metric in self.broken:
                return Resp(status=500)
            key = next(k for k, m, _ in meter.METRICS if m == metric)
            value = self.usage.get(key, 0)
            return Resp({"timeSeries": [{"points": [{"value": {"doubleValue": value}}]}]} if value else {})
        if "firestore.googleapis.com" in url and "/spend/guard-" in url:
            return Resp(status=404) if self.level is None else Resp({"fields": {"level": {"integerValue": str(self.level)}}})
        if "firestore.googleapis.com" in url:
            if "firestore" in self.broken:
                return Resp(status=503)
            if self.tokens is None:
                return Resp(status=404)
            return Resp({"fields": {k: {"integerValue": str(v)} for k, v in self.tokens.items()}})
        if "/securityPolicies/" in url:
            return Resp({"rules": list(self.armor)})
        if "/forwardingRules/" in url:
            return Resp(status=200 if url.rsplit("/", 1)[1] in self.rules else 404)
        service = self.services[url.rsplit("/", 1)[1]]
        env = [{"name": k, "value": v} for k, v in service["env"].items()]
        return Resp({"etag": "e", "template": {"containers": [{"env": env}], "scaling": {"minInstanceCount": service["min"]}}})

    def patch(self, url, json=None, params=None, timeout=0):
        if "firestore.googleapis.com" in url:
            self.level = int(json["fields"]["level"]["integerValue"])
            self.log.append(("level", self.level))
            return Resp()
        service = self.services[url.rsplit("/", 1)[1]]
        service["env"] = {e["name"]: e["value"] for e in json["template"]["containers"][0]["env"]}
        service["min"] = json["template"]["scaling"]["minInstanceCount"]
        self.log.append(("run", url.rsplit("/", 1)[1]))
        return Resp()

    def post(self, url, json=None, params=None, timeout=0):
        if url.endswith("/addRule"):
            self.armor.append(json)
            self.log.append(("armor", "close"))
        elif url.endswith("/removeRule"):
            self.armor = [r for r in self.armor if r["priority"] != params["priority"]]
            self.log.append(("armor", "open"))
        elif url.endswith("/forwardingRules"):
            self.rules[json["name"]] = json
            self.log.append(("rule", "create", json["name"]))
        return Resp()

    def delete(self, url, timeout=0):
        del self.rules[url.rsplit("/", 1)[1]]
        self.log.append(("rule", "delete", url.rsplit("/", 1)[1]))
        return Resp()


ENV = {"ACE_GUARD_PROJECT": "p", "ACE_GUARD_SERVICES": "ace-web,ace-mcp", "ACE_GUARD_MIN_INSTANCES": "ace-web=1",
       "ACE_GUARD_ARMOR": "ace-armor", "ACE_GUARD_ADDRESS": "ace-ip", "ACE_CAP_USD": "60",
       "ACE_GUARD_RULES": "ace-https-rule=https:ace-https:443,ace-http-rule=http:ace-http:80"}


def test_the_guard_walks_every_level_and_a_new_month_restores_everything():
    cloud = FakeCloud()
    guard.apply(1, cloud, ENV)
    assert cloud.services["ace-web"]["env"] == {"ACE_PUBLIC": "1", "ACE_LLM_DISABLED": "1"}
    guard.apply(2, cloud, ENV)
    assert cloud.services["ace-web"]["env"]["ACE_PAUSED"] == "1" and cloud.services["ace-mcp"]["env"] == {"ACE_PAUSED": "1"}
    assert cloud.services["ace-web"]["min"] == 0
    guard.apply(3, cloud, ENV)
    assert any(r["priority"] == edge.CLOSE_PRIORITY and r["action"] == "deny(403)" for r in cloud.armor)
    before = len(cloud.log)
    guard.apply(3, cloud, ENV)
    assert len(cloud.log) == before  # nothing changes twice
    guard.apply(4, cloud, ENV)
    assert cloud.rules == {}
    guard.apply(0, cloud, ENV)
    https = cloud.rules["ace-https-rule"]
    assert https["portRange"] == "443" and https["target"].endswith("/targetHttpsProxies/ace-https")
    assert https["IPAddress"].endswith("/addresses/ace-ip") and https["loadBalancingScheme"] == "EXTERNAL_MANAGED"
    assert cloud.rules["ace-http-rule"]["target"].endswith("/targetHttpProxies/ace-http")
    assert all(r["priority"] != edge.CLOSE_PRIORITY for r in cloud.armor)
    assert cloud.services["ace-web"] == {"env": {"ACE_PUBLIC": "1"}, "min": 1}
    opened = cloud.log[cloud.log.index(("rule", "delete", "ace-http-rule")) + 1:]
    assert opened.index(("rule", "create", "ace-https-rule")) < opened.index(("armor", "open"))  # edge, then Armor


def test_the_guard_closes_from_the_inside_out():
    cloud = FakeCloud()
    guard.apply(4, cloud, ENV)
    kinds = [entry[0] for entry in cloud.log]
    assert kinds.index("armor") < kinds.index("run") < kinds.index("rule")


def test_a_run_measures_then_sets_the_level():
    cloud = FakeCloud(usage={"lb_requests": 1.94e7})
    result = guard.run(cloud, ENV, now=LATE)
    assert result["level"] == 3 and any(r["priority"] == edge.CLOSE_PRIORITY for r in cloud.armor)
    quiet = FakeCloud(usage={"run_requests": 5000}, tokens={"calls": 40, "input_tokens": 32000, "output_tokens": 9000})
    result = guard.run(quiet, {**ENV, "ACE_GUARD_ENFORCE": "0"}, now=LATE)
    assert result["level"] == 0 and "changed" not in result and quiet.log == []
    assert cloud.level == 3  # the month's level is kept
    assert result["usage"]["llm_input_tokens"] == 32000


def test_a_failed_read_is_an_error_never_zero_spending():
    with pytest.raises(RuntimeError, match="request_count"):
        guard.run(FakeCloud(broken={"loadbalancing.googleapis.com/https/request_count"}), ENV, now=LATE)
    for broken in ({"storage.googleapis.com/api/request_count"},
                   {"firestore.googleapis.com/document/read_ops_count", "storage.googleapis.com/api/request_count"}):
        cloud = FakeCloud(usage={"lb_requests": 1.6e7}, broken=broken, level=2)
        with pytest.raises(RuntimeError):
            guard.run(cloud, ENV, now=LATE)
        assert cloud.log == [] and cloud.level == 2 and "ace-https-rule" in cloud.rules  # nothing stored, nothing changed
        cloud.broken = set()
        assert guard.run(cloud, ENV, now=LATE)["level"] == 2 and cloud.level == 2
    cloud = FakeCloud(broken={"firestore"})  # a failed token read changes nothing, rather than pricing every call high
    with pytest.raises(RuntimeError):
        guard.run(cloud, ENV, now=LATE)
    assert cloud.log == []


def test_the_level_never_falls_within_a_month_and_resets_on_the_first():
    cloud = FakeCloud(level=4)  # the cap was reached earlier this month
    result = guard.run(cloud, ENV, now=LATE)
    assert result["estimated_level"] == 0 and result["level"] == 4 and cloud.rules == {}
    december = datetime(2026, 12, 1, 9, tzinfo=timezone.utc)
    cloud.level = None  # December's document does not exist yet
    result = guard.run(cloud, ENV, now=december)
    assert result["level"] == 0 and "ace-https-rule" in cloud.rules


def test_forwarding_rule_specs_are_checked():
    assert edge.parse_rules("a=https:p:443") == [("a", "https", "p", "443")]
    with pytest.raises(ValueError):
        edge.parse_rules("a=tcp:p:443")


def call_guard(path, method="POST", body=b""):
    out = {}

    def start(status, headers):
        out["status"] = status

    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(body)),
               "wsgi.input": io.BytesIO(body)}
    return out, json.loads(b"".join(guard.app(environ, start)))


def test_the_guard_endpoint(monkeypatch):
    seen = {}
    monkeypatch.setattr(guard, "run", lambda floor=0.0: seen.setdefault("floor", floor) or {"level": 0})
    out, _ = call_guard("/meter")
    assert out["status"] == "200 OK" and seen["floor"] == 0.0
    seen.clear()
    note = base64.b64encode(json.dumps({"costAmount": 58.5, "budgetAmount": 60}).encode()).decode()
    out, _ = call_guard("/", body=json.dumps({"message": {"data": note}}).encode())
    assert out["status"] == "200 OK" and seen["floor"] == 58.5
    seen.clear()
    note = base64.b64encode(json.dumps({"costAmount": 9000, "currencyCode": "KES"}).encode()).decode()
    call_guard("/", body=json.dumps({"message": {"data": note}}).encode())
    assert seen["floor"] == 0.0  # shillings are not dollars
    out, _ = call_guard("/meter", method="GET")
    assert out["status"].startswith("400")

    def fail(floor=0.0):
        raise RuntimeError("monitoring down")

    monkeypatch.setattr(guard, "run", fail)
    out, body = call_guard("/meter")
    assert out["status"].startswith("500") and body == {"error": "spend guard failed"}


# ---------------------------------------------------------------- the model's share of the cap


def test_each_model_call_has_a_ceiling_and_reports_its_tokens(monkeypatch):
    from ace_engine import router

    sent, counted = {}, []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}],
                               "usage": {"prompt_tokens": 700, "completion_tokens": 90, "total_tokens": 1000}}).encode()

    def urlopen(req, timeout=0):
        sent.update(json.loads(req.data))
        return Reply()

    monkeypatch.setattr(router.urllib.request, "urlopen", urlopen)
    provider = router.OpenAICompatibleProvider("https://example.org/v1", "m")
    provider.on_usage = lambda given, made: counted.append((given, made))
    assert provider.generate("s", "p", 2) == "ok"
    assert sent["max_tokens"] == 1024 and sent["max_tokens"] == meter.LLM_OUTPUT_TOKENS
    assert counted == [(700, 300)]  # reasoning left out of completion_tokens is still counted


def test_model_usage_is_counted_by_pacific_month():
    from ace_engine.stores import ModelUsage

    assert ModelUsage.month(datetime(2026, 12, 1, 7, tzinfo=timezone.utc)) == "llm-2026-11"
    assert ModelUsage.month(datetime(2026, 12, 1, 9, tzinfo=timezone.utc)) == "llm-2026-12"


def test_setup_gives_the_guard_only_what_it_needs():
    setup = (ROOT / "deploy" / "gcp" / "setup.sh").read_text()
    perms = setup.split('GUARD_PERMISSIONS="', 1)[1].split('"', 1)[0].split(",")
    assert "compute.securityPolicies.update" in perms and "compute.globalForwardingRules.delete" in perms
    assert not any(p.startswith(("compute.firewalls", "compute.instances", "iam.")) for p in perms)
    assert 'ace-meter --location "$SCHEDULER_REGION" --schedule "*/10 * * * *"' in setup
    assert "roles/datastore.user" in setup and "roles/monitoring.viewer" in setup
    assert "globalForwardingRules.list" not in perms and "globalOperations.get" not in perms
    assert "ACE_LLM_MAX_TOKENS=1024" in setup


# ---------------------------------------------------------------- the audit: the safety rail

MISSED = [
    ("My father is having a heart attack", "health_urgent"), ("He had a stroke and his face is drooping", "health_urgent"),
    ("My baby is choking", "health_urgent"), ("My child took rat poison", "poisoning"), ("She took poison", "poisoning"),
    ("she has taken poison", "poisoning"), ("my daughter took pills", "poisoning"), ("she cut her wrists", "self_harm"),
    ("I cut myself", "self_harm"), ("I don't want to live anymore", "self_harm"), ("I'm going to hang myself", "self_harm"),
    ("I feel like dying", "self_harm"), ("he is having a fit", "health_urgent"), ("he is not responding", "health_urgent"),
    ("she is unresponsive", "health_urgent"), ("He is bleeding badly", "health_urgent"),
    ("There is a lot of blood", "health_urgent"), ("my water broke", "maternal"),
    ("my wife is in labour and bleeding", "maternal"), ("He was electrocuted", "health_urgent"),
    ("my husband is dying please help", "health_urgent"), ("nataka kujinyonga", "self_harm"),
    ("amejinyonga", "self_harm"), ("mtoto anakabwa", "health_urgent"), ("je veux me pendre", "self_harm"),
    ("il s'est pendu", "self_harm"), ("mon pere fait une crise cardiaque", "health_urgent"),
    ("il a fait un AVC", "health_urgent"), ("mon bebe s'etouffe", "health_urgent"),
    ("he beat me to the ground", "gbv"), ("my child drowned", "health_urgent"),
    # Reports a 2.4.1 draft silenced, kept here for good
    ("My husband beats me, what should I do?", "gbv"), ("he beats me how do I get help", "gbv"),
    ("my boyfriend beats me what should I do", "gbv"), ("he beats me where can I go", "gbv"),
    ("My boyfriend beats me why", "gbv"), ("the rape leaves me scared", "gbv"),
    ("the market collapsed, many trapped", "health_urgent"),
    ("mume wangu amenipiga simu akasema ataniua", "gbv"), ("I cut myself", "self_harm"),
    ("she is not responding, please help", "health_urgent"), ("il fait une crise d'epilepsie", "health_urgent"),
    ("my son took the pills for his grandmother's blood pressure", "poisoning"), ("baby took pills", "poisoning"),
    ("my baby is dying of hunger", "health_urgent"), ("she started choking", "health_urgent"),
]


@pytest.mark.parametrize(("text", "queue"), MISSED)
def test_common_emergencies_reach_the_rail(text, queue):
    from ace_engine.safety import EscalationPolicy

    decision = EscalationPolicy().check(text)
    assert decision.escalate and decision.queue == queue


@pytest.mark.parametrize("text", [
    "Mtu amenipiga simu akisema ni wa Safaricom anataka PIN yangu", "When should I plant rape?",
    "Beats me why maize prices went up", "He beat me to it", "Ce qui me frappe c est le prix du mais",
    "Maize prices collapsed", "My seedlings are drowning in the rain", "My maize drowned in the floods",
    "How do I prevent a bushfire on my farm", "Cuire au feu de bois", "My stomach is on fire",
    "Je suis enceinte, quand faire la prise de sang", "Nina mimba, nifanye kipimo cha damu lini",
    "The child touched the hot stove", "my phone is not responding", "my maize is dying", "the app is unresponsive",
    "I took pills for malaria", "beats me how this works", "my maize is dying please help", "striga is choking my maize",
    "I took pesticide to the farm yesterday", "electric shock fence for goats", "My child took tablets for malaria yesterday",
    "mon fils fait une crise de colere", "he is not responding to my messages since he borrowed money",
    "I cut myself while cooking", "I gave a lot of blood", "she had a fit of laughter", "I feel like dying of hunger",
    "trop de medicaments est mauvais",
])
def test_everyday_phrases_stay_quiet(text):
    from ace_engine.safety import EscalationPolicy

    assert not EscalationPolicy().check(text).escalate


def test_every_ussd_emergency_screen_keeps_every_number():
    from ace_engine import encoding
    from ace_engine.channels.ussd import UssdApp
    from ace_engine.cli import _pack_roots
    from ace_engine.countries import COUNTRIES
    from ace_engine.safety import contacts_for, emergency_text_within

    eng = Engine.from_packs(*_pack_roots(None))
    app = UssdApp(eng)
    checked = 0
    for code, country in COUNTRIES.items():
        for lang in country.languages:
            for queue in ("self_harm", "maternal", "poisoning", "child_protection", "gbv", "fire", "health_urgent"):
                contacts = contacts_for(queue, eng._contact_facts(code), code)
                text = emergency_text_within(queue, contacts, lang,
                                             lambda t: len(encoding.gsm_fold(t)) <= app._screen(t) - 4)
                screen = app._end(text)
                assert all(c.number in screen for c in contacts), (code, lang, queue, screen)
                assert len(screen) <= app._screen(text), (code, lang, queue)
                checked += 1
    assert checked == 602
    screen = app.respond("+201001234567", "8*بيتنا يحترق")
    assert screen.startswith("END") and all(n in screen for n in ("123", "122", "180")) and len(screen) <= 80


EMERGENCY_TEXTS = {
    "en": ["I want to kill myself", "I am pregnant and bleeding heavily", "my child drank paraffin", "my husband beats me",
           "our house is on fire", "my father is not breathing", "my daughter was defiled"],
    "fr": ["je veux me suicider", "je suis enceinte et je saigne", "mon enfant a avale du petrole", "mon mari me bat",
           "notre maison brule", "mon pere ne respire plus", "ma fille a ete abusee"],
}


def test_first_time_callers_keep_every_number_on_ussd_in_every_country():
    """End to end, as a gateway sends it: a new caller in each country reports an emergency in English or French."""
    from ace_engine.channels.ussd import UssdApp
    from ace_engine.cli import _pack_roots
    from ace_engine.countries import COUNTRIES
    from ace_engine.safety import EscalationPolicy, contacts_for

    eng = Engine.from_packs(*_pack_roots(None))
    app = UssdApp(eng)
    n = 0
    for code, country in COUNTRIES.items():
        for texts in EMERGENCY_TEXTS.values():
            for text in texts:
                n += 1
                screen = app.respond(f"+{country.dial}7{n:08d}", "8*" + text)
                contacts = contacts_for(EscalationPolicy().check(text).queue, eng._contact_facts(code), code)
                assert screen.startswith("END") and all(c.number in screen for c in contacts), (code, text, screen)
                assert len(screen) <= (182 if all(ord(ch) < 0x250 for ch in screen) else 80), (code, text)


def test_the_ussd_menu_works_in_every_language():
    from ace_engine.channels.ussd import UI, UssdApp

    eng = Engine.from_packs(ROOT / "context_packs")
    app = UssdApp(eng)
    for n, code in enumerate(UI):
        phone = f"+2347{n:08d}"
        profile = eng.profiles.get_or_create(phone)
        profile.language = code
        eng.profiles.save(profile)
        assert app.respond(phone, "").startswith("CON"), code
        assert app.respond(phone, "8*my child drank paraffin").startswith("END"), code


def test_arabic_text_gets_the_ucs2_screen_whatever_the_profile_language():
    from ace_engine.channels.ussd import UssdApp

    app = UssdApp(Engine.from_packs(ROOT / "context_packs"))
    assert app._screen("Hello") == 182 and app._screen("مرحبا") == 80


# ---------------------------------------------------------------- the audit: public surfaces


def test_the_public_mcp_server_keeps_no_tips(monkeypatch):
    from ace_engine.mcp_server import tips_allowed

    assert tips_allowed({}) and not tips_allowed({"ACE_PUBLIC": "1"}) and not tips_allowed({"ACE_TIPS": "off"})
    setup = (ROOT / "deploy" / "gcp" / "setup.sh").read_text()
    assert '--set-env-vars "ACE_PUBLIC=1,ACE_MCP_ALLOWED_HOSTS=' in setup
    build = (ROOT / "deploy" / "gcp" / "cloudbuild.yaml").read_text()
    assert "--update-env-vars ACE_PUBLIC=1 --remove-env-vars ACE_COMMIT" in build


def test_mcp_health_names_its_commit_behind_the_load_balancer(engine, monkeypatch):
    pytest.importorskip("mcp")
    from starlette.testclient import TestClient

    from ace_engine.mcp_server import http_app

    monkeypatch.setenv("ACE_COMMIT", "0123456789abcdef")
    client = TestClient(http_app(engine, ["ace.korext.com"]), base_url="https://ace.korext.com")
    body = client.get("/mcp/healthz").json()
    assert body["status"] == "ok" and body["commit"] == "0123456789ab"
    assert client.get("/healthz").json()["commit"] == "0123456789ab"


def test_the_release_gate_checks_the_commit_and_a_candidate_mcp():
    build = (ROOT / "deploy" / "gcp" / "cloudbuild.yaml").read_text()
    # The commit comes from the image, never from the deploy, so a wrong image cannot report the right commit
    assert "--update-env-vars ACE_COMMIT" not in build and build.count("--remove-env-vars ACE_COMMIT") == 2
    assert "ACE_COMMIT=${COMMIT}" not in (ROOT / "deploy" / "gcp" / "setup.sh").read_text()
    assert '--header "x-ace-candidate: $$CANDIDATE" --commit ${_COMMIT}' in build
    assert build.index("update-traffic ace-mcp") > build.index("smoke.py")
    setup = (ROOT / "deploy" / "gcp" / "setup.sh").read_text()
    assert "ace-mcp-candidate-backend" in setup and setup.index("ace-mcp-candidate-backend") < setup.index(
        "ace-mcp-backend\n")


def call_app(engine, method, path, body=None):
    from ace_engine.server import AceApp

    app = AceApp(engine, public=True)
    out = {}
    raw = json.dumps(body).encode() if body is not None else b""
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "", "CONTENT_LENGTH": str(len(raw)),
               "wsgi.input": io.BytesIO(raw), "wsgi.url_scheme": "https", "HTTP_HOST": "ace.korext.com",
               "SERVER_NAME": "ace.korext.com", "SERVER_PORT": "443", "REMOTE_ADDR": "10.0.0.1"}
    data = b"".join(app(environ, lambda status, headers: out.update(status=status)))
    return out["status"], data


def test_api_fields_with_the_wrong_type_get_400(engine):
    status, _ = call_app(engine, "POST", "/v1/ask", {"text": "rain", "lat": [1], "lon": 2})
    assert status.startswith("400")
    status, _ = call_app(engine, "POST", "/v1/services/rain_this_week", {"country": "KE", "place": "Embu",
                                                                         "language": "xx"})
    assert status.startswith("400")


def test_a_public_deployment_hides_the_rcs_setting(engine):
    status, body = call_app(engine, "POST", "/rcs", {"message": {}})
    assert status.startswith("404") and b"RBM_CLIENT_TOKEN" not in body


def test_recordings_are_fetched_over_https_only():
    from ace_engine.speech.google import fetch_audio

    for url in ("file:///etc/passwd", "http://10.0.0.1/x.wav", "ftp://example.org/a", "https://127.0.0.1/x.wav",
                "https://169.254.169.254/latest", "https://10.1.2.3/a.wav"):
        with pytest.raises(ValueError):
            fetch_audio(url)


# ---------------------------------------------------------------- the audit: services and follow-ups


def test_weeks_outside_a_pregnancy_are_asked_again(engine):
    for weeks in (0, 46, 100, -3):
        assert engine.services.call("pregnancy_companion", country="KE", params={"weeks": weeks})["outcome"] == "needs_weeks"
    assert engine.services.call("pregnancy_companion", country="KE", params={"weeks": 20})["outcome"] == "answer"


def test_a_market_too_far_away_is_not_quoted(engine, monkeypatch):
    from ace_engine.services import prices

    monkeypatch.setattr(prices, "MAX_KM", 5)
    out = engine.services.call("market_prices", country="KE", place="Kisumu", params={"food": "maize"})
    assert out["outcome"] == "no_match" and "near Kisumu" in out["text"] and out["data"]["nearest_market_km"] > 5


def test_follow_ups_name_another_place_and_sources_name_the_data(engine):
    phone = "+254711000555"
    assert say(engine, "rain this week in Embu", phone).text.startswith("Rain near Embu")
    nakuru = say(engine, "What about Nakuru?", phone)
    assert nakuru.actions[0]["service"] == "rain_this_week" and "Nakuru" in nakuru.text
    assert say(engine, "Embu", phone).text.startswith("Rain near Embu")
    assert "Open-Meteo" in say(engine, "SOURCES", phone).text
    assert say(engine, "and in Gotham?", phone).text.startswith("Gotham? Which county")
    assert say(engine, "Embu", phone).text.startswith("Rain near Embu")  # the question waited for the place
    general = say(engine, "how do I grow maize in Nakuru", phone)
    assert not general.actions or general.actions[0].get("service") != "rain_this_week"


def test_an_unknown_name_answering_the_place_question_is_asked_about_once(engine):
    phone = "+254711000777"
    say(engine, "nearest hospital", phone)
    assert say(engine, "Gotham", phone).text.startswith("Gotham? Which county")
    assert say(engine, "Embu", phone).actions[0]["outcome"] == "answer"
    say(engine, "nearest hospital", "+254711000778")
    assert say(engine, "Gotham", "+254711000778").text.startswith("Gotham?")
    assert not say(engine, "Gotham", "+254711000778").text.startswith("Gotham?")  # asked once, then a new question


@pytest.mark.parametrize(("first", "then"), [
    ("rain this week", "armyworm"), ("bei ya mahindi", "viwavijeshi"), ("rain this week", "Armyworm"),
])
def test_a_question_after_the_place_question_is_answered_not_asked_about(engine, first, then):
    phone = "+254711000779"
    say(engine, first, phone)
    assert not say(engine, then, phone).text.lower().startswith(then.lower() + "?")


@pytest.mark.parametrize(("phone", "text"), [
    ("+254711000780", "nearest hospital near me, my wife is in labour"), ("+254711000781", "hospitali karibu na mimi"),
    ("+254711000782", "maize price in ksh"), ("+254711000783", "rain in coming days"),
    ("+254711000784", "in kiswahili"), ("+254711000785", "rain in northern parts"),
])
def test_everyday_words_never_become_an_unknown_place(engine, phone, text):
    say(engine, "rain this week in Embu", phone)
    assert "?" not in say(engine, text, phone).text.split(" ")[0]


@pytest.mark.parametrize("text", ["hôpital près de chez moi", "pluie à partir de demain", "hospital perto de mim"])
def test_everyday_words_in_french_and_portuguese_are_not_places(text):
    assert unknown_place(text) is None


def test_service_follow_up_state_survives_firestore():
    from ace_engine.identity import Profile
    from ace_engine.stores import profile_from_doc, profile_to_doc

    p = Profile(key="k", last_service="rain_this_week", last_sources=["Open-Meteo (https://open-meteo.com/)"])
    back = profile_from_doc("k", profile_to_doc(p))
    assert back.last_service == "rain_this_week" and back.last_sources == p.last_sources


def test_production_logs_carry_no_message_text_and_no_number(engine, monkeypatch, capsys):
    """Send a message with a phone number and a distinctive phrase through the site and the API in production mode:
    no log line may carry either."""
    monkeypatch.setenv("ACE_ENV", "production")
    secret, number = "zebra-violet-quorum", "+254711999888"
    call_app(engine, "POST", "/v1/ask", {"text": f"rain in Embu {secret}", "phone": number})
    call_app(engine, "POST", "/v1/ask", {"text": f"my child drank paraffin {secret}", "phone": number})
    out = capsys.readouterr()
    logged = out.out + out.err
    assert '"message": "answer"' in logged
    assert secret not in logged and number not in logged and "711999888" not in logged


def test_cloud_build_validates_the_packs():
    assert "ace packs validate" in (ROOT / "deploy" / "gcp" / "cloudbuild.yaml").read_text()
