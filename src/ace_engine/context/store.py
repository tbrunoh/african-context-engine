"""Query the knowledge graph for the facts that apply to one person, place and moment."""
from __future__ import annotations

from dataclasses import dataclass

from ..models import GeoPoint
from .schema import ContextFact, ReviewStatus, Tier


@dataclass(frozen=True)
class ContextQuery:
    topic: str | None = None
    vertical: str | None = None
    subject: str | None = None
    location: GeoPoint | None = None
    country: str | None = None
    admin_area: str | None = None
    month: int | None = None
    language: str | None = None
    min_review: ReviewStatus = ReviewStatus.DRAFT
    include_verified: bool = False  # True only for callers entitled to the verified tier
    limit: int = 5


@dataclass(frozen=True)
class ScoredFact:
    fact: ContextFact
    score: float


class ContextStore:
    """An in-memory store. The interface is what matters: back it with a graph or
    vector database in production without changing callers."""

    def __init__(self) -> None:
        self._facts: dict[str, ContextFact] = {}

    def add(self, fact: ContextFact) -> None:
        if fact.id in self._facts:
            raise ValueError(f"Duplicate fact id: {fact.id}")
        self._facts[fact.id] = fact

    def extend(self, facts: list[ContextFact]) -> None:
        for f in facts:
            self.add(f)

    def __len__(self) -> int:
        return len(self._facts)

    def get(self, fact_id: str) -> ContextFact | None:
        return self._facts.get(fact_id)

    def query(self, q: ContextQuery) -> list[ScoredFact]:
        results: list[ScoredFact] = []
        for f in self._facts.values():
            if f.tier is Tier.VERIFIED and not q.include_verified:
                continue
            if f.review_status.rank < q.min_review.rank:
                continue
            if q.vertical and f.vertical != q.vertical:
                continue
            if q.topic and f.topic != q.topic:
                continue
            if q.subject and f.subjects and q.subject.lower() not in {s.lower() for s in f.subjects}:
                continue
            if not f.applies_in_month(q.month):
                continue
            if not f.scope.contains(q.location, q.country, q.admin_area):
                continue
            results.append(ScoredFact(f, self._score(f, q)))
        results.sort(key=lambda s: (-s.score, s.fact.id))
        return results[: q.limit]

    @staticmethod
    def _score(f: ContextFact, q: ContextQuery) -> float:
        """More specific and better reviewed facts rank first."""
        score = 1.0 + f.review_status.rank
        s = f.scope
        if s.center is not None and s.radius_km is not None:
            score += 1.5
        if s.altitude_min_m is not None or s.altitude_max_m is not None:
            score += 1.0
        if s.admin_areas:
            score += 0.75
        if s.countries:
            score += 0.25
        if f.months:
            score += 0.5
        if q.subject and f.subjects:
            score += 0.5
        if q.language and q.language in f.languages:
            score += 0.25
        return score
