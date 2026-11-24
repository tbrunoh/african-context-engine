"""Core data types shared by every layer of the engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Channel(str, Enum):
    """Entry points. Every one maps onto the same Message and Reply types."""

    VOICE = "voice"
    USSD = "ussd"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    APP = "app"
    AGENT = "agent"
    RADIO = "radio"
    API = "api"


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float
    altitude_m: float | None = None


@dataclass
class Attachment:
    kind: str  # "image", "audio", "document"
    uri: str
    mime_type: str | None = None


@dataclass
class Message:
    """A normalized inbound message, whatever channel it arrived on."""

    channel: Channel
    sender: str  # E.164 phone number, the identity key across channels
    text: str = ""
    language: str | None = None  # BCP 47 tag, for example "sw", "ki", "en"
    location: GeoPoint | None = None
    attachments: list[Attachment] = field(default_factory=list)
    session_id: str | None = None
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw: dict[str, Any] = field(default_factory=dict)


class ReplyKind(str, Enum):
    ANSWER = "answer"          # grounded in context facts
    EMERGENCY = "emergency"    # safety rail fired: numbers to call, human handoff raised
    SCAM = "scam"              # Scam Shield verdict
    CLARIFY = "clarify"        # no checked guidance matched; ACE says so and offers options
    SYSTEM = "system"          # commands such as language change, data deletion, help


@dataclass
class Citation:
    fact_id: str
    source: str
    review_status: str
    source_url: str | None = None


@dataclass
class Reply:
    """What the engine says back. Channel adapters decide how to render it."""

    text: str
    kind: ReplyKind = ReplyKind.ANSWER
    language: str = "en"
    citations: list[Citation] = field(default_factory=list)
    end_session: bool = False
    escalated: bool = False
    escalation_queue: str | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text, "kind": self.kind.value, "language": self.language,
            "escalated": self.escalated, "escalation_queue": self.escalation_queue,
            "citations": [c.__dict__ for c in self.citations], "actions": self.actions,
        }
