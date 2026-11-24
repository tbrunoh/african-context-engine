"""The context fact: the unit of local knowledge every ACE answer is grounded in."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from ..models import GeoPoint


class ReviewStatus(str, Enum):
    """How far a fact has travelled through the contribution pipeline.

    draft             submitted, not yet checked; never served unless a deployment opts in
    sourced           a maintainer checked the claim against the cited public source
    expert_reviewed   a named domain expert reviewed the claim for this place
    outcome_verified  confirmed by measured outcomes from real deployments
    """

    DRAFT = "draft"
    SOURCED = "sourced"
    EXPERT_REVIEWED = "expert_reviewed"
    OUTCOME_VERIFIED = "outcome_verified"

    @property
    def rank(self) -> int:
        return _RANK[self.value]


_RANK = {"draft": 0, "sourced": 1, "expert_reviewed": 2, "outcome_verified": 3}


class Tier(str, Enum):
    """Open facts ship under CC BY 4.0. Verified facts may carry other terms."""

    OPEN = "open"
    VERIFIED = "verified"


@dataclass(frozen=True)
class GeoScope:
    """Where a fact applies. Any field left empty means no constraint on that axis."""

    countries: tuple[str, ...] = ()        # ISO 3166-1 alpha-2, for example ("KE",)
    admin_areas: tuple[str, ...] = ()      # counties, states or districts, for example ("Nyeri",)
    center: GeoPoint | None = None
    radius_km: float | None = None
    altitude_min_m: float | None = None
    altitude_max_m: float | None = None

    def contains(self, point: GeoPoint | None, country: str | None = None,
                 admin_area: str | None = None) -> bool:
        if self.countries and country and country.upper() not in self.countries:
            return False
        if self.admin_areas and admin_area and admin_area.lower() not in {a.lower() for a in self.admin_areas}:
            return False
        if point is not None:
            if (self.center is not None and self.radius_km is not None
                    and haversine_km(point, self.center) > self.radius_km):
                return False
            if point.altitude_m is not None:
                if self.altitude_min_m is not None and point.altitude_m < self.altitude_min_m:
                    return False
                if self.altitude_max_m is not None and point.altitude_m > self.altitude_max_m:
                    return False
        return True

    @property
    def specificity(self) -> float:
        """Higher for narrower scopes, so local facts outrank national ones."""
        score = 0.0
        if self.center is not None and self.radius_km is not None:
            score += 1.5
        if self.altitude_min_m is not None or self.altitude_max_m is not None:
            score += 1.0
        if self.admin_areas:
            score += 0.75
        if self.countries:
            score += 0.25
        return score


@dataclass(frozen=True)
class Rendering:
    """A fact in one language: the full claim and a short form for USSD and SMS."""

    claim: str
    short: str | None = None
    reviewed: bool = False  # True once a fluent speaker has checked this rendering


@dataclass(frozen=True)
class Contact:
    """A phone line or short code people can reach, for emergency and referral facts."""

    label: str
    number: str
    queues: tuple[str, ...] = ()           # safety queues this line serves, for example ("gbv",)
    free: bool | None = None
    hours: str | None = None


@dataclass(frozen=True)
class ContextFact:
    id: str
    claim: str
    topic: str                             # for example "pest", "storage", "fraud", "danger_signs"
    vertical: str                          # "agriculture", "health", "finance", "safety", "legal"
    kind: str = "info"                     # "action" (what to do), "sign" (how to recognise), "info"
    scope: GeoScope = field(default_factory=GeoScope)
    subjects: tuple[str, ...] = ()         # crops, conditions or services, for example ("maize",)
    keywords: tuple[str, ...] = ()         # words people actually use, in any language
    months: tuple[int, ...] = ()           # 1 to 12; empty means all year
    short: str | None = None               # at most 160 characters, for USSD and SMS
    translations: dict[str, Rendering] = field(default_factory=dict)
    language: str = "en"                   # language of claim and short
    contacts: tuple[Contact, ...] = ()
    source: str = ""
    source_url: str | None = None
    checked_on: str | None = None          # ISO date the claim was last checked against its source
    reviewed_by: str | None = None
    review_status: ReviewStatus = ReviewStatus.DRAFT
    tier: Tier = Tier.OPEN
    expires: str | None = None             # ISO date after which the fact is withheld until re-reviewed
    safety_critical: bool = False          # answers using this fact always point to human help
    pack_id: str = ""

    def applies_in_month(self, month: int | None) -> bool:
        return not self.months or month is None or month in self.months

    def is_expired(self, today: date | None = None) -> bool:
        if not self.expires:
            return False
        return date.fromisoformat(self.expires) < (today or date.today())

    def render(self, language: str | None, short: bool = False) -> tuple[str, str]:
        """Return (text, language_used), falling back to the fact's own language."""
        if language and language != self.language and language in self.translations:
            r = self.translations[language]
            return ((r.short or r.claim) if short else r.claim), language
        return ((self.short or self.claim) if short else self.claim), self.language

    @property
    def languages(self) -> tuple[str, ...]:
        return (self.language, *sorted(self.translations))

    def search_text(self) -> str:
        parts = [self.claim, self.short or "", self.topic.replace("_", " "), " ".join(self.subjects),
                 " ".join(self.keywords)]
        for r in self.translations.values():
            parts.extend([r.claim, r.short or ""])
        return " ".join(parts)


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    r = 6371.0088
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
