"""Core data types shared by every layer of the engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Channel(str, Enum):
    """The eight entry points. Every one maps onto the same Message and Reply types."""

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


@dataclass
class Citation:
    fact_id: str
    source: str
    review_status: str


@dataclass
class Reply:
    """What the engine says back. Channel adapters decide how to render it."""

    text: str
    citations: list[Citation] = field(default_factory=list)
    end_session: bool = False
    escalated: bool = False
    escalation_queue: str | None = None
    follow_up_channel: Channel | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)  # for example a payment request
