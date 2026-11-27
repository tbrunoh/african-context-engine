"""Release 2.3: 24 more languages, each served in the countries that speak it, read by marker words within the
caller's country, folded into GSM-7 where they use Latin letters, and present in every Africa pack."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ace_engine import i18n
from ace_engine.channels.ussd import language_options
from ace_engine.commands import COMMANDS
from ace_engine.countries import COUNTRIES
from ace_engine.encoding import gsm_fold, is_gsm7
from ace_engine.text import fold, guess_language

ROOT = Path(__file__).resolve().parents[1]
ADDED_23 = ("af", "ak", "bem", "dyu", "ee", "fuf", "ha", "ig", "lg", "ln", "mos", "ny", "pcm", "rn", "rw", "sn", "st",
            "ti", "tn", "ts", "wo", "xh", "yo", "zu")
SERVED = {
    "NG": ("en", "ha", "yo", "ig", "pcm"), "ZA": ("en", "zu", "xh", "af", "st", "tn", "ts"), "BW": ("en", "tn"),
    "NA": ("en", "af"), "ZW": ("en", "sn"), "GH": ("en", "ak", "ee"), "SN": ("fr", "wo"), "CI": ("fr", "dyu"),
    "TG": ("fr", "ee"), "MW": ("en", "ny"), "ZM": ("en", "bem", "ny"), "BJ": ("fr", "yo"), "GN": ("fr", "fuf"),
    "BF": ("fr", "mos", "dyu"), "MZ": ("pt", "ts"), "RW": ("en", "fr", "rw"), "BI": ("fr", "sw", "rn"),
    "UG": ("en", "sw", "lg"), "CD": ("fr", "sw", "ln"), "ET": ("am", "om", "so", "en", "ti"),
}


def test_each_added_language_is_served_where_it_is_spoken():
    for code, langs in SERVED.items():
        assert COUNTRIES[code].languages == langs, code
    served = {lang for c in COUNTRIES.values() for lang in c.languages}
    assert set(ADDED_23) <= served


def test_added_languages_are_complete_and_unreviewed():
    assert all(not i18n.missing()[code] for code in ADDED_23)
    assert set(ADDED_23) <= set(i18n.unreviewed())


@pytest.mark.parametrize("pack", sorted((ROOT / "context_packs" / "africa").glob("*.yaml")), ids=lambda p: p.stem)
def test_every_africa_fact_has_each_added_language_within_one_sms(pack):
    data = yaml.safe_load(pack.read_text(encoding="utf-8"))
    for code in ADDED_23:
        assert data["labels"].get(code), (pack.stem, code)
    for fact in data["facts"]:
        for code in ADDED_23:
            t = fact["translations"][code]
            assert t["claim"] and t["short"] and t["reviewed"] is False, (fact["id"], code)
            assert len(t["short"]) <= 160, (fact["id"], code, len(t["short"]))


def test_no_command_word_means_two_things():
    owner: dict[str, str] = {}
    for name, words in COMMANDS.items():
        for word in words:
            assert owner.setdefault(fold(word), name) == name, (word, owner[fold(word)], name)


def test_detection_chooses_among_the_callers_country_languages():
    nigeria, south_africa = COUNTRIES["NG"].languages, COUNTRIES["ZA"].languages
    assert guess_language("my cassava leaf dey yellow", "en", nigeria) == "pcm"
    assert guess_language("Where is the nearest hospital", "en", nigeria) == "en"
    assert guess_language("Ek is 20 weke swanger", "en", south_africa) == "af"
    assert guess_language("my maize leaves are yellow", "en", south_africa) == "en"
    assert guess_language("Ngikhulelwe amasonto angu-20", "en", south_africa) == "zu"
    assert guess_language("Mvua itanyesha wiki hii?", "fr", COUNTRIES["CD"].languages) == "sw"


def test_a_tie_between_close_languages_goes_to_the_one_the_country_lists_first():
    """Sesotho and Setswana share words such as dinawa and bokae. A tie goes to the country's first listed of the
    two, which its speakers read, never to English, which neither wrote in."""
    assert guess_language("dinawa ke bokae", "en", COUNTRIES["ZA"].languages) == "st"
    assert guess_language("dinawa ke bokae", "en", COUNTRIES["BW"].languages) == "tn"


def test_geez_script_is_read_as_amharic_or_tigrinya_by_marker_words():
    ethiopia = COUNTRIES["ET"].languages
    assert guess_language("እርጉዝ ነኝ ደም እየፈሰሰኝ ነው", "am", ethiopia) == "am"
    assert guess_language("ጥንሲ ኣለኒ ደም ይፈሳ ኣሎ", "am", ethiopia) == "ti"


def test_african_latin_letters_fold_into_gsm7():
    text = gsm_fold("Ɓiɗɗo ŋatii ɛ ɔ ɣ ƒ ʋ ẹ ṣ ọ sõngre ɲ")
    assert is_gsm7(text) and text == "Biddo ngatii e o g f v e s o songre ny"


def test_the_ussd_menu_still_fits_one_screen():
    for code in COUNTRIES:
        assert len(language_options(code)) <= 4
    assert language_options("ZA") == ["en", "zu", "xh", "af"]


def test_the_safety_rail_reads_a_message_once_and_matches_as_before():
    """With 32 languages the rail holds thousands of phrases. It folds and tokenises the message once, and
    phrase_in on that must agree with contains_phrase on every phrase."""
    from ace_engine.safety import DEFAULT_RULES
    from ace_engine.text import contains_phrase, phrase_in, token_hay
    for text in ("My wife is pregnant and bleeding a lot", "Mo loyun oṣu meje ọmọ inu ko mira mọ",
                 "Ọmọ mi ti mu kẹrosini", "ጥንሲ ኣለኒ ደም ይፈሳ ኣሎ", "how much is maize in Kano"):
        hay = token_hay(text)
        for groups in DEFAULT_RULES.values():
            for group in groups:
                for phrase in group:
                    assert phrase_in(hay, phrase) == contains_phrase(text, phrase), (text, phrase)


# Fixes from the independent review of 2.3.0b1 ------------------------------------------------------------------

from ace_engine import Engine  # noqa: E402
from ace_engine.commands import language_menu, parse_command  # noqa: E402
from ace_engine.engine import CHANNEL_BUDGETS  # noqa: E402
from ace_engine.models import Channel, Message  # noqa: E402
from ace_engine.safety import EscalationPolicy, alarm_language  # noqa: E402
from ace_engine.text import _MARKERS, STOPWORDS, tokens  # noqa: E402

ORDINARY = [  # everyday messages that once raised a false alarm through a word of an added language
    "Je suis enceinte, j'ai vu la sage-femme",
    "Je suis enceinte, j'achete un joli pagne",
    "N kɔnɔma don, kɔnɔ lajɛli joli bɛ yen?",
    "Umwana yanyoye imiti ya malaria",
    "Amina alinunua dawa ya wadudu",
    "Can my cows drink water after I spray chemical",
    "Njëg gi dafa daanu",
    "Daku ni saa ngapi leo",
    "Mme Jallo est enceinte",
    "Ngiyazi ukuthi akazi lutho ngemvula",
]


@pytest.mark.parametrize("text", ORDINARY)
def test_everyday_words_of_added_languages_raise_no_alarm(text):
    assert not EscalationPolicy().check(text).escalate


def test_dyula_safety_openers_do_not_say_it_pleases_me():
    loc = i18n.locales()["dyu"]
    for queue in ("self_harm", "gbv"):
        assert not loc.templates[f"safety.OPENERS.{queue}"].startswith("A ka di")


def test_marker_words_are_whole_words_that_no_neighbour_shares():
    common = set().union(*({fold(w) for w in STOPWORDS.get(k, ())} for k in ("en", "fr", "pt")))
    for code in ADDED_23:
        for word in i18n.words("markers").get(code, ()):
            assert len(tokens(word)) == 1, (code, word)
        assert not _MARKERS[code] & common, code
    for country in COUNTRIES.values():
        for a in country.languages:
            for b in country.languages:
                if a == b or a not in ADDED_23 or {a, b} == {"st", "tn"}:
                    continue  # Sesotho and Setswana share words on purpose; the country order settles a tie
                theirs = _MARKERS.get(b, frozenset()) | {fold(w) for w in STOPWORDS.get(b, ())}
                assert not _MARKERS[a] & theirs, (country.code, a, b, sorted(_MARKERS[a] & theirs))


@pytest.mark.parametrize("text,country,expected", [
    ("Il a de la fièvre", "CI", "fr"), ("Ma femme a mal à la tête", "BF", "fr"),
    ("tell me rain tomorrow", "ZA", "en"), ("Quel temps demain svp", "CD", "fr"), ("Tu as vu la pluie ?", "TG", "fr"),
    ("My wife is pregnant and she is bleeding a lot", "SN", "en"),
])
def test_neighbour_markers_no_longer_take_french_or_english(text, country, expected):
    langs = COUNTRIES[country].languages
    assert guess_language(text, langs[0], langs) == expected


def test_every_gsm7_text_stays_gsm7_after_folding():
    for code in ADDED_23:
        loc = i18n.locales()[code]
        if loc.meta.get("encoding") != "gsm7":
            continue
        for key, value in loc.templates.items():
            for text in (value.values() if isinstance(value, dict) else [value]):
                assert is_gsm7(gsm_fold(str(text))), (code, key)
    assert gsm_fold("Ð") == "D"
    for path in (ROOT / "context_packs" / "africa").glob("*.yaml"):
        for fact in yaml.safe_load(path.read_text(encoding="utf-8"))["facts"]:
            for code, t in (fact.get("translations") or {}).items():
                if code in ADDED_23 and i18n.locales()[code].meta.get("encoding") == "gsm7":
                    for part in ("claim", "short"):
                        assert is_gsm7(gsm_fold(t.get(part) or "")), (path.name, fact["id"], code)


@pytest.mark.parametrize("text", ["Ulimi lwami luyabuhlungu", "Kan ek mielies plant?", "Bem", "Amagezi ku muwogo?",
                                  "Olulimi lwange lunnuma"])
def test_command_words_do_not_take_ordinary_messages(text):
    assert parse_command(text) is None


def test_language_command_still_works_bare_or_with_a_language():
    assert parse_command("LANG").name == "language"
    assert parse_command("LANG HA").name == "hausa"
    assert parse_command("Ururimi").name == "language"


def test_the_language_menu_lists_the_callers_country_languages():
    menu = language_menu(COUNTRIES["NG"].languages)
    assert menu.split(", ")[0] == "EN English" and len(menu.split(", ")) == 5
    assert len(language_menu().split(", ")) == len(i18n.all_languages())


def test_an_emergency_gets_the_language_its_safety_phrase_came_from():
    za = COUNTRIES["ZA"].languages
    assert alarm_language("Ngikhulelwe igazi liyaphuma", "en", za) == "zu"
    assert alarm_language("My wife is pregnant and bleeding", "en", za) == "en"
    reply = Engine.from_packs(ROOT / "context_packs").handle(Message(Channel.SMS, "+27820000000", "Ngikhulelwe igazi liyaphuma"))
    assert reply.escalated and reply.language == "zu"


def test_sms_budget_applies_after_folding():
    engine = Engine.from_packs(ROOT / "context_packs")
    for text in ("Bli ƒe ŋɔ ƒe dzesiwo", "Kpɔ ɣesiaɣi agble la me"):
        reply = engine.handle(Message(Channel.SMS, "+22890000000", text, language="ee"))
        assert len(reply.text) <= CHANNEL_BUDGETS[Channel.SMS].max_chars and is_gsm7(reply.text)


def test_rate_limit_waits_are_capped_for_the_whole_run(monkeypatch):
    import io
    import urllib.error

    from ace_engine.connectors import base

    def limited(*_a, **_k):
        raise urllib.error.HTTPError("https://example.org", 429, "Too Many Requests", {"Retry-After": "100"},
                                     io.BytesIO())

    slept: list[float] = []
    monkeypatch.setattr(base.urllib.request, "urlopen", limited)
    monkeypatch.setattr(base.time, "sleep", slept.append)
    monkeypatch.setattr(base, "_rate_waited", 0.0)
    for _ in range(5):
        with pytest.raises(base.ConnectorError):
            base.http_get("https://example.org")
    assert sum(slept) <= base.RATE_LIMIT_BUDGET
