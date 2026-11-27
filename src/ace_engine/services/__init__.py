"""V2 decision services, and the hub that routes a question to the right one.

The hub runs after the safety rail, commands and Scam Shield, and before retrieval from packs, exactly as the
V2 build plan sets out. It recognises what a person is deciding (rain, warnings, a facility, prices, a
pregnancy check, a crop problem), works out where they are, and asks for the place when it needs one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .. import i18n
from ..countries import COUNTRIES
from ..models import GeoPoint
from ..places import Gazetteer, Place
from ..snapshots import SnapshotStore, utcnow
from ..text import phrase_in, token_hay, tokens, truncate_words
from .base import (
    AREA_DEFAULT,
    AREA_WORD,
    COUNTRY_SAID,
    DAYS,
    LANGS,
    MONTHS,
    Answer,
    Context,
    Query,
    Refusal,
    Result,
    Service,
    needs_place,
)
from .facility import FacilityService
from .pests import PestService, crop_in
from .pregnancy import PregnancyService, weeks_from
from .prices import PricesService, wanted_food
from .rain import RainService
from .warnings import WarningsService

SERVICES: dict[str, Service] = {s.id: s for s in (
    RainService(), WarningsService(), FacilityService(), PricesService(), PregnancyService(), PestService())}

# Words that show what a person is deciding, in English, Swahili and French here and every added language through
# its locale file. Phrases match whole words.
CUES: dict[str, tuple[str, ...]] = {
    "pregnancy_companion": ("antenatal", "anc", "prenatal", "prénatal", "prenatale", "kliniki ya ujauzito",
                            "clinic visit", "next check", "visite prenatale", "consultation prenatale"),
    "nearest_facility": ("hospital", "hospitals", "clinic", "health centre", "health center", "dispensary",
                         "health facility", "hospitali", "zahanati", "kituo cha afya", "hopital", "hôpital",
                         "clinique", "centre de sante", "dispensaire", "nearest doctor"),
    "official_warnings": ("warning", "warnings", "alert", "alerts", "flood warning", "storm", "cyclone",
                          "tahadhari", "onyo", "alerte", "alertes", "vigilance"),
    "rain_this_week": ("rain", "rains", "raining", "weather", "forecast", "mvua", "hali ya hewa", "utabiri",
                       "pluie", "pluies", "meteo", "météo", "pleuvoir", "pleut", "prevision", "quel temps", "temps fera",
                       "temps qu il fera", "temps qu il fait"),
    "market_prices": ("price", "prices", "cost", "market", "bei", "soko", "prix", "marche", "marché", "combien coute"),
    "pest_check": ("pest", "pests", "disease", "worm", "worms", "insects", "sick", "dying", "leaves", "yellow",
                   "holes", "wilt", "wilting", "ugonjwa", "wadudu", "viwavi", "majani", "njano", "matundu",
                   "maladie", "ravageur", "ravageurs", "insectes", "feuilles", "jaune", "trous", "chenille"),
}
SEASONAL = ("long rains", "short rains", "rainy season", "rain season", "seasons", "season", "masika", "vuli",
            "msimu", "saison des pluies", "saison")
PREGNANT = ("pregnant", "pregnancy", "mjamzito", "ujauzito", "mimba", "enceinte", "grossesse")
CUES = {sid: i18n.phrases(f"services.CUES.{sid}", words) for sid, words in CUES.items()}
SEASONAL = i18n.phrases("services.SEASONAL", SEASONAL)
PREGNANT = i18n.phrases("services.PREGNANT", PREGNANT)
HOW_MUCH = i18n.phrases("services.HOW_MUCH", ("how much", "bei gani", "combien"))
PLACE_SERVICES = {"rain_this_week", "official_warnings", "nearest_facility", "market_prices"}


# A word that says where comes before a place name: in Kano, à Thiès, em Huíla, huko Mwanza, katika Embu, في سوهاج.
# The next words name a place unless they are a determiner, a number, a time or a word ACE already reads as a
# service, a month, a day or an area. Markers that are also common words elsewhere (Swahili na, Portuguese no, the
# English article a) are left out, so they never make a place out of an ordinary word.
_WHERE = re.compile(r"(?:^|(?<=[\s,.;:!?(]))(in|at|near|around|à|au|aux|dans|près de|pres de|vers|em|perto de|huko|katika|"
                    r"karibu na|mjini|kwenye|ndani ya|في|قرب)\s+([^\s,.;:!?()]+(?:\s+[^\s,.;:!?()]+){0,2})", re.I)
_NOT_A_NAME = frozenset(tokens(
    "the a an my our your his her their this that these those here there me us you it which what where some any "
    "every all one two three le la les l un une des du de mon ma mes notre nos votre vos ce cette ces ici o os as "
    "um uma meu minha nosso nossa este esta esse essa aqui hii huu hiki hapa kwangu kwetu yangu yetu wangu "
    "هذا هذه منطقتي مدينتي قريتي هنا"))
_COMMON = frozenset(tokens(
    "today tomorrow tonight yesterday now soon week weeks weekend month months year years morning afternoon evening "
    "night day days hour hours minutes time future advance general total case need emergency english french swahili "
    "home town city village area region county district province state country place places africa farm field "
    "fields school work office church mosque shop shops kg kilo kilos bulk detail details short season "
    "aujourd hui demain semaine semaines mois annee matin soir nuit jour jours ville village maison zone pays "
    "province region quartier champ ecole travail general francais anglais hoje amanha semana semanas mes ano "
    "manha tarde noite dia dias cidade aldeia casa zona regiao provincia pais campo escola trabalho geral leo "
    "kesho wiki mwezi mwaka asubuhi jioni usiku siku mji kijiji nyumbani eneo mkoa kaunti wilaya nchi shamba "
    "shule kazi kanisa msikiti duka اسبوع يوم غد غدا شهر سنة صباح مساء ليل مدينة قرية بيت منطقة بلد "
    "january february march april may june july august september october november december janvier fevrier mars "
    "avril mai juin juillet aout septembre octobre novembre decembre janeiro fevereiro marco abril maio junho julho "
    "agosto setembro outubro novembro dezembro januari februari machi aprili mei juni julai agosti septemba oktoba "
    "novemba desemba monday tuesday wednesday thursday friday saturday sunday plenty particular addition order front "
    "sight fact spite touch trouble danger "
    "back middle between shilling shillings naira cedi cedis franc francs cfa rand kwacha birr dollar dollars usd "
    "kes tzs ugx pula dalasi leones kwanza meticais metical dinar dinars pounds pound cash money bulk "
    "mimi mim moi chez labour labor partir venir coming next northern southern eastern western central nord sud est "
    "ouest ksh kshs tsh frw fcfa kwanzas kenyan nigerian ghanaian ugandan tanzanian rwandan senegalese ethiopian "
    "somali sudanese egyptian moroccan english french swahili kiswahili kingereza anglais francais portugues ingles "
    "arabic amharic hausa yoruba igbo zulu xhosa afrikaans shona wolof lingala kipindi wholesale retail effect "
    "general future past present local town centre center"))
_EXTRA: set[str] = set()


def add_known_words(words: Any) -> None:
    """Words the packs list for what people ask about (keywords and subjects, in every language): never a place."""
    for word in words:
        _EXTRA.update(tokens(str(word)))


def _known_word(word: str) -> bool:
    if word.isdigit() or len(word) < 3 or word in _COMMON or word in _NOT_A_NAME or word in _EXTRA:
        return True
    return word in _vocabulary()


def _written_small(word: str) -> bool:
    """A word in a cased script typed without a capital: an everyday word rather than a name ACE should ask about.
    Scripts with no capitals, such as Arabic and Ge'ez, are judged by the word lists alone."""
    first = word[:1]
    return first.lower() != first.upper() and not first.isupper()


