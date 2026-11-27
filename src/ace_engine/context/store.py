"""Find the facts that apply to one person, one place, one moment and one question.

Retrieval has two stages, both transparent:

1. Hard filters decide what is allowed: review status, tier, expiry, vertical,
   topic, subject, season and geography. A fact that fails a filter is never
   served, however relevant its words look.
2. Ranking orders what is left: BM25 text relevance first, then local
   specificity, review depth, season match and language availability.

The store is in memory. The interface is what matters: back it with a search
engine or a vector index in production without changing callers.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from ..models import GeoPoint
from ..text import terms
from .schema import ContextFact, ReviewStatus, Tier


@dataclass(frozen=True)
class ContextQuery:
    text: str | None = None
    topic: str | None = None
    vertical: str | None = None
    subject: str | None = None
    location: GeoPoint | None = None
    country: str | None = None
    admin_area: str | None = None
    month: int | None = None
    language: str | None = None
    prefer_kind: str | None = None  # "action" when the person asks what to do
    min_review: ReviewStatus = ReviewStatus.SOURCED
    include_verified: bool = False  # True only for callers entitled to the verified tier
    include_expired: bool = False
    today: date | None = None
    limit: int = 5


@dataclass(frozen=True)
class ScoredFact:
    fact: ContextFact
    score: float
    relevance: float = 0.0  # BM25 component alone, 0 when the query has no text


# Words for a phone number, which every fact that gives a country's lines answers, and words for an emergency, which
# its national emergency lines answer, in English, Swahili, French and Portuguese, whatever language its pack is in.
NUMBER_WORDS = "number numbers phone hotline helpline nambari namba simu numero numeros numéro numéros número números"
EMERGENCY_WORDS = "emergency urgence urgences emergencia emergência emergencias police policia polícia ambulance ambulancia"


@dataclass
class _Index:
    """A small BM25 index over each fact's searchable text."""

    k1: float = 1.4
    b: float = 0.75
    docs: dict[str, Counter[str]] = field(default_factory=dict)
    lengths: dict[str, int] = field(default_factory=dict)
    df: Counter[str] = field(default_factory=Counter)

    def add(self, fact: ContextFact) -> None:
        tf = Counter(terms(fact.search_text()))
        # keywords and subjects are what people actually type: weight them up
        for kw in (*fact.keywords, *fact.subjects):
            for t in terms(kw):
                tf[t] += 2
        # A fact that gives emergency lines answers a request for a number, so emergency numbers in Kenya finds the
        # national lines and not the M-PESA fraud line, whose text says numbers more often.
        if fact.topic == "emergency_contacts":
            for t in terms(NUMBER_WORDS):
                tf[t] += 2
            if any("emergency" in c.queues for c in fact.contacts):
                for t in terms(EMERGENCY_WORDS):
                    tf[t] += 2
        self.docs[fact.id] = tf
        self.lengths[fact.id] = sum(tf.values())
        self.df.update(tf.keys())

    def score(self, fact_id: str, query_terms: list[str]) -> float:
        tf = self.docs.get(fact_id)
        if not tf or not query_terms:
            return 0.0
        n = len(self.docs)
        avg = sum(self.lengths.values()) / max(1, n)
        length = self.lengths[fact_id]
        total = 0.0
        for t in set(query_terms):
            f = tf.get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))
            total += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / avg))
        return total


class ContextStore:
    def __init__(self) -> None:
        self._facts: dict[str, ContextFact] = {}
        self._index = _Index()

    def add(self, fact: ContextFact) -> None:
        if fact.id in self._facts:
            raise ValueError(f"Duplicate fact id: {fact.id}")
        self._facts[fact.id] = fact
        self._index.add(fact)

    def extend(self, facts: list[ContextFact] | tuple[ContextFact, ...]) -> None:
        for f in facts:
            self.add(f)

    def __len__(self) -> int:
        return len(self._facts)

    def __iter__(self):
        return iter(self._facts.values())

    def get(self, fact_id: str) -> ContextFact | None:
        return self._facts.get(fact_id)

    def topics(self, vertical: str | None = None) -> list[tuple[str, str]]:
        """Distinct (vertical, topic) pairs, for building menus."""
        pairs = {(f.vertical, f.topic) for f in self._facts.values()
                 if vertical is None or f.vertical == vertical}
        return sorted(pairs)

    def allowed(self, f: ContextFact, q: ContextQuery) -> bool:
        if f.tier is Tier.VERIFIED and not q.include_verified:
            return False
        if f.review_status.rank < q.min_review.rank:
            return False
        if not q.include_expired and f.is_expired(q.today):
            return False
        if q.vertical and f.vertical != q.vertical:
            return False
        if q.topic and f.topic != q.topic:
            return False
        if q.subject and f.subjects and q.subject.lower() not in f.subjects:
            return False
        if not f.applies_in_month(q.month):
            return False
        return f.scope.contains(q.location, q.country, q.admin_area)

    def query(self, q: ContextQuery) -> list[ScoredFact]:
        query_terms = terms(q.text) if q.text else []
        candidates = [f for f in self._facts.values() if self.allowed(f, q)]
        scored: list[ScoredFact] = []
        for f in candidates:
            rel = self._index.score(f.id, query_terms)
            if query_terms and rel <= 0:
                continue
            scored.append(ScoredFact(f, 0.0, rel))
        if not scored:
            return []
        top_rel = max(s.relevance for s in scored) or 1.0
        results = []
        for s in scored:
            f = s.fact
            norm = s.relevance / top_rel if query_terms else 0.0
            if query_terms and norm < 0.35:  # far weaker than the best match: off topic
                continue
            score = 4.0 * norm + 0.3 * f.review_status.rank + 0.4 * f.scope.specificity
            if f.months and q.month in f.months:
                score += 0.3
            if q.subject and f.subjects:
                score += 0.5
            if q.language and q.language in f.languages:
                score += 0.2
            if q.prefer_kind and f.kind == q.prefer_kind:
                score += 1.0
            results.append(ScoredFact(f, round(score, 4), round(s.relevance, 4)))
        results.sort(key=lambda s: (-s.score, s.fact.id))
        return results[: q.limit]
