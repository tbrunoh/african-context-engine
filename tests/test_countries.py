"""One engine, 34 countries: the caller's number picks the numbers, packs and language."""
from __future__ import annotations

import pytest

from ace_engine.channels.ussd import UssdApp
from ace_engine.countries import COUNTRIES, country_for_msisdn, default_language
from ace_engine.encoding import is_gsm7
from ace_engine.engine import Engine, EngineConfig
from ace_engine.models import Channel, ReplyKind

# A plausible mobile number for each covered country.
PHONES = {
    "KE": "+254712345678", "TZ": "+255712345678", "UG": "+256772345678", "RW": "+250788123456",
    "ZA": "+27821234567", "BW": "+26771234567", "NA": "+264811234567", "ZW": "+263771234567",
    "NG": "+2348031234567", "GH": "+233241234567", "SN": "+221771234567", "CI": "+2250701234567",
    "TG": "+22890123456", "CD": "+243812345678", "MW": "+265991234567", "BI": "+25779123456",
    "CM": "+237671234567", "BJ": "+2290197123456", "ZM": "+260971234567", "TD": "+23566123456",
    "GN": "+224621234567", "BF": "+22670123456", "SS": "+211921234567", "ET": "+251911234567",
    "MZ": "+258841234567", "GW": "+245955123456", "AO": "+244923123456", "SO": "+252615123456",
    "SD": "+249912345678", "DZ": "+213551234567", "EG": "+201001234567", "LY": "+218912345678",
    "MA": "+212612345678", "TN": "+21620123456",
}

# What a caller in each country must be told for a medical emergency, from the audited packs.
MEDICAL = {
    "KE": ["999", "112"], "TZ": ["112"], "UG": ["999", "112"], "RW": ["112", "912"], "ZA": ["112", "10177"],
    "BW": ["997"], "NA": ["112"], "ZW": ["999", "112"], "NG": ["112"], "GH": ["112", "193"],
    "SN": ["15", "1515"], "CI": ["185"], "MW": ["998"], "BI": ["112"], "CM": ["112"], "BJ": ["118"],
    "ZM": ["992"], "TD": ["112", "18"], "BF": ["18"], "ET": ["911"], "MZ": ["112"], "GW": ["1313"], "AO": ["112"],
    "SO": ["446", "999"], "SD": ["999"], "DZ": ["1021"], "EG": ["123"], "LY": ["1415"], "MA": ["150"], "TN": ["190"],
}
# Countries the FCDO says have no national emergency medical number: ACE says so and sends people to a facility.
NO_NATIONAL = ("CD", "GN", "SS", "TG")
# Numbers for violence against a woman.
GBV = {
    "KE": ["1195"], "ZA": ["0800 428 428", "10111"], "NA": ["106"], "GH": ["0800 111 222"], "RW": ["3512"],
    "UG": ["0800 199 195"], "CI": ["1308", "170"], "BW": ["999"], "SN": ["17"], "TG": ["117"],
}
# Child helplines.
CHILD = {"KE": "116", "ZA": "116", "BW": "11611", "NA": "116", "ZW": "116", "NG": "0800 800 8001",
         "RW": "116", "TZ": "116", "UG": "116", "SN": "116", "CI": "116", "TG": "1011"}


def test_every_country_resolves_from_its_dialling_code():
    assert set(PHONES) == set(COUNTRIES)
    for cc, phone in PHONES.items():
        assert country_for_msisdn(phone).code == cc
    assert country_for_msisdn("+14155550100") is None


def test_default_languages():
    assert default_language("SN") == "fr" and default_language("TZ") == "sw" and default_language("ZA") == "en"
    assert default_language(None) == "en" and default_language("US", "sw") == "sw"


@pytest.mark.parametrize("cc", sorted(MEDICAL))
def test_medical_emergency_gives_that_countrys_numbers(engine, cc):
    reply = engine.ask("He collapsed and is not breathing", sender=PHONES[cc], channel=Channel.SMS, language="en")
    assert reply.kind is ReplyKind.EMERGENCY
    for number in MEDICAL[cc]:
        assert number in reply.text, (cc, reply.text)
    assert all(c.fact_id.startswith(f"{cc.lower()}-emergency-contacts/") for c in reply.citations), cc


@pytest.mark.parametrize("cc", NO_NATIONAL)
def test_no_national_medical_number_sends_people_to_a_facility(engine, cc):
    reply = engine.ask("He collapsed and is not breathing", sender=PHONES[cc], channel=Channel.SMS, language="en")
    assert reply.kind is ReplyKind.EMERGENCY
    assert "health facility" in reply.text and "112" not in reply.text.replace("112 (police", ""), (cc, reply.text)


def test_no_number_is_ever_borrowed_from_another_country(engine):
    reply = engine.ask("He collapsed and is not breathing", sender=PHONES["NG"], channel=Channel.SMS)
    assert "999" not in reply.text and "1199" not in reply.text


def test_country_without_a_sourced_ambulance_number_gets_honest_fallback(engine):
    reply = engine.ask("Il ne respire plus", sender=PHONES["TG"], channel=Channel.SMS)
    assert reply.kind is ReplyKind.EMERGENCY and reply.language == "fr"
    assert "numéro d'urgence local" in reply.text and "centre de santé" in reply.text


@pytest.mark.parametrize("cc", sorted(GBV))
def test_violence_gives_that_countrys_lines(engine, cc):
    reply = engine.ask("my husband beats me", sender=PHONES[cc], channel=Channel.SMS, language="en")
    for number in GBV[cc]:
        assert number in reply.text, (cc, reply.text)