_VOCAB: set[str] | None = None


def _vocabulary() -> set[str]:
    """Every word of the service cues, months, days, area words and country names, in every language ACE has."""
    global _VOCAB
    if _VOCAB is None:
        words: set[str] = set()
        for group in (*CUES.values(), SEASONAL, PREGNANT, HOW_MUCH):
            for phrase in group:
                words.update(tokens(phrase))
        for table in (MONTHS, DAYS):
            for names in table.values():
                for name in names:
                    words.update(tokens(name))
        for table in AREA_WORD.values():
            for name in table.values():
                words.update(tokens(name))
        for name in AREA_DEFAULT.values():
            words.update(tokens(name))
        for table in COUNTRY_SAID.values():
            for name in table.values():
                words.update(tokens(name))
        for country in COUNTRIES.values():
            words.update(tokens(country.name))
        for code in (*i18n.locales(), "en", "sw", "fr"):  # language names: in Kiswahili is not a place
            words.update(tokens(i18n.native_name(code)) + tokens(i18n.english_name(code)))
        _VOCAB = words
    return _VOCAB


def unknown_place(text: str) -> str | None:
    """A place the message names after a word for where, as typed, when it is not an everyday word.

    The hub asks this only after the gazetteer found no area in the message, so whatever it returns is a place ACE
    does not know in the caller's country, such as a town smaller than an area, a place in another country or a
    misspelling. Answering for the last place named instead would answer a different question without saying so."""
    for match in _WHERE.finditer(text):
        raw = match.group(2).split()
        words = [tokens(w) for w in raw]
        if not words[0] or _written_small(raw[0]) or words[0][0] in _NOT_A_NAME or _known_word(words[0][0]):
            continue
        name = [raw[0]]
        for word, folded in zip(raw[1:], words[1:], strict=True):
            if not folded or _written_small(word) or _known_word(folded[0]):
                break
            name.append(word)
        return " ".join(name).strip("'\"«»“”")
    return None


