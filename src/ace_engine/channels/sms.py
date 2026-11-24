"""SMS adapter with GSM-7 aware segmentation."""
from __future__ import annotations

from typing import Any

from ..models import Channel, Message, Reply
from .base import ChannelAdapter

# GSM 03.38 basic character set. Text outside it is sent as UCS-2.
_GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
_GSM7_EXT = set("^{}\\[~]|€")  # each costs two septets


def is_gsm7(text: str) -> bool:
    return all(c in _GSM7 or c in _GSM7_EXT for c in text)


def segment(text: str) -> list[str]:
    """Split text into SMS segments: 160/153 for GSM-7, 70/67 for UCS-2."""
    gsm = is_gsm7(text)
    single, multi = (160, 153) if gsm else (70, 67)

    def cost(s: str) -> int:
        return sum(2 if (gsm and c in _GSM7_EXT) else 1 for c in s)

    if cost(text) <= single:
        return [text]
    parts, current = [], ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if cost(candidate) <= multi:
            current = candidate
            continue
        if current:
            parts.append(current)
        while cost(word) > multi:  # a single very long token
            parts.append(word[:multi])
            word = word[multi:]
        current = word
    if current:
        parts.append(current)
    return parts


class SmsAdapter(ChannelAdapter):
    channel = Channel.SMS

    def __init__(self, max_segments: int = 3) -> None:
        self.max_segments = max_segments

    def parse_inbound(self, payload: dict[str, Any]) -> Message:
        return Message(channel=self.channel, sender=str(payload["from"]),
                       text=str(payload.get("text", "")).strip(), raw=payload)

    def render(self, reply: Reply) -> list[str]:
        parts = segment(" ".join(reply.text.split()))
        if len(parts) > self.max_segments:
            parts = parts[: self.max_segments]
            parts[-1] = parts[-1][: max(0, len(parts[-1]) - 4)].rstrip() + " ..."
        return parts
