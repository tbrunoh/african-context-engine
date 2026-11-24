"""WhatsApp Business Platform (Cloud API): webhook parsing, verification and sending.

Policy note: since 15 January 2026 the Business API terms bar general
purpose AI assistants. ACE fits the allowed pattern only when a deployment is
a scoped service run by or for a named organisation (an agriculture advisory,
a maternal health line, a fraud help desk) that answers from its own context
packs. Do not deploy ACE on WhatsApp as an open ended assistant.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.request
from typing import Any

from ..models import Attachment, Channel, GeoPoint, Message, Reply
from .base import ChannelAdapter

WHATSAPP_MAX_TEXT = 4096


class WhatsAppAdapter(ChannelAdapter):
    channel = Channel.WHATSAPP

    def parse_inbound(self, payload: dict[str, Any]) -> Message:
        try:
            value = payload["entry"][0]["changes"][0]["value"]
            msg = value["messages"][0]
        except (KeyError, IndexError) as exc:
            raise ValueError("Payload holds no inbound message") from exc
        kind = msg.get("type")
        text, attachments, location = "", [], None
        if kind == "text":
            text = msg["text"]["body"]
        elif kind in ("image", "audio", "document", "video"):
            media = msg[kind]
            attachments.append(Attachment(kind=kind, uri=f"whatsapp-media:{media['id']}",
                                          mime_type=media.get("mime_type")))
            text = media.get("caption", "")
        elif kind == "location":
            loc = msg["location"]
            location = GeoPoint(float(loc["latitude"]), float(loc["longitude"]))
        elif kind == "interactive":
            inter = msg["interactive"]
            text = (inter.get("button_reply") or inter.get("list_reply") or {}).get("title", "")
        sender = msg["from"]
        return Message(
            channel=self.channel,
            sender=sender if sender.startswith("+") else "+" + sender,
            text=text, attachments=attachments, location=location, raw={"id": msg.get("id"), "type": kind},
        )

    def render(self, reply: Reply) -> list[str]:
        text = reply.text.strip()
        if reply.citations:
            sources = "; ".join(dict.fromkeys(c.source for c in reply.citations))
            label = {"sw": "Vyanzo"}.get(reply.language, "Sources")
            text = f"{text}\n\n{label}: {sources}"
        return [text[i:i + WHATSAPP_MAX_TEXT] for i in range(0, len(text), WHATSAPP_MAX_TEXT)] or [""]


def verify_subscription(mode: str | None, token: str | None, challenge: str | None,
                        expected_token: str) -> str | None:
    """Answer Meta's webhook verification request. Returns the challenge, or None to refuse."""
    if mode == "subscribe" and expected_token and token and hmac.compare_digest(token, expected_token):
        return challenge or ""
    return None


def verify_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Check the X-Hub-Signature-256 header so only Meta can call the webhook."""
    if not app_secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


def send_payload(to: str, text: str) -> dict[str, Any]:
    return {"messaging_product": "whatsapp", "to": to.lstrip("+"), "type": "text",
            "text": {"preview_url": False, "body": text}}


class WhatsAppCloudSender:
    """Send text messages. Configure WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID and
    WHATSAPP_API_VERSION (the Graph API version your app is set to use)."""

    def __init__(self, token: str | None = None, phone_number_id: str | None = None,
                 api_version: str | None = None, timeout_s: float = 10.0) -> None:
        self.token = token or os.environ.get("WHATSAPP_TOKEN", "")
        self.phone_number_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self.api_version = api_version or os.environ.get("WHATSAPP_API_VERSION", "")
        self.timeout_s = timeout_s
        if not (self.token and self.phone_number_id and self.api_version):
            raise ValueError("Set WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_API_VERSION")

    def send(self, to: str, text: str) -> dict[str, Any]:
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        req = urllib.request.Request(url, data=json.dumps(send_payload(to, text)).encode(), headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310  fixed provider URL
            return json.loads(resp.read() or b"{}")
