"""USSD adapter.

Parses the callback shape used by common African USSD gateways (for example
Africa's Talking): form fields sessionId, serviceCode, phoneNumber and text,
where text holds every menu input of the session joined by "*". Responses
start with CON to keep the session open or END to close it.
"""
from __future__ import annotations

from typing import Any

from ..models import Channel, Message, Reply
from .base import ChannelAdapter, truncate_words

USSD_MAX_CHARS = 182  # a common gateway limit for one USSD screen


class UssdAdapter(ChannelAdapter):
    channel = Channel.USSD

    def __init__(self, max_chars: int = USSD_MAX_CHARS) -> None:
        self.max_chars = max_chars

    def parse_inbound(self, payload: dict[str, Any]) -> Message:
        inputs = [p for p in str(payload.get("text", "")).split("*") if p != ""]
        return Message(
            channel=self.channel,
            sender=str(payload["phoneNumber"]),
            text=inputs[-1] if inputs else "",
            session_id=str(payload.get("sessionId", "")) or None,
            raw={"inputs": inputs, "serviceCode": payload.get("serviceCode")},
        )

    def render(self, reply: Reply) -> list[str]:
        prefix = "END " if reply.end_session else "CON "
        body = truncate_words(reply.text, self.max_chars - len(prefix))
        return [prefix + body]
