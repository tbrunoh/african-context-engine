"""One web server for every channel, using only the Python standard library.

Routes
    GET  /                    browser playground: a phone simulator for USSD and SMS
    GET  /healthz             liveness and pack counts
    GET  /v1/packs            loaded packs with fact counts
    POST /v1/ask              JSON question in, grounded JSON answer out
    POST /v1/scam             JSON message in, Scam Shield verdict out
    GET  /v1/emergency        numbers for a safety queue, for example ?queue=gbv
    GET  /v1/services         V2 decision services and their coverage in each country
    POST /v1/services/<id>    run one service: {"country", "place" or "lat"/"lon", "language", "text", ...}
    POST /ussd                Africa's Talking USSD callback (form)  -> text/plain CON or END
    POST /sms                 Africa's Talking inbound SMS (form)     -> JSON, and sends replies if configured
    POST /voice               Africa's Talking voice callback (form)  -> XML actions
    GET  /voice/audio/<file>  synthesised prompts the voice call plays (only with a PlayedVoice)
    GET  /whatsapp            Meta webhook verification
    POST /whatsapp            WhatsApp Cloud API webhook (JSON)      -> sends replies if configured
    POST /rcs                 RCS Business Messaging webhook (JSON)  -> replies by RCS, or SMS as fallback

Security
    ACE_API_TOKEN         when set, /v1/* requires "Authorization: Bearer <token>"
    ACE_WEBHOOK_SECRET    when set, /ussd, /sms and /voice require ?key=<secret> in the callback URL
    WHATSAPP_APP_SECRET   when set, POST /whatsapp requires a valid X-Hub-Signature-256
    RBM_CLIENT_TOKEN      the RCS webhook client token: answers console verification and checks X-Goog-Signature.
                          Without it, POST /rcs answers 503, so unsigned messages can never trigger texts

RCS
    ACE_RCS_COUNTRIES     countries where RCS is switched on, for example NG,ZA. Empty (the default) keeps RCS off,
                          so replies go by SMS. Where it is on, ACE checks that each person can receive RCS first

Voice audio
    ACE_VOICE_AUDIO_URL   public base URL of this server; with GEMINI_API_KEY set, the voice line plays Gemini
                          TTS audio for languages the Say action cannot read, such as Amharic and Somali
    ACE_VOICE_AUDIO_DIR   where synthesised audio is cached (default .ace_voice_audio). The files hold only
                          fixed prompts and public pack text, so /voice/audio needs no key
"""
from __future__ import annotations

import hmac
import json
import logging
import os
from collections.abc import Callable, Iterable
from importlib import resources
from typing import Any
from urllib.parse import parse_qs

from .channels import (
    RcsAdapter,
    RcsWithSmsFallback,
    SmsAdapter,
    UssdApp,
    VoiceApp,
    WhatsAppAdapter,
    verify_signature,
    verify_subscription,
)
from .channels import rcs as rcs_channel
from .countries import COUNTRIES
from .engine import Engine
from .models import Channel, GeoPoint, Message
from .safety import contacts_for
from .scam import analyse

log = logging.getLogger("ace.server")
MAX_BODY = 64 * 1024
StartResponse = Callable[[str, list[tuple[str, str]]], Any]


def played_voice_from_env() -> Any:
    """A PlayedVoice backed by Gemini TTS when ACE_VOICE_AUDIO_URL and GEMINI_API_KEY are both set, else None."""
    base = os.environ.get("ACE_VOICE_AUDIO_URL", "")
    if not base or not os.environ.get("GEMINI_API_KEY"):
        return None
    from .speech import PlayedVoice
    from .speech.google import GeminiTextToSpeech
    return PlayedVoice(GeminiTextToSpeech(), os.environ.get("ACE_VOICE_AUDIO_DIR", ".ace_voice_audio"), base)


