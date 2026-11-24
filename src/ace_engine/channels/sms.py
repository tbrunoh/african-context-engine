"""SMS: GSM-7 aware segmentation, Africa's Talking inbound parsing and sending.

Africa's Talking delivers inbound messages as a form POST with the fields
from, to, text, date, id and linkId. Replies go out through the messaging
API. Keeping replies inside GSM-7 matters: one non GSM character switches
the whole message to UCS-2 and cuts each segment from 160 to 70 characters.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

from ..models import Channel, Message, Reply
from .base import ChannelAdapter

# GSM 03.38 basic character set. Text outside it is sent as UCS-2.
_GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
_GSM7_EXT = set("^{}\\[~]|€")  # each costs two septets
_REPLACEMENTS = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                 "…": "...", " ": " "}


def is_gsm7(text: str) -> bool:
    return all(c in _GSM7 or c in _GSM7_EXT for c in text)


def to_gsm7(text: str) -> str:
    """Replace typographic characters that would force UCS-2 encoding."""
    return "".join(_REPLACEMENTS.get(c, c) for c in text)


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
                       text=str(payload.get("text", "")).strip(),
                       session_id=str(payload.get("linkId") or payload.get("id") or "") or None,
                       raw={k: payload.get(k) for k in ("to", "date", "id", "linkId")})

    def render(self, reply: Reply) -> list[str]:
        parts = segment(to_gsm7(" ".join(reply.text.split())))
        if len(parts) > self.max_segments:
            parts = parts[: self.max_segments]
            parts[-1] = parts[-1][: max(0, len(parts[-1]) - 4)].rstrip() + " ..."
        return parts


class AfricasTalkingSms:
    """Send SMS through Africa's Talking. Configure with AT_USERNAME, AT_API_KEY and
    optionally AT_SENDER_ID. The username "sandbox" targets the sandbox API."""

    def __init__(self, username: str | None = None, api_key: str | None = None,
                 sender_id: str | None = None, timeout_s: float = 10.0) -> None:
        self.username = username or os.environ.get("AT_USERNAME", "")
        self.api_key = api_key or os.environ.get("AT_API_KEY", "")
        self.sender_id = sender_id or os.environ.get("AT_SENDER_ID") or None
        self.timeout_s = timeout_s
        if not self.username or not self.api_key:
            raise ValueError("Set AT_USERNAME and AT_API_KEY to send SMS through Africa's Talking")
        host = "api.sandbox.africastalking.com" if self.username == "sandbox" else "api.africastalking.com"
        self.url = f"https://{host}/version1/messaging"

    def send(self, to: str, message: str, link_id: str | None = None) -> dict[str, Any]:
        fields = {"username": self.username, "to": to, "message": message}
        if self.sender_id:
            fields["from"] = self.sender_id
        if link_id:  # replies on premium short codes must carry the inbound linkId
            fields["linkId"] = link_id
        req = urllib.request.Request(self.url, data=urllib.parse.urlencode(fields).encode(), headers={
            "apiKey": self.api_key, "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310  fixed provider URL
            return json.loads(resp.read() or b"{}")