_REPLIES = frozenset(tokens(
    "yes no ok okay thanks thank you please hello hi hey asante sawa ndio ndiyo hapana jambo habari merci oui non "
    "bonjour salut sim nao obrigado ola"))
# Words a follow-up adds to a place name: What about Nakuru? And in Lagos? Et à Kolda ? Je, Nakuru?
_FOLLOW = frozenset(tokens(
    "what about and how in at for there then also too whats et a au aux en pour quoi de la le les na je vipi huko "
    "kwa nini e em no para sobre ya ni"))


def bare_name(text: str) -> str | None:
    """A reply of one to three words that is not an everyday word: a place name ACE could not find, as typed."""
    raw = text.strip(" ?.!,;:'\"«»“”")
    words = raw.split()
    if not 1 <= len(words) <= 3 or _written_small(words[0]):
        return None
    for word in words:
        folded = tokens(word)
        if not folded or folded[0] in _REPLIES or _known_word(folded[0]):
            return None
    return raw


def needs_named_place(service: str, country: str | None, name: str) -> Refusal:
    """Ask for the area again, starting with the name ACE could not place, so the caller sees why."""
    refusal = needs_place(service, country)
    refusal.text = {lang: f"{name}? {text}" for lang, text in refusal.text.items()}
    refusal.data = {**(refusal.data or {}), "unknown_place": name}
    return refusal


def detect(text: str) -> str | None:
    """The service a message is about, or None to fall through to pack retrieval."""
    if not tokens(text):
        return None
    hay = token_hay(text)
    if any(phrase_in(hay, c) for c in CUES["pregnancy_companion"]) or (
            weeks_from(text) is not None and any(phrase_in(hay, p) for p in PREGNANT)):
        return "pregnancy_companion"
    for sid in ("nearest_facility", "official_warnings", "rain_this_week", "market_prices"):
        if any(phrase_in(hay, c) for c in CUES[sid]):
            if sid == "rain_this_week" and any(phrase_in(hay, c) for c in SEASONAL):
                continue  # a question about the rainy seasons, which the season packs answer
            return sid
    if wanted_food(text) and any(phrase_in(hay, c) for c in HOW_MUCH):
        return "market_prices"
    if crop_in(text) and any(phrase_in(hay, c) for c in CUES["pest_check"]):
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

    def follow_up_place(self, text: str, country: str | None) -> Place | None:
        """The place a short follow-up names, when it adds nothing else: What about Nakuru? Et à Kolda ?"""
        place = self.places.find(text, country) if country else None
        if place is None:
            return None
        named: set[str] = set()
        for rec in self.places.areas(place.country):
            if rec["code"] == place.code:
                for name in (rec["name"], *rec.get("aliases", ())):
                    named.update(tokens(name))
        rest = [t for t in tokens(text) if t not in named and t not in _FOLLOW]
        return None if rest else place

    @staticmethod
    def follow_up_unknown(text: str) -> str | None:
        """The place a short follow-up names that ACE does not know: And in Gotham?"""
        name = unknown_place(text)
        if not name:
            return None
        rest = [t for t in tokens(text) if t not in set(tokens(name)) and t not in _FOLLOW]
        return None if rest else name

    def run(self, service_id: str, text: str, country: str | None, language: str, max_chars: int,
            location: GeoPoint | None = None, remembered: tuple[str, str] | None = None,
            params: dict[str, Any] | None = None, place: Place | None = None) -> ServiceResult:
        service = SERVICES[service_id]
        if place is None and location is None and country and service_id in PLACE_SERVICES \
                and self.places.has(country) and self.places.find(text, country) is None:
            named = unknown_place(text)
            if named:
                refusal = needs_named_place(service_id, country, named)
                refusal.text = {lang: truncate_words(t, max_chars) for lang, t in refusal.text.items()}
                return ServiceResult(service_id, refusal, None)
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
