"""V2 decision services, and the hub that routes a question to the right one.

The hub runs after the safety rail, commands and Scam Shield, and before retrieval from packs, exactly as the
V2 build plan sets out. It recognises what a person is deciding (rain, warnings, a facility, prices, a
pregnancy check, a crop problem), works out where they are, and asks for the place when it needs one.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..countries import COUNTRIES
from ..models import GeoPoint
from ..places import Gazetteer, Place
from ..snapshots import SnapshotStore, utcnow
from ..text import contains_phrase, tokens, truncate_words
from .base import LANGS, Answer, Context, Query, Refusal, Result, Service
from .facility import FacilityService
from .pests import PestService, crop_in
from .pregnancy import PregnancyService, weeks_from
from .prices import PricesService, wanted_food
from .rain import RainService
from .warnings import WarningsService

SERVICES: dict[str, Service] = {s.id: s for s in (
    RainService(), WarningsService(), FacilityService(), PricesService(), PregnancyService(), PestService())}

# Words that show what a person is deciding, in English, Swahili and French. Phrases match whole words.
CUES: dict[str, tuple[str, ...]] = {
    "pregnancy_companion": ("antenatal", "anc", "prenatal", "prénatal", "prenatale", "kliniki ya ujauzito",
                            "clinic visit", "next check", "visite prenatale", "consultation prenatale"),
    "nearest_facility": ("hospital", "hospitals", "clinic", "health centre", "health center", "dispensary",
                         "health facility", "hospitali", "zahanati", "kituo cha afya", "hopital", "hôpital",
                         "clinique", "centre de sante", "dispensaire", "nearest doctor"),
    "official_warnings": ("warning", "warnings", "alert", "alerts", "flood warning", "storm", "cyclone",
                          "tahadhari", "onyo", "alerte", "alertes", "vigilance"),
    "rain_this_week": ("rain", "rains", "raining", "weather", "forecast", "mvua", "hali ya hewa", "utabiri",
                       "pluie", "pluies", "meteo", "météo", "pleuvoir", "pleut", "prevision"),
    "market_prices": ("price", "prices", "cost", "market", "bei", "soko", "prix", "marche", "marché", "combien coute"),
    "pest_check": ("pest", "pests", "disease", "worm", "worms", "insects", "sick", "dying", "leaves", "yellow",
                   "holes", "wilt", "wilting", "ugonjwa", "wadudu", "viwavi", "majani", "njano", "matundu",
                   "maladie", "ravageur", "ravageurs", "insectes", "feuilles", "jaune", "trous", "chenille"),
}
SEASONAL = ("long rains", "short rains", "rainy season", "rain season", "seasons", "season", "masika", "vuli",
            "msimu", "saison des pluies", "saison")
PREGNANT = ("pregnant", "pregnancy", "mjamzito", "ujauzito", "mimba", "enceinte", "grossesse")
PLACE_SERVICES = {"rain_this_week", "official_warnings", "nearest_facility", "market_prices"}


def detect(text: str) -> str | None:
    """The service a message is about, or None to fall through to pack retrieval."""
    if not tokens(text):
        return None
    if any(contains_phrase(text, c) for c in CUES["pregnancy_companion"]) or (
            weeks_from(text) is not None and any(contains_phrase(text, p) for p in PREGNANT)):
        return "pregnancy_companion"
    for sid in ("nearest_facility", "official_warnings", "rain_this_week", "market_prices"):
        if any(contains_phrase(text, c) for c in CUES[sid]):
            if sid == "rain_this_week" and any(contains_phrase(text, c) for c in SEASONAL):
                continue  # a question about the rainy seasons, which the season packs answer
            return sid
    if wanted_food(text) and any(contains_phrase(text, c) for c in ("how much", "bei gani", "combien")):
        return "market_prices"
    if crop_in(text) and any(contains_phrase(text, c) for c in CUES["pest_check"]):
        return "pest_check"
    return None


@dataclass
class ServiceResult:
    service: str
    result: Result
    place: Place | None

    @property
    def ok(self) -> bool:
        return isinstance(self.result, Answer)

    def text(self, lang: str) -> str:
        texts = self.result.text
        return texts.get(lang) or texts["en"]


class ServiceHub:
    def __init__(self, snapshots: SnapshotStore, store: Any = None, numbers: Any = None) -> None:
        self.snapshots = snapshots
        self.places = Gazetteer(snapshots)
        self.ctx = Context(snapshots, self.places, store, numbers)
        self.clock = utcnow  # replaceable, so tests and replays run at a fixed time

    def resolve_place(self, text: str, country: str | None, location: GeoPoint | None = None,
                      remembered: tuple[str, str] | None = None) -> Place | None:
        if country:
            found = self.places.find(text, country)
            if found:
                return found
        if location is not None:
            found = self.places.locate(location.lat, location.lon, country)
            if found:
                return found
        if remembered and (not country or remembered[0] == country):
            return self.places.by_code(*remembered)
        return None

    def run(self, service_id: str, text: str, country: str | None, language: str, max_chars: int,
            location: GeoPoint | None = None, remembered: tuple[str, str] | None = None,
            params: dict[str, Any] | None = None, place: Place | None = None) -> ServiceResult:
        service = SERVICES[service_id]
        place = place or self.resolve_place(text, country, location, remembered)
        q = Query(text=text, country=country or (place.country if place else None),
                  language=language if language in LANGS else "en", place=place, location=location,
                  max_chars=max_chars, now=self.clock(), params=dict(params or {}))
        result = service.answer(q, self.ctx)
        if isinstance(result, Refusal):  # refusals fit the channel too
            result.text = {lang: truncate_words(t, max_chars) for lang, t in result.text.items()}
        return ServiceResult(service_id, result, place)

    def call(self, service_id: str, country: str | None = None, place: str | None = None, lat: float | None = None,
             lon: float | None = None, language: str = "en", text: str = "", params: dict[str, Any] | None = None,
             max_chars: int = 1500) -> dict[str, Any]:
        """One service call as plain JSON, for the web API and the MCP server."""
        if service_id not in SERVICES:
            raise ValueError("unknown service, one of " + ", ".join(SERVICES))
        country = (country or "").upper() or None
        if country and country not in COUNTRIES:
            raise ValueError("country must be one of " + ", ".join(COUNTRIES))
        location = GeoPoint(float(lat), float(lon)) if lat is not None and lon is not None else None
        if location is not None and country is None:
            found = self.places.locate(location.lat, location.lon)
            country = found.country if found else None
        resolved = self.places.find(place, country) if place and country else None
        run = self.run(service_id, " ".join(filter(None, [text, place])), country, language, max_chars,
                       location=location, params=params, place=resolved)
        r = run.result
        return {
            "service": service_id, "outcome": "answer" if run.ok else r.reason, "preview": r.preview,
            "language": language, "text": run.text(language), "text_all": r.text,
            "place": None if run.place is None else {"country": run.place.country, "code": run.place.code,
                                                     "name": run.place.name},
            "citations": [c.__dict__ for c in r.citations], "data": r.data,
            "data_date": getattr(r, "data_date", None), "confidence": getattr(r, "confidence", None),
        }

    def coverage(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Service by country: whether ACE can answer there, and why not when it cannot."""
        out: dict[str, dict[str, dict[str, Any]]] = {}
        for sid, service in SERVICES.items():
            out[sid] = {}
            for code in COUNTRIES:
                ok, detail = service.coverage(code, self.ctx)
                out[sid][code] = {"available": ok, "detail": detail}
        return out


__all__ = ["PLACE_SERVICES", "SERVICES", "Answer", "Context", "Query", "Refusal", "ServiceHub", "ServiceResult", "detect"]
