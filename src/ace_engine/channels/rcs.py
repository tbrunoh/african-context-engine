"""RCS Business Messaging, with SMS fallback.

RCS brings suggested replies and a verified business sender into the phone's
own messaging app, with no install, on Android phones and on iPhones running
iOS 18.1 or later, where the carrier supports it. It travels over mobile data
or Wi-Fi, so it reaches people with a capable phone, a carrier that has
launched RCS and a data connection. Everyone else is still reached by SMS.

ACE therefore treats RCS as a richer layer over SMS, never as a replacement:

* RCS is off until an operator lists the countries where it is launched
  (``ACE_RCS_COUNTRIES``, for example ``NG,ZA``).
* Before sending, ACE asks the RBM API whether the person can receive RCS.
  A 404 means they cannot (no capable device, RCS switched off, or the agent
  is not launched on their network), and the reply goes out as SMS.
* A send that RCS refuses or cannot start also falls back to SMS. A send
  that times out after Google may have accepted it does not, so nobody gets
  the same reply twice.

Replies end with suggested reply chips (More, Sources, Help) in the person's
language. Each chip sends a command word ACE already understands.

Inbound messages arrive at a webhook. Google signs each one: the header
``X-Goog-Signature`` holds the base64 HMAC SHA512 of the decoded payload,
keyed with the webhook's client token.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Iterable
from typing import Any

from .. import i18n
from ..countries import country_for_msisdn
from ..models import Attachment, Channel, GeoPoint, Message, Reply, ReplyKind
from .base import ChannelAdapter
from .sms import SmsAdapter

RCS_MAX_TEXT = 3072          # text limit of one agent message
RCS_MAX_SUGGESTIONS = 11     # suggestion chips after one message
RCS_MAX_SUGGESTION_TEXT = 25  # characters on one chip
RBM_HOST = "rcsbusinessmessaging.googleapis.com"
log = logging.getLogger("ace.rcs")


def decode_event(payload: dict[str, Any]) -> dict[str, Any]:
    """The user event inside a webhook body. Accepts the signed envelope
    ({"message": {"data": <base64>}}) or an event that is already decoded."""
    message = payload.get("message")
    if isinstance(message, dict) and isinstance(message.get("data"), str):
        try:
            return json.loads(base64.b64decode(message["data"]))
        except (binascii.Error, ValueError) as exc:
            raise ValueError("RCS payload is not valid base64 JSON") from exc
    return payload


class RcsAdapter(ChannelAdapter):
    channel = Channel.RCS

    def parse_inbound(self, payload: dict[str, Any]) -> Message:
        try:
            return self._parse(decode_event(payload))
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("RCS payload is malformed") from exc

    def _parse(self, event: dict[str, Any]) -> Message:
        if not isinstance(event, dict):
            raise TypeError("event is not an object")
        sender = str(event.get("senderPhoneNumber") or "")
        if not sender or event.get("eventType"):
            raise ValueError("Payload holds no user message")  # delivery, read and typing events
        text, attachments, location = "", [], None
        if "text" in event:
            text = str(event["text"])
        elif "suggestionResponse" in event:
            choice = event["suggestionResponse"]
            text = str(choice.get("text") or _postback_text(choice.get("postbackData")))
        elif "location" in event:
            loc = event["location"]
            location = GeoPoint(float(loc["latitude"]), float(loc["longitude"]))
        elif "userFile" in event:
            file = event["userFile"].get("payload", {})
            attachments.append(Attachment(kind=_kind(file.get("mimeType", "")), uri=str(file.get("fileUri", "")),
                                          mime_type=file.get("mimeType")))
        return Message(channel=self.channel, sender=sender if sender.startswith("+") else "+" + sender,
                       text=text.strip(), attachments=attachments, location=location,
                       raw={"messageId": event.get("messageId"), "agentId": event.get("agentId")})

    def render(self, reply: Reply) -> list[str]:
        text = reply.text.strip()
        if reply.citations:
            sources = "; ".join(dict.fromkeys(c.source for c in reply.citations))
            label = {"sw": "Vyanzo"}.get(reply.language, "Sources")
            text = f"{text}\n\n{label}: {sources}"
        return [text[i:i + RCS_MAX_TEXT] for i in range(0, len(text), RCS_MAX_TEXT)] or [""]


# Command words ACE already understands, first word per language. Added languages read theirs from locales/.
_CHIP_WORDS = {"en": {"more": "More", "sources": "Sources", "help": "Help"},
               "sw": {"more": "Zaidi", "sources": "Vyanzo", "help": "Msaada"},
               "fr": {"more": "Plus", "sources": "Sources", "help": "Aide"}}


def chip_word(command: str, language: str) -> str:
    """The command word for a chip in the person's language, falling back to English."""
    if language in _CHIP_WORDS:
        return _CHIP_WORDS[language][command]
    loc = i18n.locales().get(language)
    words = (loc.phrases.get(f"commands.COMMANDS.{command}") if loc else None) or ()
    return str(words[0]).capitalize() if words else _CHIP_WORDS["en"][command]


