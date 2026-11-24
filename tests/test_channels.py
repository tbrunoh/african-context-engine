from ace_engine.channels import SmsAdapter, UssdAdapter, VoiceAdapter, WhatsAppAdapter, segment
from ace_engine.identity import normalize_msisdn
from ace_engine.models import Channel, Citation, Reply


def test_normalize_msisdn_formats():
    assert normalize_msisdn("0712345678") == "+254712345678"
    assert normalize_msisdn("254712345678") == "+254712345678"
    assert normalize_msisdn("+234 803 123 4567") == "+2348031234567"


def test_ussd_parse_takes_last_input_and_renders_within_limit():
    a = UssdAdapter()
    m = a.parse_inbound({"sessionId": "s", "serviceCode": "*384#", "phoneNumber": "+254712345678",
                         "text": "1*3*maize"})
    assert m.channel is Channel.USSD and m.text == "maize" and m.raw["inputs"] == ["1", "3", "maize"]
    out = a.render(Reply(text="word " * 100))[0]
    assert out.startswith("CON ") and len(out) <= 182
    assert a.render(Reply(text="Bye", end_session=True)) == ["END Bye"]


def test_sms_segmentation_gsm_and_unicode():
    assert len(segment("a" * 160)) == 1
    parts = segment(("hello " * 60).strip())
    assert len(parts) == 3 and all(len(p) <= 153 for p in parts)
    assert all(len(p) <= 67 for p in segment(("ሰላም " * 40).strip()))  # Amharic forces UCS-2


def test_sms_render_caps_segments():
    out = SmsAdapter(max_segments=2).render(Reply(text="word " * 200))
    assert len(out) == 2 and out[-1].endswith("...")


def test_whatsapp_parse_text_image_location():
    def wrap(msg):
        return {"entry": [{"changes": [{"value": {"messages": [msg]}}]}]}

    a = WhatsAppAdapter()
    t = a.parse_inbound(wrap({"from": "254712345678", "type": "text", "text": {"body": "hi"}}))
    assert t.sender == "+254712345678" and t.text == "hi"
    i = a.parse_inbound(wrap({"from": "254712345678", "type": "image",
                              "image": {"id": "MEDIA1", "mime_type": "image/jpeg", "caption": "leaf"}}))
    assert i.attachments[0].uri == "whatsapp-media:MEDIA1" and i.text == "leaf"
    loc = a.parse_inbound(wrap({"from": "254712345678", "type": "location",
                                "location": {"latitude": -0.42, "longitude": 36.95}}))
    assert loc.location.lat == -0.42


def test_whatsapp_render_appends_sources():
    out = WhatsAppAdapter().render(Reply(text="Answer", citations=[Citation("f1", "KALRO", "draft")]))
    assert out[0].endswith("Sources: KALRO")


def test_voice_render_splits_turns():
    turns = VoiceAdapter(max_sentences_per_turn=2).render(Reply(text="One. Two. Three. Four. Five."))
    assert turns == ["One. Two.", "Three. Four.", "Five."]
