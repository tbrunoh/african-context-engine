"""The context fact: the unit of hyperlocal knowledge ACE grounds every answer in."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..models import GeoPoint


class ReviewStatus(str, Enum):
    """How far a fact has travelled through the contribution pipeline."""

    DRAFT = "draft"                        # submitted by the community, not yet reviewed
    EXPERT_REVIEWED = "expert_reviewed"    # checked by a named domain expert
    OUTCOME_VERIFIED = "outcome_verified"  # confirmed by results from real sessions

    @property
    def rank(self) -> int:
        return {"draft": 0, "expert_reviewed": 1, "outcome_verified": 2}[self.value]


class Tier(str, Enum):
    """Open facts ship under CC BY 4.0. Verified facts carry commercial terms."""

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
        if self.admin_areas and admin_area and admin_area not in self.admin_areas:
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


@dataclass(frozen=True)
class ContextFact:
    id: str
    claim: str
    topic: str                             # for example "pest", "soil", "market", "maternal_health", "land"
    vertical: str                          # "agriculture", "health", "legal", "finance"
    scope: GeoScope = field(default_factory=GeoScope)
    subjects: tuple[str, ...] = ()         # crops, livestock, conditions, for example ("maize",)
    months: tuple[int, ...] = ()           # 1 to 12; empty means all year
    languages: tuple[str, ...] = ()        # languages a localized rendering exists for
    source: str = ""
    reviewed_by: str | None = None
    review_status: ReviewStatus = ReviewStatus.DRAFT
    tier: Tier = Tier.OPEN
    expires: str | None = None             # ISO date after which the fact needs re-review
    safety_critical: bool = False          # answers using this fact always offer human escalation

    def applies_in_month(self, month: int | None) -> bool:
        return not self.months or month is None or month in self.months


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    r = 6371.0088
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