class AceApp:
    """A WSGI application. Run it with ace serve, or under any WSGI server such as gunicorn."""

    def __init__(self, engine: Engine, sms_sender: Any = None, whatsapp_sender: Any = None,
                 api_token: str | None = None, webhook_secret: str | None = None,
                 whatsapp_verify_token: str | None = None, whatsapp_app_secret: str | None = None,
                 rcs_sender: Any = None, rcs_client_token: str | None = None,
                 rcs_countries: Iterable[str] | None = None) -> None:
        self.engine = engine
        self.ussd = UssdApp(engine)
        self.voice = VoiceApp(engine, voice=played_voice_from_env())
        self.sms = SmsAdapter()
        self.wa = WhatsAppAdapter()
        self.rcs = RcsAdapter()
        self.sms_sender = sms_sender
        self.whatsapp_sender = whatsapp_sender
        self.api_token = api_token if api_token is not None else os.environ.get("ACE_API_TOKEN", "")
        self.webhook_secret = (webhook_secret if webhook_secret is not None
                               else os.environ.get("ACE_WEBHOOK_SECRET", ""))
        self.wa_verify = whatsapp_verify_token or os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
        self.wa_secret = (whatsapp_app_secret if whatsapp_app_secret is not None
                          else os.environ.get("WHATSAPP_APP_SECRET", ""))
        self.rcs_token = (rcs_client_token if rcs_client_token is not None
                          else os.environ.get("RBM_CLIENT_TOKEN", ""))
        self.rcs_delivery = RcsWithSmsFallback(rcs_sender, sms_sender, rcs_countries)

    # ------------------------------------------------------------------ WSGI

    def __call__(self, environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        method, path = environ.get("REQUEST_METHOD", "GET"), environ.get("PATH_INFO", "/")
        query = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
        try:
            body = self._body(environ)
            status, headers, payload = self.route(method, path, query, body, environ)
        except ValueError as exc:
            status, headers, payload = _json(400, {"error": str(exc)})
        except Exception:  # noqa: BLE001  never leak internals to a caller
            log.exception("unhandled error on %s %s", method, path)
            status, headers, payload = _json(500, {"error": "internal error"})
        start_response(status, headers)
        return [payload]

    def route(self, method: str, path: str, query: dict[str, str], body: bytes,
              environ: dict[str, Any]) -> tuple[str, list[tuple[str, str]], bytes]:
        if path == "/" and method == "GET":
            return "200 OK", [("Content-Type", "text/html; charset=utf-8")], _playground()
        if path == "/healthz":
            return _json(200, {"status": "ok", "packs": len(self.engine.packs), "facts": len(self.engine.store)})

        if path.startswith("/v1/"):
            if self.api_token and not _bearer_ok(environ, self.api_token):
                return _json(401, {"error": "missing or invalid bearer token"})
            return self._api(method, path, query, body)

        if path.startswith("/voice/audio/") and method == "GET" and self.voice.voice is not None:
            audio = self.voice.voice.audio(path.rsplit("/", 1)[-1])
            if audio is None:
                return _json(404, {"error": "not found"})
            return "200 OK", [("Content-Type", "audio/wav"), ("Cache-Control", "public, max-age=86400")], audio

        if path in ("/ussd", "/sms", "/voice"):
            if self.webhook_secret and not hmac.compare_digest(query.get("key", ""), self.webhook_secret):
                return _json(403, {"error": "invalid webhook key"})
            form = {k: v[0] for k, v in parse_qs(body.decode("utf-8", "replace")).items()}
            if path == "/ussd" and method == "POST":
                return "200 OK", [("Content-Type", "text/plain; charset=utf-8")], \
                    self.ussd.handle_payload(_require(form, "phoneNumber")).encode()
            if path == "/sms" and method == "POST":
                return self._sms(_require(form, "from"))
            if path == "/voice" and method == "POST":
                xml = self.voice.respond(form)
                return "200 OK", [("Content-Type", "application/xml; charset=utf-8")], xml.encode()

        if path == "/whatsapp":
            if method == "GET":
                challenge = verify_subscription(query.get("hub.mode"), query.get("hub.verify_token"),
                                                query.get("hub.challenge"), self.wa_verify)
                if challenge is None:
                    return _json(403, {"error": "verification failed"})
                return "200 OK", [("Content-Type", "text/plain")], challenge.encode()
            if method == "POST":
                if self.wa_secret and not verify_signature(body, environ.get("HTTP_X_HUB_SIGNATURE_256"),
                                                           self.wa_secret):
                    return _json(403, {"error": "invalid signature"})
                return self._whatsapp(body)

        if path == "/rcs" and method == "POST":
            data = _json_body(body)
            if environ.get("HTTP_X_GOOG_WEBHOOK_TYPE") == "verification" or "clientToken" in data:
                secret = rcs_channel.verify_webhook(data, self.rcs_token)
                if secret is None:
                    return _json(403, {"error": "verification failed"})
                return "200 OK", [("Content-Type", "text/plain")], secret.encode()
            if not self.rcs_token:  # never act on unsigned messages: they could trigger texts to any number
                return _json(503, {"error": "RCS webhook not configured: set RBM_CLIENT_TOKEN"})
            if not rcs_channel.verify_signature(body, environ.get("HTTP_X_GOOG_SIGNATURE"), self.rcs_token):
                return _json(403, {"error": "invalid signature"})
            return self._rcs(data)
        return _json(404, {"error": "not found"})

    # ------------------------------------------------------------------ handlers

    def _api(self, method: str, path: str, query: dict[str, str],
             body: bytes) -> tuple[str, list[tuple[str, str]], bytes]:
        if path == "/v1/packs" and method == "GET":
            return _json(200, {"packs": [{
                "id": p.id, "title": p.title, "version": p.version, "country": p.country,
                "countries": sorted({c for f in p.facts for c in f.scope.countries}), "license": p.license,
                "facts": len(p.facts), "labels": p.labels} for p in self.engine.packs]})
        if path == "/v1/emergency" and method == "GET":
            queue = query.get("queue", "emergency")
            country = (query.get("country") or self.engine.config.country or "").upper()
            if country not in COUNTRIES:  # never mix numbers from different countries
                return _json(400, {"error": "country is required, one of " + ", ".join(COUNTRIES)})
            contacts = contacts_for(queue, list(self.engine.store), country)
            return _json(200, {"queue": queue, "country": country, "contacts": [c.__dict__ for c in contacts]})
        if path == "/v1/services" and method == "GET":
            hub = self.engine.services
            if hub is None:
                return _json(200, {"services": [], "note": "no snapshots loaded, so V2 services are off"})
            from .services import SERVICES

            coverage = hub.coverage()
            return _json(200, {"preview": True, "services": [
                {"id": sid, "title": svc.title, "connectors": list(svc.connectors), "coverage": coverage[sid]}
                for sid, svc in SERVICES.items()]})
        if path.startswith("/v1/services/") and method == "POST":
            hub = self.engine.services
            if hub is None:
                return _json(503, {"error": "no snapshots loaded, so V2 services are off"})
            data = _json_body(body)
            params = {k: data[k] for k in ("weeks", "crop", "food") if data.get(k) is not None}
            if self.engine.safety.check(str(data.get("text", ""))).escalate:
                message = Message(channel=Channel.API, sender=str(data.get("phone") or "+254700000000"),
                                  text=str(data["text"]), language=data.get("language"))
                return _json(200, {"outcome": "emergency", **self.engine.handle(message).to_dict()})
            return _json(200, hub.call(path.rsplit("/", 1)[-1], data.get("country"), data.get("place"),
                                       data.get("lat"), data.get("lon"), data.get("language") or "en",
                                       str(data.get("text", "")), params))
        if method != "POST":
            return _json(405, {"error": "method not allowed"})
        data = _json_body(body)
        if path == "/v1/ask":
            text = str(data.get("text", "")).strip()
            if not text:
                raise ValueError("text is required")
            channel = Channel(data.get("channel", "api"))
            location = None
            if data.get("lat") is not None and data.get("lon") is not None:
                location = GeoPoint(float(data["lat"]), float(data["lon"]), data.get("altitude_m"))
            message = Message(channel=channel, sender=str(data.get("phone") or "+254700000000"), text=text,
                              language=data.get("language"), location=location)
            reply = self.engine.handle(message)
            out = reply.to_dict()
            if channel is Channel.SMS:
                out["segments"] = self.sms.render(reply)
            return _json(200, out)
        if path == "/v1/scam":
            text = str(data.get("text", "")).strip()
            if not text:
                raise ValueError("text is required")
            report = analyse(text, data.get("sender"))
            budget = self.engine.config.budgets[Channel.API]
            reply = self.engine.scam_reply(report, data.get("language") or "en", budget)
            return _json(200, {**reply.to_dict(), "verdict": report.verdict.value, "score": report.score,
                               "signals": [s.id for s in report.signals]})
        return _json(404, {"error": "not found"})

    def _sms(self, form: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        message = self.sms.parse_inbound(form)
        reply = self.engine.handle(message)
        parts = self.sms.render(reply)
        if self.sms_sender is not None:
            for part in parts:
                self.sms_sender.send(message.sender, part, link_id=form.get("linkId"))
        return _json(200, {"kind": reply.kind.value, "segments": parts, "sent": self.sms_sender is not None})

    def _whatsapp(self, body: bytes) -> tuple[str, list[tuple[str, str]], bytes]:
        data = _json_body(body)
        try:
            message = self.wa.parse_inbound(data)
        except ValueError:
            return _json(200, {"status": "ignored"})  # delivery receipts and status updates
        reply = self.engine.handle(message)
        parts = self.wa.render(reply)
        if self.whatsapp_sender is not None:
            for part in parts:
                self.whatsapp_sender.send(message.sender, part)
        return _json(200, {"kind": reply.kind.value, "messages": parts, "sent": self.whatsapp_sender is not None})

    def _rcs(self, data: dict[str, Any]) -> tuple[str, list[tuple[str, str]], bytes]:
        try:
            message = self.rcs.parse_inbound(data)
        except ValueError:
            return _json(200, {"status": "ignored"})  # delivery, read and typing events
        reply = self.engine.handle(message)
        text = self.rcs.render(reply)[0]
        sent = self.rcs_delivery.send(message.sender, text, rcs_channel.chips_for(reply), sms_text=reply.text)
        return _json(200, {"kind": reply.kind.value, "messages": sent["parts"], "channel": sent["channel"]})

    @staticmethod
    def _body(environ: dict[str, Any]) -> bytes:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            raise ValueError("request body too large")
        return environ["wsgi.input"].read(length) if length else b""


def _json(code: int, data: dict[str, Any]) -> tuple[str, list[tuple[str, str]], bytes]:
    reasons = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
               405: "Method Not Allowed", 500: "Internal Server Error", 503: "Service Unavailable"}
    return (f"{code} {reasons.get(code, 'OK')}", [("Content-Type", "application/json; charset=utf-8")],
            json.dumps(data, ensure_ascii=False).encode())


def _json_body(body: bytes) -> dict[str, Any]:
    try:
        data = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise ValueError("body must be JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    return data


def _require(form: dict[str, str], field: str) -> dict[str, str]:
    if not form.get(field):
        raise ValueError(f"{field} is required")
    return form


def _bearer_ok(environ: dict[str, Any], token: str) -> bool:
    header = environ.get("HTTP_AUTHORIZATION", "")
    return header.startswith("Bearer ") and hmac.compare_digest(header[7:], token)


def _playground() -> bytes:
    return resources.files("ace_engine").joinpath("web/playground.html").read_bytes()


def serve(engine: Engine, host: str = "127.0.0.1", port: int = 8000, **kwargs: Any) -> None:
    from wsgiref.simple_server import make_server

    app = AceApp(engine, **kwargs)
    with make_server(host, port, app) as httpd:
        print(f"ACE is listening on http://{host}:{port}  ({len(engine.packs)} packs, {len(engine.store)} facts)")
        print("Open the address in a browser for the phone playground. Press Ctrl+C to stop.")
        httpd.serve_forever()
