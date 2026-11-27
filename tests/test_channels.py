from __future__ import annotations

import hashlib
import hmac
import itertools
import xml.etree.ElementTree as ET

from ace_engine.channels import (
    SmsAdapter,
    UssdAdapter,
    UssdApp,
    VoiceApp,
    WhatsAppAdapter,
    is_gsm7,
    segment,
    send_payload,
    to_gsm7,
    verify_signature,
    verify_subscription,
)
from ace_engine.models import Citation, Reply

# ---------------------------------------------------------------- SMS

def test_gsm7_segmentation():
    assert segment("short") == ["short"]
    parts = segment("word " * 80)
    assert len(parts) == 3 and all(len(p) <= 153 for p in parts)


def test_ucs2_segmentation():
    text = "maji " * 30 + "م"  # one Arabic letter forces UCS-2
    assert not is_gsm7(text)
    assert all(len(p) <= 67 for p in segment(text))


def test_typographic_characters_are_replaced():
    assert is_gsm7(to_gsm7("Don’t “share” – ever…"))


def test_sms_parse_and_render_africas_talking():
    msg = SmsAdapter().parse_inbound({"from": "+254711000000", "to": "21606", "text": " hello ", "linkId": "L1"})
    assert msg.text == "hello" and msg.session_id == "L1"
    parts = SmsAdapter(max_segments=2).render(Reply(text="word " * 200))
    assert len(parts) == 2 and parts[-1].endswith("...")


# ---------------------------------------------------------------- USSD

def test_ussd_adapter():
    msg = UssdAdapter().parse_inbound({"sessionId": "s", "serviceCode": "*384#", "phoneNumber": "0711000000",
                                       "text": "1*2"})
    assert msg.text == "2" and msg.raw["inputs"] == ["1", "2"]
    assert UssdAdapter().render(Reply(text="bye", end_session=True)) == ["END bye"]


def test_ussd_main_menu(engine):
    screen = UssdApp(engine).respond("+254711000001", "")
    assert screen.startswith("CON ACE\n1 Rain this week")
    assert "7 Topics" in screen and "Ask a question" in screen and len(screen) <= 182


def test_ussd_browse_a_pack(engine):
    app = UssdApp(engine)
    first = app.respond("+254711000002", "7*1")
    second = app.respond("+254711000002", "7*1*1")
    assert first != second and "1 Next" in first and "0 Back" in first
    assert app.respond("+254711000002", "7*1*1*0").startswith("CON ACE")


def test_ussd_ask_and_scam(engine):
    app = UssdApp(engine)
    answer = app.respond("+254711000003", "8*how do I store maize")
    assert "13" in answer and answer.endswith("0 Menu")
    verdict = app.respond("+254711000003", "9*Send your M-PESA PIN now")
    assert "LIKELY SCAM" in verdict


def test_ussd_emergency_ends_the_session(engine):
    assert UssdApp(engine).respond("+254711000004", "8*mtoto amekunywa sumu").startswith("END ")


def test_ussd_language_switch(engine):
    app = UssdApp(engine)
    screen = app.respond("+254711000005", "98*10*2")
    assert "Mvua wiki hii" in screen and "Uliza swali" in screen
    assert "Viwavijeshi" in app.respond("+254711000005", "98*10*2*7")


def test_ussd_invalid_choice(engine):
    assert UssdApp(engine).respond("+254711000006", "77").startswith("CON Invalid choice.")


def test_every_ussd_screen_fits(engine):
    """Walk every short path through the menu in both languages; no screen may exceed 182 characters."""
    app = UssdApp(engine)
    tokens = ["1", "2", "3", "4", "5", "6", "0", "98", "00"]
    for lang_prefix in ([], ["98", "10", "2"]):
        for depth in (1, 2, 3):
            for combo in itertools.product(tokens, repeat=depth):
                screen = app.respond("+254711000007", "*".join([*lang_prefix, *combo]))
                assert screen.startswith(("CON ", "END ")) and len(screen) <= 182, (combo, len(screen), screen)


# ---------------------------------------------------------------- Voice

def test_voice_menu_and_topic_are_valid_xml(engine):
    app = VoiceApp(engine)
    menu = app.respond({"callerNumber": "+254711000008", "isActive": "1"})
    root = ET.fromstring(menu)
    assert root.tag == "Response" and root.find("GetDigits/Say").text.startswith("Welcome to ACE.")
    topic = ET.fromstring(app.respond({"callerNumber": "+254711000008", "isActive": "1", "dtmfDigits": "4"}))
    assert "0722000000" in topic.find("Say").text


def test_voice_end_of_call_and_invalid_digit(engine):
    app = VoiceApp(engine)
    assert app.respond({"isActive": "0"}) == ""
    xml = app.respond({"callerNumber": "+254711000009", "isActive": "1", "dtmfDigits": "9"})
    assert "not a valid choice" in xml


# ---------------------------------------------------------------- WhatsApp

def _wa(message):
    return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}


def test_whatsapp_parse_text_location_and_buttons():
    wa = WhatsAppAdapter()
    assert wa.parse_inbound(_wa({"from": "254711000000", "type": "text", "text": {"body": "hi"}})).text == "hi"
    loc = wa.parse_inbound(_wa({"from": "254711000000", "type": "location",
                                "location": {"latitude": -1.2, "longitude": 36.8}}))
    assert loc.location.lat == -1.2
    btn = wa.parse_inbound(_wa({"from": "254711000000", "type": "interactive",
                                "interactive": {"button_reply": {"title": "More"}}}))
    assert btn.text == "More"


def test_whatsapp_render_lists_sources_once():
    reply = Reply(text="Answer.", citations=[Citation("a", "KALRO", "sourced"), Citation("b", "KALRO", "sourced")])
    assert WhatsAppAdapter().render(reply) == ["Answer.\n\nSources: KALRO"]


def test_whatsapp_verification_and_signature():
    assert verify_subscription("subscribe", "tok", "123", "tok") == "123"
    assert verify_subscription("subscribe", "bad", "123", "tok") is None
    body = b'{"a":1}'
    sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, "secret")
    assert not verify_signature(body, sig, "other")
    assert send_payload("+254711000000", "hi")["to"] == "254711000000"