def chips_for(reply: Reply) -> list[str]:
    """Suggested replies after a reply: none after an emergency, so the numbers stay the focus."""
    if reply.kind is ReplyKind.EMERGENCY:
        return []
    names = ("more", "sources", "help") if reply.kind is ReplyKind.ANSWER else ("help",)
    return [chip_word(n, reply.language) for n in names]


def suggestions(labels: Iterable[str]) -> list[dict[str, Any]]:
    """Suggested reply chips: at most 11, each cut to 25 characters. Tapping one sends its label back."""
    chips = []
    for label in list(dict.fromkeys(str(x).strip() for x in labels if str(x).strip()))[:RCS_MAX_SUGGESTIONS]:
        short = label[:RCS_MAX_SUGGESTION_TEXT]
        chips.append({"reply": {"text": short, "postbackData": base64.b64encode(label.encode()).decode()}})
    return chips


def agent_message(text: str, chips: Iterable[str] = (), traffic_type: str | None = None) -> dict[str, Any]:
    """The body of phones.agentMessages.create for a text message with optional suggested replies."""
    content: dict[str, Any] = {"text": text[:RCS_MAX_TEXT]}
    rendered = suggestions(chips)
    if rendered:
        content["suggestions"] = rendered
    body: dict[str, Any] = {"contentMessage": content}
    if traffic_type:
        body["messageTrafficType"] = traffic_type
    return body


def verify_signature(body: bytes, signature_header: str | None, client_token: str) -> bool:
    """Check X-Goog-Signature: base64 HMAC SHA512 of the decoded payload, keyed with the client token."""
    if not client_token or not signature_header:
        return False
    try:
        data = json.loads(body or b"{}")["message"]["data"]
        decoded = base64.b64decode(data)
    except (KeyError, TypeError, ValueError, binascii.Error):
        return False
    expected = base64.b64encode(hmac.new(client_token.encode(), decoded, hashlib.sha512).digest()).decode()
    return hmac.compare_digest(expected.encode(), signature_header.strip().encode())


def verify_webhook(payload: dict[str, Any], client_token: str) -> str | None:
    """Answer the console's verification request: return the secret when the client token matches."""
    token, secret = payload.get("clientToken"), payload.get("secret")
    if client_token and isinstance(token, str) and isinstance(secret, str) \
            and hmac.compare_digest(token.encode(), client_token.encode()):
        return secret
    return None


def enabled_countries(value: str | None = None) -> frozenset[str]:
    """Countries where RCS is switched on, from ACE_RCS_COUNTRIES. Empty means RCS is off."""
    raw = value if value is not None else os.environ.get("ACE_RCS_COUNTRIES", "")
    return frozenset(code.strip().upper() for code in raw.split(",") if code.strip())


