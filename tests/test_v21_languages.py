"""Release 2.1: eight languages, 34 countries, the alphabet a reply travels in, and the data problems ACE designs around."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from ace_engine import i18n
from ace_engine.channels.ussd import UssdApp, language_options
from ace_engine.commands import language_code
from ace_engine.connectors import held
from ace_engine.connectors.national_registries import malawi_records, plausible_phone, zambia_records
from ace_engine.countries import COUNTRIES, country_for_msisdn
from ace_engine.encoding import gsm_fold, is_gsm7, scale, sms_limit, ussd_limit
from ace_engine.engine import Engine
from ace_engine.models import Channel, Message, ReplyKind
from ace_engine.router import Budget
from ace_engine.services import facility, prices, warnings
from ace_engine.text import SUPPORTED_LANGUAGES, fold, guess_language, script_language, tokens

ROOT = Path(__file__).resolve().parents[1]
ADDED = ("pt", "ar", "am", "om", "so")
FIELD = re.compile(r"{(\w+)}")


def test_eight_languages_in_a_stable_order():
    assert SUPPORTED_LANGUAGES == ("en", "sw", "fr", "pt", "ar", "am", "om", "so")
    assert i18n.added_languages() == ADDED
    assert i18n.native_name("am") == "አማርኛ" and i18n.native_name("om") == "Afaan Oromoo"


def test_every_added_language_is_complete():
    assert i18n.missing() == {code: [] for code in ADDED}


def test_added_languages_are_marked_unreviewed():
    assert set(i18n.unreviewed()) == set(ADDED)


@pytest.mark.parametrize("code", ADDED)
def test_templates_keep_every_placeholder(code):
    """A translation that drops or renames {numbers} would send a reply with no number in it."""
    loc = i18n.locales()[code]
    for path, text in loc.templates.items():
        english = i18n.template(path, "en")
        if isinstance(text, str) and isinstance(english, str):
            assert set(FIELD.findall(text)) == set(FIELD.findall(english)), (code, path)


def test_country_languages_are_supported():
    for c in COUNTRIES.values():
        assert set(c.languages) <= set(SUPPORTED_LANGUAGES), c.code
    assert COUNTRIES["ET"].languages[0] == "am" and "om" in COUNTRIES["ET"].languages
    assert COUNTRIES["SO"].languages[0] == "so" and COUNTRIES["MZ"].languages[0] == "pt"
    assert all(COUNTRIES[c].languages[0] == "ar" for c in ("EG", "LY", "SD"))


def test_34_countries_resolve_from_dialling_codes():
    assert len(COUNTRIES) == 34
    assert country_for_msisdn("+251911234567").code == "ET"
    assert country_for_msisdn("+245955123456").code == "GW"
    assert country_for_msisdn("+218912345678").code == "LY"


# The alphabet a reply travels in.

def test_latin_text_is_folded_into_gsm7():
    assert gsm_fold("Você está grávida? «Ligue já»") == 'Voce esta gravida? "Ligue ja"'
    assert gsm_fold("été, où, à") == "été, où, à"  # letters GSM-7 has stay
    assert is_gsm7(gsm_fold("Ça coûte 1 500 francs, côté marché"))


def test_other_scripts_are_left_alone():
    assert gsm_fold("ድንገተኛ") == "ድንገተኛ" and gsm_fold("طوارئ") == "طوارئ"
    assert not is_gsm7("طوارئ")


def test_budgets_shrink_for_ucs2_languages():
    assert ussd_limit("ar") == 80 and ussd_limit("am") == 80 and ussd_limit("so") == 182
    assert sms_limit("am", 1) == 70 and sms_limit("pt", 1) == 160
    assert scale(182, "ussd", "ar") == 80 and scale(182, "ussd", "om") == 182 and scale(500, "api", "ar") == 500


def test_amharic_ussd_reply_fits_one_screen():
    engine = Engine.from_packs(ROOT / "context_packs")
    reply = engine.ask("ባለቤቴ እርጉዝ ናት ብዙ ደም እየፈሰሳት ነው", sender="+251911234567", channel=Channel.USSD)
    assert reply.kind is ReplyKind.EMERGENCY and reply.language == "am"
    assert len(reply.text) <= 80 + 4


def test_portuguese_sms_reply_is_gsm7():
    engine = Engine.from_packs(ROOT / "context_packs")
    reply = engine.ask("A minha mulher está grávida e está a sangrar muito", sender="+258841234567", channel=Channel.SMS)
    assert reply.kind is ReplyKind.EMERGENCY and reply.language == "pt" and is_gsm7(reply.text)
    assert "112" in reply.text


# Reading text in five more languages.

def test_arabic_is_normalised_and_clitics_stripped():
    assert fold("أنا حامل") == fold("انا حامل")
    assert "حامل" in tokens("والحامل") and "ولاده" in tokens("الولادة")


def test_ethiopic_variants_fold_together():
    assert fold("ሐኪም") == fold("ሀኪም") and fold("ፀሐይ") == fold("ጸሀይ")


def test_script_decides_the_language():
    assert script_language("زوجتي حامل") == "ar" and script_language("እርጉዝ ናት") == "am"
    assert script_language("my wife is pregnant") is None
    assert guess_language("ባለቤቴ እርጉዝ ናት") == "am"


@pytest.mark.parametrize("text,lang", [("Estou grávida e o bebé não mexe", "pt"), ("Haadha manaa koo ulfa qabdi", "om"),
                                       ("Xaaskeyga waa uur leedahay", "so")])
def test_latin_script_languages_are_recognised(text, lang):
    assert guess_language(text) == lang


@pytest.mark.parametrize("word,code", [("portugues", "pt"), ("arabic", "ar"), ("amharic", "am"), ("oromo", "om"),
                                       ("somali", "so"), ("العربية", "ar"), ("አማርኛ", "am")])
def test_language_commands(word, code):
    assert language_code(word) == code


def test_ussd_menu_offers_the_callers_languages_first():
    for code, country in COUNTRIES.items():
        options = language_options(code)
        assert options[:len(country.languages)] == list(country.languages)[:4] and len(options) <= 4, code
        assert "en" in options or len(country.languages) >= 4, code
    assert language_options("ET") == ["am", "om", "so", "en"]
    assert language_options(None) == ["en", "fr", "sw", "pt"]


def test_ussd_language_menu_uses_native_names():
    engine = Engine.from_packs(ROOT / "context_packs")
    app, phone = UssdApp(engine), "+251911234567"
    pages = app._pages("am", phone)
    index = next(i for i, page in enumerate(pages) if any(k == "lang" for _, k, _ in page))
    option = next(n for n, k, _ in pages[index] if k == "lang")
    screen = app.respond(phone, "*".join(["98"] * index + [str(option)]))
    assert "1 አማርኛ" in screen and "2 Afaan Oromoo" in screen and "3 Soomaali" in screen


# Data problems ACE designs around.

@dataclass
class Place:
    country: str
    code: str
    name: str
    point: tuple[float, float]


class Places:
    def __init__(self, box, named):
        self.box, self.named = box, named

    def country_box(self, country):
        return self.box

    def named_in(self, text, country):
        return self.named


BOX = (0.0, 0.0, 10.0, 10.0)
WHOLE = [[0.1, 0.1], [0.1, 9.9], [9.9, 9.9], [9.9, 0.1], [0.1, 0.1]]
SMALL = [[1.0, 1.0], [1.0, 2.0], [2.0, 2.0], [2.0, 1.0], [1.0, 1.0]]


def test_a_country_wide_outline_with_named_areas_matches_by_name():
    north, south = Place("XX", "N", "North", (8.0, 8.0)), Place("XX", "S", "South", (1.5, 1.5))
    alert = {"polygons": [WHOLE], "area_desc": ["North"], "headline": "Heavy rain"}
    places = Places(BOX, {"N"})
    assert warnings.scope(alert, north, places) == "named"
    assert warnings.scope(alert, south, places) is None


def test_a_small_polygon_still_decides():
    inside, outside = Place("XX", "A", "Alpha", (1.5, 1.5)), Place("XX", "B", "Beta", (5.0, 5.0))
    alert = {"polygons": [SMALL], "area_desc": ["Alpha"]}
    assert warnings.scope(alert, inside, Places(BOX, set())) == "polygon"
    assert warnings.scope(alert, outside, Places(BOX, set())) is None


def test_a_country_wide_outline_without_names_is_national():
    alert = {"polygons": [WHOLE], "area_desc": []}
    assert warnings.scope(alert, Place("XX", "A", "Alpha", (5.0, 5.0)), Places(BOX, set())) == "national"


def test_degenerate_polygons_are_dropped():
    point = [[1.0, 1.0]] * 5
    line = [[1.0, 1.0], [2.0, 2.0], [1.0, 1.0], [2.0, 2.0]]
    assert warnings.clean_rings([point, line, SMALL]) == [SMALL]


def test_a_thin_price_list_is_a_stated_gap():
    today = date(2026, 11, 24)
    one = [{"items": [{"commodity": "Maize (white)", "series": [["2026-10", 300]]}]}]
    two = [{"items": [{"commodity": "Maize (white)", "series": [["2026-10", 300]]},
                      {"commodity": "Beans (dry)", "series": [["2026-10", 900]]}]}]
    old = [{"items": [{"commodity": "Rice", "series": [["2021-01", 300]]}, {"commodity": "Beans", "series": [["2021-01", 3]]}]}]
    assert prices.staple_count(one, today) == 1 < prices.MIN_STAPLES
    assert prices.staple_count(two, today) == 2 >= prices.MIN_STAPLES
    assert prices.staple_count(old, today) == 0


def test_facility_positions_far_from_their_country_are_dropped():
    from ace_engine.connectors.health_facilities import check_positions
    from ace_engine.snapshots import SnapshotStore
    store = SnapshotStore(ROOT / "snapshots")
    records = [["Good clinic", "Health Centre", "Public", "Lilongwe", -13.98, 33.78],
               ["Null island", "Health Centre", "Public", "Lilongwe", 0.0, 0.0]]
    kept, dropped = check_positions(records, "MW", store)
    assert [r[0] for r in kept] == ["Good clinic"] and dropped and "Null island" in dropped[0]


def test_north_africa_has_no_facility_list_and_says_so():
    engine = Engine.from_packs(ROOT / "context_packs", snapshots=ROOT / "snapshots")
    cover = engine.services.coverage()["nearest_facility"]
    for code in ("DZ", "EG", "LY", "MA", "TN"):
        assert not cover[code]["available"] and "sub-Saharan" in cover[code]["detail"], code


# National registries: a complete connector held until the licence is cleared.

def test_national_registries_are_held_until_cleared():
    assert "national_facility_registry" in held(ROOT / "snapshots")


def test_registry_rows_are_parsed_and_placeholder_phones_dropped():
    assert plausible_phone("+265 999 123 456") == "265999123456"
    assert plausible_phone("1234567890") is None and plausible_phone("0999") is None
    mw = malawi_records([{"id": 1, "facility_name": "Bwaila Hospital", "facility_type_id": 2, "facility_owner_id": 1,
                          "district_id": 18, "archived_date": None},
                         {"id": 2, "facility_name": "Facility Name", "district_id": 1}],
                        [{"facility_id": 1, "latitude": "-13.98", "longitude": "33.78"}, {"facility_id": 2, "latitude": "1",
                                                                                          "longitude": "1"}],
                        [{"facility_id": 1, "contact_person_phone": "0999 111 222"}])
    assert mw == [["Bwaila Hospital", "2", "1", "18", -13.98, 33.78, "0999111222"]]
    zm = zambia_records([{"name": "Chipata Clinic", "facility_type": "Health Centre", "ownership": "GRZ",
                          "province": "Lusaka", "latitude": "-15.37", "longitude": "28.27", "phone": "1234",
                          "operation_status": "Operational"},
                         {"name": "Closed", "latitude": "1", "longitude": "1", "operation_status": "Closed"}])
    assert zm == [["Chipata Clinic", "Health Centre", "GRZ", "Lusaka", -15.37, 28.27, None]]


def test_a_registry_phone_number_is_shown_with_the_facility():
    row = ["Bwaila Hospital", "District Hospital", "Government", "Lilongwe", -13.98, 33.78, "0999111222"]
    assert facility.label(row, 2.4, "en") == "Bwaila Hospital (district hospital, 2 km, 0999111222)"
    assert facility.label(row[:6] + [None], None, "en") == "Bwaila Hospital (district hospital)"


# The added languages reach every part of the product.

@pytest.mark.parametrize("phone,text,queue", [
    ("+251911234567", "ባለቤቴ እርጉዝ ናት እና ብዙ ደም እየፈሰሳት ነው", "maternal"),
    ("+249912345678", "زوجتي حامل وعندها نزيف شديد", "maternal"),
    ("+252615123456", "Waxaan rabaa inaan is dilo", "self_harm"),
    ("+251911234567", "Abbaan manaa koo guyyaa guyyaan na reeba", "gbv"),
    ("+244923123456", "O meu pai desmaiou e não respira", "health_urgent"),
])
def test_the_safety_rail_works_in_every_added_language(phone, text, queue):
    engine = Engine.from_packs(ROOT / "context_packs")
    reply = engine.ask(text, sender=phone, channel=Channel.SMS)
    assert reply.kind is ReplyKind.EMERGENCY and reply.escalation_queue == queue


@pytest.mark.parametrize("code", ADDED)
def test_africa_packs_carry_every_added_language(code):
    from ace_engine.context import load_packs
    for pack in load_packs(ROOT / "context_packs"):
        if pack.id.startswith("africa-"):
            assert all(code in f.translations and not f.translations[code].reviewed for f in pack.facts), pack.id
            assert pack.labels.get(code), pack.id


@pytest.mark.parametrize("code", ADDED)
def test_services_answer_in_every_added_language(code):
    engine = Engine.from_packs(ROOT / "context_packs", snapshots=ROOT / "snapshots")
    reply = engine.run_service("pregnancy_companion", Message(channel=Channel.API, sender="+251911234567", text="24",
                                                              language=code), Budget(max_chars=500, short=False))
    assert reply.kind is ReplyKind.ANSWER and reply.language == code and reply.citations