@pytest.mark.parametrize("cc", sorted(CHILD))
def test_child_protection_gives_that_countrys_helpline(engine, cc):
    reply = engine.ask("my daughter was defiled", sender=PHONES[cc], channel=Channel.SMS, language="en")
    assert CHILD[cc] in reply.text, (cc, reply.text)


def test_french_emergency_in_senegal(engine):
    reply = engine.ask("Je suis enceinte et je saigne beaucoup", sender=PHONES["SN"], channel=Channel.SMS)
    assert reply.language == "fr" and reply.escalation_queue == "maternal"
    # SMS replies are folded to the GSM-7 alphabet (ê becomes e) so a French message keeps 160 characters a segment.
    assert reply.text.startswith("Cela peut etre une urgence de grossesse") and is_gsm7(reply.text)
    assert "Appelez le" in reply.text and "15" in reply.text and "1515" in reply.text


def test_french_speaker_in_an_english_country_is_answered_in_french(engine):
    reply = engine.ask("mon mari me bat", sender=PHONES["RW"], channel=Channel.SMS)
    assert reply.language == "fr" and "3512" in reply.text


def test_continental_maternal_facts_carry_the_callers_numbers(engine):
    """WHO guidance applies everywhere; the numbers beside it must be the caller's own."""
    gh = engine.ask("danger signs in pregnancy", sender=PHONES["GH"], channel=Channel.WHATSAPP)
    ke = engine.ask("danger signs in pregnancy", sender=PHONES["KE"], channel=Channel.WHATSAPP)
    assert gh.kind is ReplyKind.ANSWER and ke.kind is ReplyKind.ANSWER
    assert any(c.fact_id.startswith("africa-maternal-danger-signs/") for c in gh.citations)
    assert "112" in gh.text and "193" in gh.text and "999" not in gh.text
    assert "999" in ke.text and "193" not in ke.text


def test_french_farmer_in_cote_divoire_gets_armyworm_guidance(engine):
    reply = engine.ask("Comment lutter contre la chenille légionnaire dans mon maïs ?", sender=PHONES["CI"],
                       channel=Channel.SMS)
    assert reply.kind is ReplyKind.ANSWER and reply.language == "fr"
    assert any(c.fact_id.startswith("africa-maize-fall-armyworm/") for c in reply.citations)
    assert not any(c.fact_id.endswith("/push-pull") for c in reply.citations)


def test_kenya_only_packs_are_not_offered_elsewhere(engine):
    reply = engine.ask("how do I store maize to avoid aflatoxin", sender=PHONES["NG"], channel=Channel.SMS)
    assert not any(c.fact_id.startswith("ke-") for c in reply.citations)
    labels = engine.topic_labels("en", "NG")
    assert "Emergency numbers" in labels and not any("M-PESA" in label for label in labels)


def test_scam_shield_never_cites_safaricom_outside_kenya(engine):
    text = "Your SIM is registered twice. Send your PIN to 0712000111 to avoid being blocked."
    ng = engine.ask(text, sender=PHONES["NG"], channel=Channel.SMS)
    ke = engine.ask(text, sender=PHONES["KE"], channel=Channel.SMS)
    assert ng.kind is ReplyKind.SCAM and ke.kind is ReplyKind.SCAM
    assert not any(c.fact_id.startswith("ke-") for c in ng.citations)
    assert "333" not in ng.text and "provider" in ng.text
    assert "333" in ke.text


def test_french_scam_message_is_caught(engine):
    reply = engine.ask("Félicitations, vous avez gagné 500 000 FCFA. Envoyez votre code secret pour recevoir "
                       "votre cadeau.", sender=PHONES["SN"], channel=Channel.SMS)
    assert reply.kind is ReplyKind.SCAM and reply.text.startswith("ARNAQUE PROBABLE")


def test_ussd_menu_is_local_and_in_french_in_togo(engine):
    app = UssdApp(engine)
    screen = app.respond(PHONES["TG"], "")
    assert screen.startswith("CON ") and "Pluie cette semaine" in screen
    assert "Poser une question" in app.respond(PHONES["TG"], "98")
    topics = app.respond(PHONES["TG"], "7")
    assert "Numéros d'urgence" in topics and "M-PESA" not in topics
    assert all(len(app.respond(PHONES[cc], "")) <= 182 for cc in PHONES)


def test_ussd_language_switch_to_french(engine):
    app = UssdApp(engine)
    pages = app._pages("en", PHONES["KE"])
    lang_option = next(n for page in pages for n, key, _ in page if key == "lang")
    more = "*".join(["98"] * next(i for i, page in enumerate(pages) if any(k == "lang" for _, k, _ in page)))
    path = f"{more}*{lang_option}*3" if more else f"{lang_option}*3"
    app.respond(PHONES["KE"], path)
    assert engine.profiles.peek(PHONES["KE"]).language == "fr"


def test_pinned_country_overrides_the_dialling_code(packs_dir):
    engine = Engine.from_packs(packs_dir, config=EngineConfig(country="KE"))
    reply = engine.ask("He collapsed and is not breathing", sender=PHONES["NG"], channel=Channel.SMS)
    assert "999" in reply.text


def test_lang_fr_command(engine):
    reply = engine.ask("LANG FR", sender=PHONES["KE"])
    assert reply.text == "ACE répondra en français."
    assert engine.ask("hello", sender=PHONES["KE"]).language == "fr"
