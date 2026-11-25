from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import urllib.error
from wsgiref.util import setup_testing_defaults

import pytest

from ace_engine.channels import RcsAdapter, RcsWithSmsFallback, enabled_countries
from ace_engine.channels.rcs import (
    RCS_MAX_SUGGESTION_TEXT,
    RCS_MAX_SUGGESTIONS,
    agent_message,
    chip_word,
    chips_for,
    decode_event,
    suggestions,
    verify_signature,
    verify_webhook,
)
from ace_engine.commands import parse_command
from ace_engine.encoding import scale
from ace_engine.models import Channel, Citation, Reply, ReplyKind
from ace_engine.server import AceApp


def call(app, method, path, body=b"", headers=None):
    environ = {}
    setup_testing_defaults(environ)
    environ.update({"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(body)),
                    "CONTENT_TYPE": "application/json", "wsgi.input": io.BytesIO(body)})
    environ.update(headers or {})
    captured = {}

    def start_response(status, hdrs):
        captured["status"] = status

    payload = b"".join(app(environ, start_response))
    return int(captured["status"].split()[0]), None, payload


def envelope(event: dict) -> bytes:
    return json.dumps({"message": {"data": base64.b64encode(json.dumps(event).encode()).decode()}}).encode()


def signature(body: bytes, token: str) -> str:
    decoded = base64.b64decode(json.loads(body)["message"]["data"])
    return base64.b64encode(hmac.new(token.encode(), decoded, hashlib.sha512).digest()).decode()


class FakeRbm:
    def __init__(self, reachable=True, fail=None):
        self.is_reachable, self.fail, self.sent = reachable, fail, []

    def reachable(self, phone):
        return self.is_reachable

    def send(self, phone, text, chips=()):
        if self.fail:
            raise self.fail
        self.sent.append((phone, text, list(chips)))


class FakeSms:
    def __init__(self, fail_after=None):
        self.sent, self.fail_after = [], fail_after

    def send(self, to, text, link_id=None):
        if self.fail_after is not None and len(self.sent) >= self.fail_after:
            raise OSError("gateway down")
        self.sent.append((to, text))


# ---------------------------------------------------------------- parsing and rendering

def test_parse_text_suggestion_location_and_file():
    adapter = RcsAdapter()
    msg = adapter.parse_inbound(json.loads(envelope({"senderPhoneNumber": "+2348031234567", "text": " hello ",
                                                      "messageId": "m1", "agentId": "a1"})))
    assert msg.channel is Channel.RCS and msg.sender == "+2348031234567" and msg.text == "hello"
    chip = adapter.parse_inbound({"senderPhoneNumber": "+27821234567",
                                  "suggestionResponse": {"postbackData": base64.b64encode(b"Rain this week").decode()}})
    assert chip.text == "Rain this week"
    where = adapter.parse_inbound({"senderPhoneNumber": "+27821234567",
                                   "location": {"latitude": -26.2, "longitude": 28.04}})
    assert where.location.lat == -26.2
    photo = adapter.parse_inbound({"senderPhoneNumber": "+27821234567",
                                   "userFile": {"payload": {"mimeType": "image/jpeg", "fileUri": "https://x/y"}}})
    assert photo.attachments[0].kind == "image"


def test_receipts_typing_and_malformed_events_are_not_messages():
    with pytest.raises(ValueError):
        RcsAdapter().parse_inbound({"senderPhoneNumber": "+27821234567", "eventType": "DELIVERED"})
    with pytest.raises(ValueError):
        decode_event({"message": {"data": "not base64 json"}})
    for bad in ({"senderPhoneNumber": "+27821234567", "location": {"latitude": 1}},
                {"senderPhoneNumber": "+27821234567", "userFile": "x"},
                {"senderPhoneNumber": "+27821234567", "suggestionResponse": None},
                {"message": {"data": base64.b64encode(b"[1, 2]").decode()}}):
        with pytest.raises(ValueError):
            RcsAdapter().parse_inbound(bad)


