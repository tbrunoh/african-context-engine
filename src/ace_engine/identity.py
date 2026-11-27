"""One identity across every channel, keyed to the phone number, stored pseudonymously.

ACE never needs to know who someone is. It needs to recognise the same phone
across USSD, SMS, voice and WhatsApp so a conversation can continue. The
store therefore keys every profile by a salted HMAC of the normalised number,
keeps only what improves the next answer, and deletes everything on request.

This follows the data minimisation principle in Kenya's Data Protection Act
2019. Deployments remain responsible for their own legal basis, notices and
registration with the Office of the Data Protection Commissioner.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .countries import COUNTRIES
from .models import Channel, GeoPoint, Message

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")
DEV_SALT = "ace-development-salt-change-me"


_COVERED_DIAL_CODES = tuple(c.dial for c in COUNTRIES.values())

# A web session has no phone number. Its sender is web:<country>:<random token>, so it gets its own private key,
# the country its visitor chose, and nothing that could match a real subscriber.
WEB_PREFIX = "web:"


def web_sender(country: str, token: str) -> str:
    """The sender for a browser session in a covered country."""
    code = country.upper()
    if code not in COUNTRIES:
        raise ValueError(f"unknown country {country!r}")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", token):
        raise ValueError("invalid session token")
    return f"{WEB_PREFIX}{code}:{token}"


def web_country(sender: str) -> str | None:
    """The country of a web session sender, or None for any other sender."""
    if not sender.startswith(WEB_PREFIX):
        return None
    code = sender[len(WEB_PREFIX):].split(":", 1)[0]
    return code if code in COUNTRIES else None


def normalize_msisdn(number: str, default_country_code: str | None = None) -> str:
    """Normalize a phone number to E.164.

    Handles the local formats seen in channel callbacks, for example 0712345678 or 254712345678 in Kenya,
    when the deployment names its country's dialling code. With no default, a number in local format has no
    country, so it is refused rather than given one: ACE never assumes a caller is in Kenya or anywhere else.
    """
    digits = re.sub(r"[^\d+]", "", number.strip())
    if digits.startswith("+"):
        candidate = digits
    elif digits.startswith("00"):
        candidate = "+" + digits[2:]
    elif default_country_code and digits.startswith("0"):
        candidate = "+" + default_country_code + digits[1:]
    elif default_country_code and digits.startswith(default_country_code):
        candidate = "+" + digits
    elif len(digits) >= 11 and any(digits.startswith(code) for code in _COVERED_DIAL_CODES):
        candidate = "+" + digits  # a full international number sent without the plus
    elif default_country_code:
        candidate = "+" + default_country_code + digits
    else:
        raise ValueError(f"No country for a number in local format: {number!r}")
    if not _E164.match(candidate):
        raise ValueError(f"Not a valid phone number: {number!r}")
    return candidate


def pseudonymize(msisdn: str, salt: str) -> str:
    """A stable, non reversible key for a normalised phone number."""
    return hmac.new(salt.encode(), msisdn.encode(), hashlib.sha256).hexdigest()[:32]


@dataclass
class Turn:
    channel: Channel
    text: str
    role: str  # "user" or "ace"
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Profile:
    key: str
    language: str | None = None
    last_location: GeoPoint | None = None
    last_topic: tuple[str, str] | None = None  # (vertical, topic) of the last grounded answer
    last_fact_ids: list[str] = field(default_factory=list)
    last_query: str | None = None
    last_place: tuple[str, str] | None = None     # (country, area code) the person last named, for V2 services
    pending_service: str | None = None            # a V2 service waiting for the person's place or details
    pending_text: str = ""                        # the question that service is answering
    pending_language: str | None = None           # the language that question was asked in
    pending_asked: bool = False                   # ACE already asked once about a place it could not find
    last_service: str | None = None               # the V2 service that gave the last answer, for a follow-up
    last_sources: list[str] = field(default_factory=list)  # that answer's sources, for SOURCES
    channels: list[Channel] = field(default_factory=list)
    history: list[Turn] = field(default_factory=list)
    opted_out: bool = False

    def recent(self, n: int = 6) -> list[Turn]:
        return self.history[-n:]


class ProfileStore:
    """In memory profiles. Implement the same methods over a database for production."""

    def __init__(self, salt: str | None = None, default_country_code: str | None = None,
                 keep_history: bool = True, max_history: int = 20) -> None:
        self.salt = salt or os.environ.get("ACE_PSEUDONYM_SALT") or DEV_SALT
        if self.salt == DEV_SALT and os.environ.get("ACE_ENV") == "production":
            warnings.warn("ACE_PSEUDONYM_SALT is not set; using the development salt", stacklevel=2)
        self.default_country_code = default_country_code
        self.keep_history = keep_history
        self.max_history = max_history
        self._profiles: dict[str, Profile] = {}

    def save(self, profile: Profile) -> None:
        """Persist a profile after a message. Profiles in memory are changed in place, so there is nothing to do."""

    def begin_request(self) -> None:
        """Called at the start of each web request. A store that caches reads drops them here."""

    def key_for(self, number: str) -> str:
        if number.startswith(WEB_PREFIX):  # a web session: its random token is the identity
            return pseudonymize(number, self.salt)
        try:
            canonical = normalize_msisdn(number, self.default_country_code)
        except ValueError:  # a local number with no country still gets its own private key, and no country
            canonical = "local:" + re.sub(r"\D", "", number)
        return pseudonymize(canonical, self.salt)

    def get_or_create(self, number: str) -> Profile:
        key = self.key_for(number)
        if key not in self._profiles:
            self._profiles[key] = Profile(key=key)
        return self._profiles[key]

    def peek(self, number: str) -> Profile | None:
        return self._profiles.get(self.key_for(number))

    def record_inbound(self, message: Message) -> Profile:
        profile = self.get_or_create(message.sender)
        if message.language:
            profile.language = message.language
        if message.location:
            profile.last_location = message.location
        if message.channel not in profile.channels:
            profile.channels.append(message.channel)
        self._append(profile, Turn(message.channel, message.text, "user"))
        return profile

    def record_reply(self, profile: Profile, channel: Channel, text: str) -> None:
        self._append(profile, Turn(channel, text, "ace"))

    def forget(self, number: str) -> bool:
        """Delete everything held about a person. Returns True if a profile existed."""
        return self._profiles.pop(self.key_for(number), None) is not None

    def __len__(self) -> int:
        return len(self._profiles)

    def _append(self, profile: Profile, turn: Turn) -> None:
        if not self.keep_history:
            return
        profile.history.append(turn)
        if len(profile.history) > self.max_history:
            del profile.history[: len(profile.history) - self.max_history]
