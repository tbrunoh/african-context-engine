"""One identity and one memory across every channel, keyed to the phone number."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .models import Channel, GeoPoint, Message

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def normalize_msisdn(number: str, default_country_code: str = "254") -> str:
    """Normalize a phone number to E.164.

    Handles the common local formats seen in channel callbacks, for example
    0712345678 or 254712345678 for Kenya. The default country code is Kenya's
    because that is the launch market; pass another for other deployments.
    """
    digits = re.sub(r"[^\d+]", "", number.strip())
    if digits.startswith("+"):
        candidate = digits
    elif digits.startswith("00"):
        candidate = "+" + digits[2:]
    elif digits.startswith("0"):
        candidate = "+" + default_country_code + digits[1:]
    elif digits.startswith(default_country_code):
        candidate = "+" + digits
    else:
        candidate = "+" + default_country_code + digits
    if not _E164.match(candidate):
        raise ValueError(f"Not a valid phone number: {number!r}")
    return candidate


@dataclass
class Turn:
    channel: Channel
    text: str
    role: str  # "user" or "ace"
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Profile:
    msisdn: str
    preferred_language: str | None = None
    preferred_channel: Channel | None = None
    last_location: GeoPoint | None = None
    consent_outcome_data: bool = False
    last_intent: object | None = None  # carried across channels by the engine
    history: list[Turn] = field(default_factory=list)

    def channels_used(self) -> list[Channel]:
        seen: list[Channel] = []
        for t in self.history:
            if t.channel not in seen:
                seen.append(t.channel)
        return seen

    def recent(self, n: int = 6) -> list[Turn]:
        return self.history[-n:]


class ProfileStore:
    """In-memory profile store. Swap for a database in production deployments."""

    def __init__(self, default_country_code: str = "254", max_history: int = 200) -> None:
        self._profiles: dict[str, Profile] = {}
        self.default_country_code = default_country_code
        self.max_history = max_history

    def get_or_create(self, number: str) -> Profile:
        key = normalize_msisdn(number, self.default_country_code)
        if key not in self._profiles:
            self._profiles[key] = Profile(msisdn=key)
        return self._profiles[key]

    def record_inbound(self, message: Message) -> Profile:
        profile = self.get_or_create(message.sender)
        if message.language:
            profile.preferred_language = message.language
        if message.location:
            profile.last_location = message.location
        profile.history.append(Turn(channel=message.channel, text=message.text, role="user"))
        self._trim(profile)
        return profile

    def record_reply(self, profile: Profile, channel: Channel, text: str) -> None:
        profile.history.append(Turn(channel=channel, text=text, role="ace"))
        self._trim(profile)

    def forget(self, number: str) -> bool:
        """Delete everything held about a person. Returns True if a profile existed."""
        key = normalize_msisdn(number, self.default_country_code)
        return self._profiles.pop(key, None) is not None

    def _trim(self, profile: Profile) -> None:
        if len(profile.history) > self.max_history:
            del profile.history[: len(profile.history) - self.max_history]