@pytest.mark.parametrize("language", ["en", "sw", "fr", "pt", "ar", "am", "om", "so"])
def test_chips_are_commands_in_every_language(language):
    for command in ("more", "sources", "help"):
        word = chip_word(command, language)
        assert len(word) <= RCS_MAX_SUGGESTION_TEXT and parse_command(word).name == command
    assert len(chips_for(Reply(text="x", language=language))) == 3
    assert chips_for(Reply(text="x", kind=ReplyKind.EMERGENCY, language=language)) == []
    assert len(chips_for(Reply(text="x", kind=ReplyKind.CLARIFY, language=language))) == 1


def test_render_lists_sources():
    reply = Reply(text="Dry maize to 13% moisture.", citations=[Citation("f1", "FAO", "reviewed")])
    assert RcsAdapter().render(reply) == ["Dry maize to 13% moisture.\n\nSources: FAO"]


def test_suggestions_respect_limits():
    chips = suggestions([f"Option number {i} with a long label" for i in range(20)])
    assert len(chips) == RCS_MAX_SUGGESTIONS
    assert all(len(c["reply"]["text"]) <= RCS_MAX_SUGGESTION_TEXT for c in chips)
    body = agent_message("hi", ["Yes", "Yes", "No"], traffic_type="TRANSACTION")
    assert [c["reply"]["text"] for c in body["contentMessage"]["suggestions"]] == ["Yes", "No"]
    assert body["messageTrafficType"] == "TRANSACTION"
    assert "messageTrafficType" not in agent_message("hi")


def test_rcs_budget_fits_sms_for_every_alphabet():
    assert scale(450, "rcs", "am") == scale(450, "sms", "am") < 450
    assert scale(450, "rcs", "sw") == 450


# ---------------------------------------------------------------- webhook security

def test_signature_and_verification():
    body = envelope({"senderPhoneNumber": "+2348031234567", "text": "hi"})
    assert verify_signature(body, signature(body, "tok"), "tok")
    assert not verify_signature(body, signature(body, "other"), "tok")
    assert not verify_signature(body, None, "tok") and not verify_signature(b"{}", "x", "tok")
    assert verify_webhook({"clientToken": "tok", "secret": "123"}, "tok") == "123"
    assert verify_webhook({"clientToken": "bad", "secret": "123"}, "tok") is None
    assert verify_webhook({"clientToken": "tok", "secret": "123"}, "") is None
    assert verify_webhook({"clientToken": "é", "secret": "123"}, "tok") is None
    assert not verify_signature(body, "é", "tok")


# ---------------------------------------------------------------- RCS with SMS fallback

def test_rcs_is_off_until_a_country_is_listed(monkeypatch):
    monkeypatch.delenv("ACE_RCS_COUNTRIES", raising=False)
    assert enabled_countries() == frozenset()
    assert enabled_countries(" ng, za ,") == {"NG", "ZA"}
    rbm, sms = FakeRbm(), FakeSms()
    out = RcsWithSmsFallback(rbm, sms).send("+2348031234567", "hello")
    assert out["channel"] == "sms" and not rbm.sent and sms.sent


def test_rcs_where_enabled_and_reachable():
    rbm, sms = FakeRbm(), FakeSms()
    out = RcsWithSmsFallback(rbm, sms, ["NG"]).send("+2348031234567", "hello", chips=["Rain"])
    assert out["channel"] == "rcs" and rbm.sent == [("+2348031234567", "hello", ["Rain"])] and not sms.sent


def test_sms_when_country_off_unreachable_or_send_refused():
    refused = urllib.error.HTTPError("u", 500, "error", None, None)
    for rbm, phone in ((FakeRbm(), "+254711000000"), (FakeRbm(reachable=False), "+2348031234567"),
                       (FakeRbm(fail=refused), "+2348031234567"),
                       (FakeRbm(fail=urllib.error.URLError("refused")), "+2348031234567")):
        sms = FakeSms()
        out = RcsWithSmsFallback(rbm, sms, ["NG"]).send(phone, "text " * 200, sms_text="short reply")
        assert out["channel"] == "sms" and sms.sent == [(phone, "short reply")]


