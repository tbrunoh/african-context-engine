"""WhatsApp adapter for the WhatsApp Business Platform (Cloud API) webhook shape.

Policy note: since 15 January 2026 the Business API terms bar general purpose
AI assistants. ACE deployments on WhatsApp must stay vertical expert services
(agriculture, health, legal guidance) operated by or for a named business.
"""
from __future__ import annotations

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
        sender = msg["from"]
        return Message(
            channel=self.channel,
            sender=sender if sender.startswith("+") else "+" + sender,
            text=text, attachments=attachments, location=location, raw=msg,
        )

    def render(self, reply: Reply) -> list[str]:
        text = reply.text.strip()
        if reply.citations:
            sources = "; ".join(sorted({c.source for c in reply.citations}))
            text = f"{text}\n\nSources: {sources}"
        return [text[i:i + WHATSAPP_MAX_TEXT] for i in range(0, len(text), WHATSAPP_MAX_TEXT)] or [""]
