"""Release 2.3: telling a language ACE speaks from one it does not, and saying so instead of answering in the wrong
language. The safety rail still runs first."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ace_engine import Engine, i18n, langid
from ace_engine.countries import COUNTRIES
from ace_engine.engine import EngineConfig
from ace_engine.langid import GlotLID, confirmed_by, grams, profiles, to_ace, unread_language
from ace_engine.models import Channel, Message, ReplyKind

ROOT = Path(__file__).resolve().parents[1]

GIKUYU = "Nĩ wega mũno nĩ ũndũ wa ũteithio waku, no ndĩrenda kũmenya kana mbura nĩ ĩkuura kũu gũcoka wiki ĩno"
DHOLUO = "Erokamano kuom konyruok, to adwaro ng'eyo ka koth biro chwe e dalawa e jumani ma biro ni"
MALAGASY = "Misaotra betsaka tamin'ny fanampianao, te hahafantatra aho raha hilatsaka ny orana amin'ity herinandro ity"


def test_profiles_cover_every_ace_language_and_name_the_others():
    langs = profiles()
    assert {c for c, p in langs.items() if p["ace"]} == set(i18n.all_languages())
    others = {c: p for c, p in langs.items() if not p["ace"]}
    assert len(others) >= 40 and all(p["name"] for p in others.values())
    # close neighbours whose speakers read an ACE language are deliberately absent
    assert not {"nbl", "kri", "bam", "emk", "tum"} & set(others)


def test_grams_read_folded_words_with_their_edges():
    assert grams("Ŋa!") == [" ng", "nga", "ga "]


@pytest.mark.parametrize("text,country,code", [(GIKUYU, "KE", "kik"), (DHOLUO, "KE", "luo"), (MALAGASY, None, "plt")])
def test_a_language_ace_does_not_speak_is_recognised_as_such(text, country, code):
    found = unread_language(text, COUNTRIES[country].languages if country else None)
    assert found is not None and found.code == code


def _ordinary_messages():
    data = yaml.safe_load((ROOT / "benchmark" / "sets" / "ordinary.yaml").read_text(encoding="utf-8"))
    return [(text, lang) for lang, texts in data.items() for text in texts]


def test_ace_never_turns_away_its_own_ordinary_messages():
    messages = _ordinary_messages()
    assert len({lang for _, lang in messages}) == 32 and len(messages) >= 200
    for text, lang in messages:
        for country in COUNTRIES.values():
            if lang in country.languages:
                assert unread_language(text, country.languages) is None, (lang, country.code, text)


def test_short_messages_and_other_scripts_are_never_judged():
    assert unread_language("Ũhoro waku?", COUNTRIES["KE"].languages) is None
    assert unread_language("ባለቤቴ እርጉዝ ናት እና ብዙ ደም እየፈሰሳት ነው አሁን ምን ላድርግ", COUNTRIES["ET"].languages) is None


@pytest.fixture(scope="module")
def engine():
    return Engine.from_packs(ROOT / "context_packs")


def test_ace_says_it_does_not_read_the_language_and_names_the_ones_it_does(engine):
    reply = engine.handle(Message(Channel.SMS, "+254700000101", GIKUYU))
    assert reply.kind is ReplyKind.SYSTEM and reply.language == "en"
    assert reply.text.startswith("ACE does not read this language yet") and "English or Kiswahili" in reply.text
    reply = engine.handle(Message(Channel.API, "+221770000101", DHOLUO))
    assert reply.language == "fr" and "Français ou Wolof." in reply.text and "15" in reply.text


def test_the_safety_rail_still_runs_first_in_any_language(engine):
    reply = engine.handle(Message(Channel.SMS, "+254700000102", GIKUYU + " snake bite"))
    assert reply.kind is ReplyKind.EMERGENCY


def test_a_chosen_language_is_always_answered_in(engine):
    engine.handle(Message(Channel.SMS, "+254700000103", "LANG SW"))
    reply = engine.handle(Message(Channel.SMS, "+254700000103", GIKUYU))
    assert reply.kind is not ReplyKind.SYSTEM or not reply.text.startswith("ACE")


class FakeIdentifier:
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def identify(self, text):
        self.calls += 1
        return self.answer


def test_a_plugged_in_identifier_can_overrule_the_check():
    offered = COUNTRIES["KE"].languages
    assert confirmed_by(None, GIKUYU, offered)
    assert not confirmed_by(FakeIdentifier([("sw", 0.92)]), GIKUYU, offered)
    assert confirmed_by(FakeIdentifier([("kik_Latn", 0.97)]), GIKUYU, offered)
    assert confirmed_by(FakeIdentifier([("sw", 0.3)]), GIKUYU, offered)

    class Broken:
        def identify(self, text):
            raise RuntimeError("provider down")
    assert confirmed_by(Broken(), GIKUYU, offered)


def test_the_identifier_is_asked_only_about_messages_ace_would_turn_away():
    fake = FakeIdentifier([("sw", 0.95)])
    engine = Engine.from_packs(ROOT / "context_packs", config=EngineConfig(language_identifier=fake))
    engine.handle(Message(Channel.SMS, "+254700000104", "Mvua itanyesha lini wiki hii hapa Nairobi?"))
    assert fake.calls == 0
    reply = engine.handle(Message(Channel.SMS, "+254700000105", GIKUYU))
    assert fake.calls == 1 and not reply.text.startswith("ACE does not read")


def test_identifier_codes_map_onto_ace_codes():
    assert to_ace("__label__kin_Latn") == "rw" and to_ace("fuv") == "fuf" and to_ace("ff") == "fuf"
    assert to_ace("sw-KE") == "sw" and to_ace("twi") == "ak" and to_ace("kik") == "kik"


def test_google_language_detection_request():
    from ace_engine.speech import google

    calls = []

    def post(url, body):
        calls.append((url, body))
        return {"languages": [{"languageCode": "ki", "confidence": 0.88}]}

    found = google.GoogleLanguageDetector(project="demo", post=post).identify(GIKUYU)
    assert found == [("ki", 0.88)]
    assert calls[0][0].endswith("/projects/demo/locations/global:detectLanguage")
    assert calls[0][1] == {"content": GIKUYU, "mimeType": "text/plain"}


def test_glotlid_needs_its_optional_package(monkeypatch):
    import builtins

    real = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "fasttext":
            raise ImportError("no fasttext")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError):
        GlotLID("model.bin")


def test_the_reply_exists_in_every_language():
    for code in i18n.added_languages():
        assert "{languages}" in i18n.locales()[code].templates["commands.TEXTS.unread"], code
    assert langid.MIN_GRAMS >= 16 and 0 < langid.MARGIN < 1


def test_profiles_record_their_licence_and_pinned_sources():
    import json

    data = json.loads(langid.PROFILES.read_text(encoding="utf-8"))
    assert data["licence"] == "CC BY-SA 4.0" and "FLORES-200" in data["built_from"]
    sources = json.loads((ROOT / "benchmark" / "langid" / "sources.json").read_text(encoding="utf-8"))
    assert len(sources["flores200"]["sha256"]) == 64 and len(sources["udhr_commit"]) == 40
    assert all(len(h) == 64 for h in sources["udhr"].values())


def test_profiles_are_rebuilt_after_a_locale_or_pack_change():
    import json
    import sys

    sys.path.insert(0, str(ROOT / "benchmark" / "langid"))
    import build

    data = json.loads(langid.PROFILES.read_text(encoding="utf-8"))
    assert data["ace_text_sha256"] == build.ace_text_digest(), "run: python benchmark/langid/build.py fetch && build"
    assert data["licence_url"].endswith("/by-sa/4.0/") and "NLLB" in data["attribution"]


# Fixes from the second independent review ------------------------------------------------------------------------

EVERYDAY = [  # messages in languages ACE speaks, full of names, places, links or Sheng, that must be answered
    ("+254700004001", "Weather forecast for Kirinyaga, Murang'a, Othaya, Karatina and Kangema this week"),
    ("+256700004002", "Price of matooke in Mbarara, Ntungamo, Kabale and Rukungiri today"),
    ("+233200004003", "Price of yam in Bolgatanga Navrongo Bawku Zebilla Paga market"),
    ("+244900004004", "Chuva em Huambo, Kuito, Menongue, Lubango e Ondjiva esta semana?"),
    ("+254700004005", "Mvua Othaya Karatina Mukurweini Kerugoya Kagio wiki hii?"),
    ("+254700004006", "Bei ya mahindi Oyugis Ndhiwa Kendu Bay Rongo Awendo Migori leo"),
    ("+254700004007", "Is this real? From: Kariuki Mwangi Gathoni Wambui Kinyanjui Ndungu"),
    ("+254700004008", "Nimetumiwa pesa na Otieno Odhiambo Achieng Akinyi Ochieng, ni kweli?"),
    ("+254700004009", "Sasa boss, nimeskia kuna scam ya mpesa inazunguka, hii message ni legit?"),
    ("+254700004010", "Ebu nicheki hii sms, inasema nimewin gari, nitume 2k ya processing"),
    ("+254700004011", "https://bit.ly/3xYz https://tinyurl.com/abcd https://cutt.ly/qwer"),
    ("+20100004012", "ana 3ayez a3raf el gaw bokra fel qahira law sama7t"),
    ("+212600004013", "salam bghit n3ref taman dyal l9am7 f souk lyoum"),
    ("+251911004014", "balebete betam temechegre new dem eyewetaw new"),
    ("+254700004015", "niaje msee, uko poa? nataka kujua bei ya unga leo kwa duka"),
    ("+234800004016", "Abeg how much be garri for Oyingbo market today, my pikin dey hungry"),
    ("+27820004017", "Ngicela ukwazi ukuthi imvula izona nini eThekwini naseMgungundlovu kuleli sonto"),
    ("+250780004018", "Ese imvura izagwa ryari i Musanze na Rubavu muri iki cyumweru?"),
]


@pytest.mark.parametrize("sender,text", EVERYDAY)
def test_everyday_messages_in_ace_languages_are_answered(engine, sender, text):
    reply = engine.handle(Message(Channel.SMS, sender, text))
    assert not reply.text.startswith(("ACE does not read", "ACE bado haisomi", "O ACE ainda", "ACE ne lit")), text


def test_the_answer_to_a_question_ace_asked_is_never_turned_away(engine):
    sender = "+254700004020"
    engine.handle(Message(Channel.SMS, sender, "Mvua itanyesha wiki hii?"))
    reply = engine.handle(Message(Channel.SMS, sender, "Niko Kirinyaga karibu na Kerugoya, Kagio na Kutus"))
    assert not reply.text.startswith("ACE")


def test_the_unread_reply_gives_the_emergency_numbers(engine):
    gikuyu_emergency = "Ndi na mũtumia wakwa ũrĩ na nda na nĩarathiaga thakame nyingĩ, ndeithia"
    reply = engine.handle(Message(Channel.SMS, "+254700004021", gikuyu_emergency))
    assert reply.text.startswith("ACE does not read") and "999" in reply.text and "112" in reply.text
    guinea = engine.handle(Message(Channel.SMS, "+224620004022", GIKUYU))
    if guinea.kind is ReplyKind.SYSTEM and "ACE" in guinea.text[:4]:
        assert "112" not in guinea.text  # Guinea has no national number: ACE names the health facility instead


def test_countries_with_arabic_amharic_or_tigrinya_are_never_judged():
    for code in ("EG", "MA", "SD", "TD", "ET", "SO"):
        assert unread_language(GIKUYU, COUNTRIES[code].languages) is None


def test_the_unread_reply_fits_a_ussd_screen(engine):
    reply = engine.handle(Message(Channel.USSD, "+27820004023", GIKUYU))
    assert len(reply.text) <= 182 and "112" in reply.text and "TS" in reply.text
    lang = engine.handle(Message(Channel.USSD, "+251911004024", "LANG"))
    assert lang.text.endswith("TI ትግርኛ") and len(lang.text) <= 80


def test_a_chosen_language_keeps_its_emergency_reply(engine):
    reply = engine.handle(Message(Channel.API, "+27820004025", "My wife is pregnant and bleeding", language="zu"))
    assert reply.escalated and reply.language == "zu"


def test_english_swahili_and_french_have_their_own_safety_phrases():
    from ace_engine import safety

    cd = COUNTRIES["CD"].languages
    assert safety.alarm_language("Mtoto wangu amekunywa mafuta ya taa", "fr", cd) == "sw"
    assert safety.EscalationPolicy().check("Mtoto wangu amekunywa mafuta ya taa").escalate


def test_more_identifier_codes_map_onto_ace_codes():
    assert to_ace("swc") == "sw" and to_ace("bam") == "dyu" and to_ace("arz") == "ar" and to_ace("nde") == "zu"


def test_google_language_detection_is_capped_and_quick():
    from ace_engine.speech import google

    calls = []
    detector = google.GoogleLanguageDetector(project="demo", post=lambda url, body: calls.append(body) or {})
    detector.identify("a" * 2000)
    assert len(calls[0]["content"]) == 500 and detector.timeout <= 3


def test_rate_limit_budget_resets_each_refresh(monkeypatch, tmp_path):
    from ace_engine import connectors
    from ace_engine.connectors import base

    monkeypatch.setattr(base, "_rate_waited", base.RATE_LIMIT_BUDGET)
    monkeypatch.setattr(connectors, "CONNECTORS", {})  # no network: only the reset runs
    connectors.refresh(tmp_path)
    assert base._rate_waited == 0.0


# Fixes from the third independent review -------------------------------------------------------------------------

@pytest.mark.parametrize("sender,text,lang", [
    ("+254700007001", "Roobku goorma ayuu da'ayaa Garissa, xoolahayga waa gaajoonayaan", "so"),
    ("+237670007002", "Yaushe ne ruwan sama zai sauka a Maroua, masarana sun bushe", "ha"),
    ("+263770007003", "Ngicela usizo, umntwana wami uyagula kakhulu", "zu"),
    ("+260970007004", "Mvua itanyesha lini, mahindi yangu yamekauka kabisa", "sw"),
    ("+258840007005", "Mvua itanyesha lini, mahindi yangu yamekauka kabisa", "sw"),
])
def test_ace_languages_written_from_across_a_border_are_read_and_answered(engine, sender, text, lang):
    reply = engine.handle(Message(Channel.SMS, sender, text))
    assert reply.kind is not ReplyKind.SYSTEM and reply.language == lang, reply.text


def test_the_ussd_turn_away_always_lists_the_languages_and_numbers(engine):
    from ace_engine import i18n
    from ace_engine.encoding import gsm_fold

    for country in COUNTRIES.values():
        reply = engine.handle(Message(Channel.USSD, f"+{country.dial}700007099", GIKUYU))
        if reply.kind is not ReplyKind.SYSTEM:
            continue
        text = gsm_fold(reply.text).lower()
        assert len(reply.text) <= 182
        for code in country.languages:
            assert code in text or gsm_fold(i18n.native_name(code)).lower() in text, (country.code, code)


def test_a_slow_identifier_never_keeps_a_person_waiting():
    import time

    class Slow:
        def identify(self, text):
            time.sleep(1)
            return [("sw", 0.99)]

    start = time.monotonic()
    assert confirmed_by(Slow(), GIKUYU, COUNTRIES["KE"].languages, deadline=0.1)
    assert time.monotonic() - start < 0.5


# Fixes from the fourth independent review ------------------------------------------------------------------------

@pytest.mark.parametrize("sender,text,lang", [
    ("+254700009101", "Kakamega hospital", "en"), ("+27820009102", "KwaZulu-Natal hospital", "en"),
    ("+256700009103", "Isingiro hospital", "en"), ("+264810009104", "Ohangwena hospital", "en"),
])
def test_place_names_never_move_a_message_into_another_language(engine, sender, text, lang):
    assert engine.handle(Message(Channel.SMS, sender, text)).language == lang


def test_a_county_reply_keeps_the_conversation_language(engine):
    sender = "+254700009105"
    engine.handle(Message(Channel.SMS, sender, "Mvua itanyesha wiki hii?"))
    assert engine.handle(Message(Channel.SMS, sender, "Garissa Wajir Mandera Isiolo")).language == "sw"


def test_place_name_messages_stay_in_the_country_languages(engine):
    from ace_engine.countries import ALSO_READ, readable
    from ace_engine.langid import detect_language

    for code in ALSO_READ:
        offered = COUNTRIES[code].languages
        also = readable(code)[len(offered):]
        places = engine._place_words(code)
        names = [rec["name"] for rec in engine.services.places.areas(code)]
        for message in [f"{n} hospital" for n in names] + [f"{a} {b}" for a in names[:12] for b in names[:12] if a != b]:
            # English is read everywhere, and hospital is English; no other cross-border language may take over
            assert detect_language(message, offered[0], offered, also, places) not in set(also) - {"en"}, (code, message)


def test_cross_border_emergencies_are_answered_in_their_language(engine):
    reply = engine.handle(Message(Channel.SMS, "+228900009106", "Ọmọ mi kò lè mí dáadáa"))
    assert reply.escalated and reply.language == "yo"


def test_an_english_overdose_is_caught_but_not_farm_dosage():
    from ace_engine.safety import EscalationPolicy

    assert EscalationPolicy().check("my son took an overdose").escalate
    for text in ("How do I avoid an overdose of fertiliser on my maize?", "Do not overdose the cattle dewormer"):
        assert not EscalationPolicy().check(text).escalate


def test_the_ussd_codes_end_their_sentence(engine):
    reply = engine.handle(Message(Channel.USSD, "+224620009107", GIKUYU))
    assert reply.text.startswith("FR ou FUF. ")


def test_the_identifier_counts_cross_border_languages(engine):
    fake = FakeIdentifier([("so", 0.9)])
    eng = Engine.from_packs(ROOT / "context_packs", config=EngineConfig(language_identifier=fake))
    eng.handle(Message(Channel.SMS, "+254700009108", GIKUYU))
    assert fake.calls == 1
    from ace_engine.countries import readable
    assert not confirmed_by(fake, GIKUYU, readable("KE"))


# Fixes from the fifth independent review -------------------------------------------------------------------------

@pytest.mark.parametrize("sender,text", [
    ("+229700011001", "she is bleeding heavily after birth"), ("+243700011002", "she is bleeding heavily after birth"),
    ("+221700011003", "my son took an overdose"), ("+225700011004", "she is bleeding heavily after birth"),
    ("+221700011005", "maize price in Dakar market"), ("+229700011006", "maize price in Alibori market"),
    ("+226700011007", "help me find a doctor in Bankui"), ("+221700011008", "Is there a clinic near Dakar?"),
    ("+254700011009", "Homa Bay hospital"), ("+225700011010", "weather in District Autonome d'Abidjan this week"),
])
def test_english_is_read_in_every_country(engine, sender, text):
    assert engine.handle(Message(Channel.SMS, sender, text)).language == "en", text


@pytest.mark.parametrize("dial,question,answer,lang", [
    ("+254", "Mvua itanyesha wiki hii?", "How do I store maize to avoid aflatoxin?", "en"),
    ("+237", "Will it rain this week?", "Comment conserver le maïs contre les charançons ?", "fr"),
    ("+254", "Mvua itanyesha wiki hii?", "Niko Kirinyaga karibu na Kerugoya", "sw"),
])
def test_a_clear_new_language_wins_over_the_pending_question(engine, dial, question, answer, lang):
    sender = f"{dial}700011{len(answer):03d}"
    engine.handle(Message(Channel.SMS, sender, question))
    assert engine.handle(Message(Channel.SMS, sender, answer)).language == lang


def test_a_region_named_like_a_language_answers_the_question(engine):
    sender = "+251911011020"
    engine.handle(Message(Channel.SMS, sender, "Rain this week?"))
    reply = engine.handle(Message(Channel.SMS, sender, "Somali"))
    assert reply.language == "en" and "Somali" in reply.text


# Fixes from the sixth independent review ------------------------------------------------------------------------

@pytest.mark.parametrize("sender,text", [
    ("+254700012001", "Nimeumwa na nyoka"), ("+254700012002", "Nimeng'atwa na nyoka mguu"),
    ("+255700012003", "Nimeumwa na nyoka mguuni"), ("+254700012004", "Nyoka ameniuma"),
    ("+254700012005", "My mother is struggling to breathe"), ("+254700012006", "my baby has stopped breathing"),
    ("+221700012007", "Mon mari me frappe tous les jours"), ("+243700012008", "Mwana na ngai amweli petrole"),
    ("+243700012009", "Mke wangu anatoka damu mingi baada ya kuzaa"), ("+233700012010", "Me ba no ntumi nhome, boa me"),
    ("+221700012011", "Sama doom naan na esans"), ("+251911012012", "ልጄ ነዳጅ ጠጣ ምን ላድርግ"),
    ("+27700012013", "Ngiyafa, ngisizeni"), ("+229700012014", "Ọmọ mi mu epo kẹrosíìnì"),
    ("+234700012015", "Ọmọ mi ò mí mọ́"), ("+27700012016", "Umfazi wami uyopha kakhulu ngemuva kokubeletha"),
    ("+27700012017", "Umntwana wami uphuze uphalafini"), ("+254700012018", "Nyathiwa omodho mafuta taa"),
    ("+234700012019", "Nwa m nweghị ike iku ume"), ("+254700012020", "Nyoka ameniuma nikiwa nachunga mbuzi"),
    ("+254700012021", "A dog bit my child and he is bleeding heavily"),
    # From the seventh review: an animal in the message never silences the person's emergency
    ("+254700012022", "my neighbour was bitten by a snake while herding the goats"),
    ("+254700012023", "farmer bitten by snake while milking cows"), ("+254700012024", "bibi amezimia akilisha kuku"),
    ("+254700012025", "Mwanangu ameumwa na nyoka akichunga mbuzi"),
    ("+254700012026", "ng'ombe amempiga teke mwanangu amepoteza fahamu"),
    ("+254700012027", "mbwa amemuuma mwanangu anatoka damu nyingi"),
    ("+221700012028", "un serpent a mordu mon voisin pres des chevres"),
    ("+254700012029", "wife bleeding alot after giving birth"), ("+258840012030", "quero me matar"),
    ("+258840012031", "meu marido me bate"), ("+254700012032", "baba amezirai hajitambui"),
    ("+254700012033", "mtoto amekunywa dawa ya kuua wadudu"), ("+254700012034", "i want to end it all tonight"),
    ("+243810012035", "mwasi na ngai azali kobimisa makila mingi"), ("+243810012036", "mobali na ngai abetaka ngai"),
    ("+256700012037", "njagala kwetta"), ("+233240012038", "me ba no nom kerosene"),
    ("+233240012039", "me kunu boro me"), ("+234800012040", "onye a adaala enweghị ume"),
    ("+237670012041", "my pikin don drink kerosine"), ("+250780012042", "inzoka yarumye umwana wanjye"),
    ("+27700012043", "inyoka iluma umntwana wami"), ("+252610012044", "abeeso ayaa qaniinay wiilkeyga"),
    ("+20100012045", "ثعبان لدغ ابني"), ("+221700012046", "jaan mat na ma"),
    ("+256700012047", "omusota gumuluma omwana wange"), ("+258840012048", "uma cobra mordeu o meu filho"),
])
def test_common_emergencies_get_the_emergency_reply(engine, sender, text):
    reply = engine.handle(Message(Channel.SMS, sender, text))
    assert reply.escalated, text


@pytest.mark.parametrize("text", [
    "I saw a snake in the maize, a bit scared", "Where can I donate blood in Nakuru?",
    "Ibiciro bya peteroli mu Kigali ni angahe?", "Mtoto wangu amezaliwa jana na yuko salama",
    "mke wangu ameanza kuumwa uchungu, je nyoka wanaingia nyumba", "I was a bit the worried after seeing a snake",
    "How do I keep snakes away from my chicken house?",
])
def test_everyday_messages_about_snakes_or_blood_raise_no_alarm(text):
    from ace_engine.safety import EscalationPolicy

    assert not EscalationPolicy().check(text).escalate, text


@pytest.mark.parametrize("sender", ["+261340012030", "+447700012031", "+12025012032", "+919800012033"])
def test_a_caller_from_outside_aces_countries_gets_no_other_countrys_number(engine, sender):
    for text in ("My baby is not breathing please help", "Tsy mahay miteny aho fa marary ny zanako dia mila dokotera aho",
                 "emergency numbers", "police number", "how do I report mpesa fraud"):
        reply = engine.handle(Message(Channel.SMS, sender, text))
        assert not any(ch.isdigit() for ch in reply.text), (text, reply.text)


def test_lang_with_a_language_ace_does_not_speak_shows_the_menu(engine):
    for text in ("LANG KIKUYU", "LANG KIKAMBA", "LUGHA KIKONGO", "LANG KI"):
        reply = engine.handle(Message(Channel.SMS, "+254700012050", text))
        assert reply.text.startswith("Reply LANG") or "LUGHA" in reply.text, (text, reply.text)
    assert engine.handle(Message(Channel.SMS, "+254700012051", "LANG SWA")).text == "ACE itajibu kwa Kiswahili."


@pytest.mark.parametrize("dial,question,answer,area", [
    ("+234", "Will it rain this week?", "Oyo", "Oyo"), ("+234", "Will it rain this week?", "Mo wa ni Oyo", "Oyo"),
    ("+234", "Will it rain in Ibadan this week?", None, "Oyo"), ("+27", "Will it rain in eThekwini this week?", None, "KwaZulu"),
    ("+27", "Will it rain in Polokwane?", None, "Limpopo"),
    ("+27", "Sal dit reën in Kaapstad hierdie week?", None, "Western Cape"),
    ("+251", "በአዲስ አበባ ዝናብ ይዘንባል?", None, "Addis Ababa"), ("+263", "Mvura ichanaya here muHarare svondo rino?", None, "Harare"),
])
def test_cities_and_place_names_with_prefixes_are_found(engine, dial, question, answer, area):
    sender = f"{dial}70001{len(question) * 7 + len(answer or ''):04d}"
    reply = engine.handle(Message(Channel.SMS, sender, question))
    if answer:
        reply = engine.handle(Message(Channel.SMS, sender, answer))
    assert area in reply.text, reply.text


def test_lingala_naming_a_price_is_answered_in_lingala(engine):
    reply = engine.handle(Message(Channel.SMS, "+243810012060", "Nalingi koyeba ntalo ya masangu na Kinshasa"))
    assert reply.language == "ln"


@pytest.mark.parametrize("text", ["emergency numbers", "Emergency number", "ambulance number", "nambari za dharura"])
def test_asking_for_the_emergency_number_in_kenya_gets_it(engine, text):
    reply = engine.handle(Message(Channel.SMS, "+254700012060", text))
    assert "999" in reply.text and "333" not in reply.text, reply.text


@pytest.mark.parametrize("dial,text,area", [
    ("+254", "Will it rain in Eldoret this week?", "Uasin Gishu"), ("+254", "Will it rain in Thika tomorrow?", "Kiambu"),
    ("+27", "Will it rain in Joburg?", "Gauteng"), ("+221", "Va-t-il pleuvoir à Touba cette semaine ?", "Diourbel"),
    ("+252", "Roob ma di doonaa Banaadir toddobaadkan?", "Banadir"), ("+20", "هل ستمطر بالقاهرة غدا؟", "Cairo"),
    ("+251", "በአማራ ዝናብ ይዘንባል?", "Amhara"),
])
def test_more_city_and_local_names_are_found(engine, dial, text, area):
    reply = engine.handle(Message(Channel.SMS, f"{dial}70002{len(text):04d}", text))
    assert area in reply.text, reply.text


def test_the_api_with_no_phone_gives_no_countrys_numbers():
    from ace_engine.server import _sender

    assert _sender({}).startswith("+888") and _sender({}) != _sender({}) and _sender({"country": "ng"}).startswith("+234")
    assert _sender({"phone": "+254711000000"}) == "+254711000000"


# Fixes from the eighth independent review ------------------------------------------------------------------------

@pytest.mark.parametrize("sender,text", [
    ("+254700013001", "i cant breathe"), ("+254700013002", "i want to kill my self"), ("+254700013003", "i wanna die"),
    ("+254700013004", "I took too many pills"), ("+254700013005", "he is unconcious"),
    ("+254700013006", "baby not breathin"), ("+254700013007", "my wife is bledding alot after birth"),
    ("+234800013008", "maciji ya ciji yarona"), ("+252610013009", "maska ayaa qaniinay wiilkeyga"),
    ("+20100013010", "لدغتني حية"), ("+20100013011", "ثعبان عض ابني"), ("+258840013012", "foi picado por uma cobra"),
    ("+221700013013", "piqué par un serpent"), ("+254700013014", "mume wangu amenichapa"),
    ("+265990013015", "mwamuna wanga amandimenya"), ("+258840013016", "nao esta a respirar"),
    ("+20100013017", "طفلي ما يتنفس"),
])
def test_more_emergencies_get_the_emergency_reply(engine, sender, text):
    assert engine.handle(Message(Channel.SMS, sender, text)).escalated, text


@pytest.mark.parametrize("text", [
    "tenho uma picada de mosquito mas nao tenho febre", "a picada da abelha doi mas passa",
    "quanto cobra a farmacia pela vacina da mordida de cao", "snake print yoga mat", "my friend Tara saw a snake",
    "maciji ya shiga gidan mutane tara", "የነዳጅ ተመን ጨመረ ንብ ነደፈኝ",
])
def test_words_that_mean_snake_or_bite_only_in_another_language_raise_no_alarm(text):
    from ace_engine.safety import EscalationPolicy

    assert not EscalationPolicy().check(text).escalate, text


@pytest.mark.parametrize("sender,text,lang", [
    ("+254700013020", "nyoka ameniuma", "sw"), ("+250780013021", "inzoka yandumye", "rw"),
    ("+27700013022", "inyoka ingilumile", "zu"),
])
def test_a_snake_bite_is_answered_in_the_language_it_was_written_in(engine, sender, text, lang):
    assert engine.handle(Message(Channel.SMS, sender, text)).language == lang


@pytest.mark.parametrize("sender", ["+447700013030", "+888000013031"])
def test_scam_replies_and_menus_give_no_countrys_number_outside_aces_countries(engine, sender):
    reply = engine.handle(Message(Channel.SMS, sender, "Your account is blocked send your PIN to 0712345678"))
    assert "333" not in reply.text, reply.text
    assert engine.packs_for(None) == [p for p in engine.packs if any(not f.scope.countries for f in p.facts)]


@pytest.mark.parametrize("text", ["numero d urgence", "numero de emergencia", "numero da policia"])
def test_kenyas_national_lines_answer_in_french_and_portuguese_too(engine, text):
    assert "999" in engine.handle(Message(Channel.SMS, "+254700013040", text)).text


@pytest.mark.parametrize("sender", ["+234800013050", "+229970013051"])
def test_english_about_winning_is_not_read_as_yoruba(engine, sender):
    assert engine.handle(Message(Channel.SMS, sender, "I got an SMS saying I won 50000 send pin")).language == "en"


def test_a_word_that_starts_like_a_prefix_is_not_a_place(engine):
    places = engine.services.places
    assert places.find("nataka kuchoma mahindi", "ZM") is None and places.find("kutanga mbegu", "TZ") is None
    assert places.find("Mvura ichanaya here muHarare", "ZW").name == "Harare"


# Fixes from the ninth independent review -------------------------------------------------------------------------

def test_somali_mas_counts_only_beside_a_somali_bite_word():
    from ace_engine.safety import EscalationPolicy

    for text in ("mas baa i qaniinay", "mas ayaa wiilkayga qaniinay"):
        assert EscalationPolicy().check(text).escalate, text
    assert not EscalationPolicy().check("tenho uma picada de mosquito mas nao tenho febre").escalate


def test_a_childs_overdose_gets_the_poisoning_reply(engine):
    assert engine.handle(Message(Channel.SMS, "+254700014001", "my daughter took too many pills")).escalation_queue == "poisoning"
    assert engine.handle(Message(Channel.SMS, "+254700014002", "I took too many pills")).escalation_queue == "self_harm"


@pytest.mark.parametrize("sender,text", [
    ("+201000014010", "ana 3ayez a3raf el ma6ar el osbo3 da"), ("+212600014011", "bghit n3ref chhal taman dyal l9amh"),
])
def test_arabic_in_latin_letters_is_answered_in_arabic(engine, sender, text):
    assert engine.handle(Message(Channel.SMS, sender, text)).language == "ar"


def test_mcp_questions_do_not_share_a_session():
    import inspect

    from ace_engine import mcp_server

    assert "secrets.randbelow" in inspect.getsource(mcp_server)


def test_phone_less_api_and_mcp_questions_keep_no_profile(engine):
    from ace_engine.server import _sender

    sender = _sender({})
    before = len(engine.profiles)
    engine.handle(Message(Channel.API, sender, "Will it rain this week?"))
    engine.profiles.forget(sender)
    assert len(engine.profiles) == before