def test_timeout_after_send_does_not_text_twice():
    sms = FakeSms()
    out = RcsWithSmsFallback(FakeRbm(fail=TimeoutError()), sms, ["NG"]).send("+2348031234567", "hello")
    assert out == {"channel": "rcs", "parts": ["hello"], "confirmed": False} and not sms.sent


def test_sms_failure_is_reported_not_raised():
    out = RcsWithSmsFallback(None, FakeSms(fail_after=1), ["NG"]).send("+2348031234567", "word " * 120)
    assert out["complete"] is False and out["channel"] == "sms" and len(out["parts"]) == 1
    assert RcsWithSmsFallback(None, FakeSms(fail_after=0), []).send("+2348031234567", "hi")["channel"] == "none"


def test_no_sender_reports_undelivered():
    assert RcsWithSmsFallback(None, None, ["NG"]).send("+2348031234567", "hi")["channel"] == "none"


# ---------------------------------------------------------------- server

def test_rcs_webhook_end_to_end(engine):
    rbm, sms = FakeRbm(), FakeSms()
    app = AceApp(engine, api_token="", webhook_secret="", sms_sender=sms, rcs_sender=rbm,
                 rcs_client_token="tok", rcs_countries=["NG"])
    code, _, secret = call(app, "POST", "/rcs", json.dumps({"clientToken": "tok", "secret": "42"}).encode(),
                           headers={"HTTP_X_GOOG_WEBHOOK_TYPE": "verification"})
    assert code == 200 and secret == b"42"
    body = envelope({"senderPhoneNumber": "+2348031234567", "text": "how do I store maize"})
    assert call(app, "POST", "/rcs", body)[0] == 403
    code, _, out = call(app, "POST", "/rcs", body, headers={"HTTP_X_GOOG_SIGNATURE": signature(body, "tok")})
    data = json.loads(out)
    assert code == 200 and data["channel"] == "rcs" and "Sources:" in rbm.sent[0][1]
    assert rbm.sent[0][2] == ["More", "Sources", "Help"]
    receipt = envelope({"senderPhoneNumber": "+2348031234567", "eventType": "READ"})
    out = call(app, "POST", "/rcs", receipt, headers={"HTTP_X_GOOG_SIGNATURE": signature(receipt, "tok")})[2]
    assert json.loads(out)["status"] == "ignored"


def test_unsigned_messages_never_trigger_texts(engine):
    sms = FakeSms()
    app = AceApp(engine, api_token="", webhook_secret="", sms_sender=sms, rcs_client_token="")
    body = envelope({"senderPhoneNumber": "+2348031234567", "text": "hello"})
    assert call(app, "POST", "/rcs", body)[0] == 503 and not sms.sent


def test_rcs_webhook_answers_200_when_sms_fails(engine):
    app = AceApp(engine, api_token="", webhook_secret="", sms_sender=FakeSms(fail_after=0),
                 rcs_client_token="tok", rcs_countries=[])
    body = envelope({"senderPhoneNumber": "+2348031234567", "text": "how do I store maize"})
    code, _, out = call(app, "POST", "/rcs", body, headers={"HTTP_X_GOOG_SIGNATURE": signature(body, "tok")})
    assert code == 200 and json.loads(out)["channel"] == "none"


def test_rcs_emergency_falls_back_to_sms_with_numbers_intact(engine):
    sms = FakeSms()
    app = AceApp(engine, api_token="", webhook_secret="", sms_sender=sms, rcs_sender=FakeRbm(reachable=False),
                 rcs_client_token="tok", rcs_countries=["ZA"])
    body = envelope({"senderPhoneNumber": "+27821234567", "text": "my wife is bleeding heavily"})
    out = json.loads(call(app, "POST", "/rcs", body, headers={"HTTP_X_GOOG_SIGNATURE": signature(body, "tok")})[2])
    assert out["kind"] == "emergency" and out["channel"] == "sms"
    assert any(ch.isdigit() for _, part in sms.sent for ch in part) and len(sms.sent) <= 3
