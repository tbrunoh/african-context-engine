from __future__ import annotations

import hashlib
import hmac
import io
import json
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

import pytest

from ace_engine.server import AceApp


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, to, text, link_id=None):
        self.sent.append((to, text))


def call(app, method, path, body=b"", content_type="application/json", query="", headers=None):
    environ = {}
    setup_testing_defaults(environ)
    environ.update({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
                    "CONTENT_LENGTH": str(len(body)), "CONTENT_TYPE": content_type, "wsgi.input": io.BytesIO(body)})
    environ.update(headers or {})
    captured = {}

    def start_response(status, hdrs):
        captured["status"], captured["headers"] = status, dict(hdrs)

    payload = b"".join(app(environ, start_response))
    return int(captured["status"].split()[0]), captured["headers"], payload


@pytest.fixture()
def app(engine):
    return AceApp(engine, api_token="", webhook_secret="", whatsapp_app_secret="")


def test_health_and_packs(app):
    code, _, body = call(app, "GET", "/healthz")
    assert code == 200 and json.loads(body)["packs"] >= 6
    code, _, body = call(app, "GET", "/v1/packs")
    assert {p["id"] for p in json.loads(body)["packs"]} >= {"ke-emergency-contacts", "ke-mobile-money-safety"}


def test_playground_is_served(app):
    code, headers, body = call(app, "GET", "/")
    assert code == 200 and headers["Content-Type"].startswith("text/html") and b"ACE playground" in body


def test_ask_endpoint(app):
    code, _, body = call(app, "POST", "/v1/ask", json.dumps({"text": "how do I store maize", "channel": "sms"}).encode())
    data = json.loads(body)
    assert code == 200 and data["kind"] == "answer" and data["citations"] and data["segments"]


def test_ask_validation(app):
    assert call(app, "POST", "/v1/ask", b"{}")[0] == 400
    assert call(app, "POST", "/v1/ask", b"not json")[0] == 400


def test_scam_endpoint(app):
    code, _, body = call(app, "POST", "/v1/scam", json.dumps({"text": "send your PIN now"}).encode())
    assert code == 200 and json.loads(body)["verdict"] == "likely_scam"


def test_emergency_endpoint(app):
    status, _, body = call(app, "GET", "/v1/emergency", query="queue=gbv&country=KE")
    assert status == 200 and "1195" in {c["number"] for c in json.loads(body)["contacts"]}
    _, _, body = call(app, "GET", "/v1/emergency", query="queue=gbv&country=za")
    assert "0800 428 428" in {c["number"] for c in json.loads(body)["contacts"]}
    status, _, _ = call(app, "GET", "/v1/emergency", query="queue=gbv")
    assert status == 400  # numbers from different countries are never mixed


def test_ussd_webhook(app):
    form = urlencode({"sessionId": "s1", "serviceCode": "*384#", "phoneNumber": "+254711000000", "text": ""})
    code, headers, body = call(app, "POST", "/ussd", form.encode(), "application/x-www-form-urlencoded")
    assert code == 200 and headers["Content-Type"].startswith("text/plain") and body.startswith(b"CON ACE")


def test_sms_webhook_sends_replies(engine):
    sender = FakeSender()
    app = AceApp(engine, sms_sender=sender, api_token="", webhook_secret="")
    form = urlencode({"from": "+254711000000", "to": "21606", "text": "how do I store maize"})
    code, _, body = call(app, "POST", "/sms", form.encode(), "application/x-www-form-urlencoded")
    assert code == 200 and json.loads(body)["sent"] and sender.sent[0][0] == "+254711000000"


def test_voice_webhook(app):
    form = urlencode({"isActive": "1", "callerNumber": "+254711000000", "sessionId": "v1"})
    code, headers, body = call(app, "POST", "/voice", form.encode(), "application/x-www-form-urlencoded")
    assert code == 200 and headers["Content-Type"].startswith("application/xml") and b"<GetDigits" in body


def test_whatsapp_webhook_and_status_updates(app):
    msg = {"entry": [{"changes": [{"value": {"messages": [
        {"from": "254711000000", "type": "text", "text": {"body": "how do I store maize"}}]}}]}]}
    code, _, body = call(app, "POST", "/whatsapp", json.dumps(msg).encode())
    assert code == 200 and "Sources:" in json.loads(body)["messages"][0]
    status = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    assert json.loads(call(app, "POST", "/whatsapp", json.dumps(status).encode())[2])["status"] == "ignored"


def test_whatsapp_signature_is_enforced(engine):
    app = AceApp(engine, api_token="", webhook_secret="", whatsapp_app_secret="s3cret")
    body = b'{"entry": []}'
    assert call(app, "POST", "/whatsapp", body)[0] == 403
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert call(app, "POST", "/whatsapp", body, headers={"HTTP_X_HUB_SIGNATURE_256": sig})[0] == 200


def test_api_token_is_enforced(engine):
    app = AceApp(engine, api_token="t0ken", webhook_secret="")
    assert call(app, "GET", "/v1/packs")[0] == 401
    assert call(app, "GET", "/v1/packs", headers={"HTTP_AUTHORIZATION": "Bearer t0ken"})[0] == 200


def test_webhook_secret_is_enforced(engine):
    app = AceApp(engine, api_token="", webhook_secret="k3y")
    form = urlencode({"phoneNumber": "+254711000000", "text": ""}).encode()
    assert call(app, "POST", "/ussd", form, "application/x-www-form-urlencoded")[0] == 403
    assert call(app, "POST", "/ussd", form, "application/x-www-form-urlencoded", query="key=k3y")[0] == 200


def test_body_limit_and_not_found(app):
    big = b"x" * (64 * 1024 + 1)
    assert call(app, "POST", "/v1/ask", big)[0] == 400
    assert call(app, "GET", "/nope")[0] == 404