class RbmSender:
    """Send through the RCS Business Messaging API.

    Configure RBM_AGENT_ID and give an OAuth access token for a service account with RBM access, either
    as RBM_ACCESS_TOKEN or as a callable that returns a fresh token (for example from google-auth).
    A static token expires (Google OAuth access tokens last about an hour), so production should pass a
    callable that refreshes it. RBM_REGION, when set, selects a regional endpoint: Google routes numbers
    that start with +2 or +3, which covers Africa, to ``europe``. RBM_TRAFFIC_TYPE, when set, is sent as
    messageTrafficType for carriers that bill by traffic type.
    """

    def __init__(self, agent_id: str | None = None, token: str | Callable[[], str] | None = None,
                 region: str | None = None, traffic_type: str | None = None, timeout_s: float = 10.0) -> None:
        self.agent_id = agent_id or os.environ.get("RBM_AGENT_ID", "")
        self._token = token if token is not None else os.environ.get("RBM_ACCESS_TOKEN", "")
        region = region if region is not None else os.environ.get("RBM_REGION", "")
        self.base = f"https://{region + '-' if region else ''}{RBM_HOST}/v1"
        self.traffic_type = traffic_type or os.environ.get("RBM_TRAFFIC_TYPE") or None
        self.timeout_s = timeout_s
        if not self.agent_id or not self._token:
            raise ValueError("Set RBM_AGENT_ID and RBM_ACCESS_TOKEN, or pass a token callable")

    def _headers(self) -> dict[str, str]:
        token = self._token() if callable(self._token) else self._token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _url(self, phone: str, tail: str, **params: str) -> str:
        query = urllib.parse.urlencode({"agentId": self.agent_id, **params})
        return f"{self.base}/phones/{urllib.parse.quote(phone)}/{tail}?{query}"

    def reachable(self, phone: str) -> bool:
        """True when the person can receive RCS from this agent. A 404 means they cannot."""
        req = urllib.request.Request(self._url(phone, "capabilities", requestId=str(uuid.uuid4())),
                                     headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s):  # noqa: S310  fixed provider URL
                return True
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
            raise

    def send(self, phone: str, text: str, chips: Iterable[str] = ()) -> dict[str, Any]:
        body = json.dumps(agent_message(text, chips, self.traffic_type)).encode()
        req = urllib.request.Request(self._url(phone, "agentMessages", messageId=str(uuid.uuid4())),
                                     data=body, headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310  fixed provider URL
            return json.loads(resp.read() or b"{}")


class RcsWithSmsFallback:
    """Deliver one reply as RCS where the person can receive it, and as SMS everywhere else.

    ``rcs`` needs ``reachable(phone)`` and ``send(phone, text, chips)``, like RbmSender. ``sms`` needs
    ``send(phone, text)``, like AfricasTalkingSms. Either may be None: with no RCS sender every reply
    goes by SMS, and with no SMS sender a reply that cannot go by RCS is reported as undelivered.
    """

    def __init__(self, rcs: Any = None, sms: Any = None, countries: Iterable[str] | None = None,
                 max_sms_segments: int = 3) -> None:
        self.rcs, self.sms = rcs, sms
        self.countries = frozenset(c.upper() for c in countries) if countries is not None else enabled_countries()
        self.sms_render = SmsAdapter(max_segments=max_sms_segments)

    def rcs_allowed(self, phone: str) -> bool:
        country = country_for_msisdn(phone)
        return self.rcs is not None and country is not None and country.code in self.countries

    def send(self, phone: str, text: str, chips: Iterable[str] = (), sms_text: str | None = None) -> dict[str, Any]:
        """Returns {"channel": "rcs" | "sms" | "none", "parts": [...]} describing what went out."""
        chips = list(chips)
        if self.rcs_allowed(phone):
            try:
                reachable = self.rcs.reachable(phone)
            except Exception:  # noqa: BLE001  any failure before sending, token errors included, means SMS
                log.warning("RCS capability check failed, falling back to SMS", exc_info=True)
                reachable = False
            if reachable:
                try:
                    self.rcs.send(phone, text, chips)
                    return {"channel": "rcs", "parts": [text]}
                except TimeoutError:
                    # Google may have accepted the message; sending SMS too could deliver it twice.
                    log.warning("RCS send timed out; not falling back, to avoid a duplicate")
                    return {"channel": "rcs", "parts": [text], "confirmed": False}
                except Exception:  # noqa: BLE001  refused or never started: fall back to SMS
                    log.warning("RCS send failed, falling back to SMS", exc_info=True)
        parts = self.sms_render.render(Reply(text=sms_text if sms_text is not None else text))
        if self.sms is None:
            return {"channel": "none", "parts": parts}
        sent = []
        try:
            for part in parts:
                self.sms.send(phone, part)
                sent.append(part)
        except Exception:  # noqa: BLE001  never fail the webhook, or Google retries and repeats sent parts
            log.warning("SMS fallback failed after %d of %d parts", len(sent), len(parts), exc_info=True)
            return {"channel": "sms" if sent else "none", "parts": sent, "complete": False}
        return {"channel": "sms", "parts": parts}


def _postback_text(data: Any) -> str:
    try:
        return base64.b64decode(str(data or "")).decode()
    except (binascii.Error, UnicodeDecodeError):
        return str(data or "")


def _kind(mime: str) -> str:
    head = mime.split("/", 1)[0]
    return head if head in ("image", "audio", "video") else "document"
