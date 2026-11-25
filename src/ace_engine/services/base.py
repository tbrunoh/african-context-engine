"""The service contract. A decision service answers one named decision from snapshots and packs.

Services never touch the network. Each one returns an Answer, with text in every language ACE serves that
fits the channel, a citation for every fact, the date of its data and one next step; or a Refusal that says
why it cannot answer safely and who to ask instead. Every V2 service is a preview until it passes the launch
gate in docs/v2/build-plan.md, and every answer says so in its metadata.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol

from .. import i18n
from ..models import Citation, GeoPoint
from ..places import Gazetteer, Place
from ..snapshots import Snapshot, SnapshotStore, parse_time, utcnow
from ..text import SUPPORTED_LANGUAGES, truncate_words

if TYPE_CHECKING:
    from ..context.store import ContextStore
    from ..safety import Contact

LANGS = SUPPORTED_LANGUAGES
Text = dict[str, str]

DAYS: dict[str, tuple[str, ...]] = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "sw": ("Jumatatu", "Jumanne", "Jumatano", "Alhamisi", "Ijumaa", "Jumamosi", "Jumapili"),
    "fr": ("lun", "mar", "mer", "jeu", "ven", "sam", "dim"),
}
MONTHS: dict[str, tuple[str, ...]] = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "sw": ("Jan", "Feb", "Machi", "Apr", "Mei", "Juni", "Julai", "Ago", "Sep", "Okt", "Nov", "Des"),
    "fr": ("janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"),
}


def day_name(d: date, lang: str) -> str:
    return DAYS.get(lang, DAYS["en"])[d.weekday()]


def short_date(d: date | datetime, lang: str) -> str:
    return f"{d.day} {MONTHS.get(lang, MONTHS['en'])[d.month - 1]}"


def month_year(ym: str, lang: str) -> str:
    y, m = ym[:7].split("-")
    return f"{MONTHS.get(lang, MONTHS['en'])[int(m) - 1]} {y}"


def say(templates: dict[str, str], lang: str, **values: Any) -> str:
    text = (templates.get(lang) or templates["en"]).format(**values)
    return french(text) if lang == "fr" else text


def all_langs(templates: dict[str, str], **values: Any) -> Text:
    return {lang: say(templates, lang, **values) for lang in LANGS}


def fit(pieces: list[str], limit: int) -> str:
    """Join pieces in order, keeping the first one always and adding each later one only if it fits."""
    if not pieces:
        return ""
    text = truncate_words(pieces[0], limit)
    for piece in pieces[1:]:
        if piece and len(f"{text} {piece}") <= limit:
            text = f"{text} {piece}"
    return text


@dataclass
class Query:
    text: str = ""
    country: str | None = None
    language: str = "en"
    place: Place | None = None
    location: GeoPoint | None = None
    max_chars: int = 1500
    now: datetime = field(default_factory=utcnow)
    params: dict[str, Any] = field(default_factory=dict)  # structured inputs, for example weeks or crop


@dataclass
class Answer:
    service: str
    text: Text                                    # per language, already inside the channel budget
    citations: list[Citation]
    confidence: Literal["high", "medium", "low"] = "medium"
    next_step: Text | None = None
    data_date: str | None = None
    preview: bool = True
    data: dict[str, Any] = field(default_factory=dict)  # structured result for the API and MCP


@dataclass
class Refusal:
    service: str
    reason: str                                   # machine readable: needs_place, gap, stale, no_match
    text: Text
    citations: list[Citation] = field(default_factory=list)
    preview: bool = True
    data: dict[str, Any] = field(default_factory=dict)


Result = Answer | Refusal


@dataclass
class Context:
    """What a service may read: snapshots, places, packs and the country's verified numbers."""

    snapshots: SnapshotStore
    places: Gazetteer
    store: ContextStore | None = None
    numbers: Any = None  # callable(queue, country) -> list[Contact]

    def contacts(self, queue: str, country: str | None) -> list[Contact]:
        return list(self.numbers(queue, country)) if self.numbers and country else []


class Service(Protocol):
    id: str
    title: Text
    countries: frozenset[str]
    connectors: tuple[str, ...]

    def coverage(self, country: str, ctx: Context) -> tuple[bool, str]: ...
    def answer(self, q: Query, ctx: Context) -> Result: ...


def cite_snapshot(snap: Snapshot, label: str | None = None) -> Citation:
    return Citation(fact_id=f"snapshot:{snap.dataset}/{snap.country}", source=label or snap.source,
                    review_status="preview", source_url=snap.source_url, licence=snap.licence,
                    date=snap.data_date or snap.retrieved_at[:10])


def cite_fact(fact: Any) -> Citation:
    return Citation(fact.id, fact.source, fact.review_status.value, fact.source_url, date=fact.checked_on)


def snapshot_age_hours(snap: Snapshot, now: datetime) -> float:
    return (now - (parse_time(snap.retrieved_at) or now)).total_seconds() / 3600


NEEDS_PLACE = {
    "en": "Which {area} are you in? Reply with its name, for example {example}.",
    "sw": "Uko {area} gani? Jibu kwa jina lake, kwa mfano {example}.",
    "fr": "Indiquez votre {area}, par exemple {example}.",
}
AREA_WORD = {
    "en": {"KE": "county", "NG": "state", "UG": "district", "TZ": "region", "GH": "region", "SN": "region",
           "CI": "district", "TG": "region", "RW": "province", "ZA": "province", "BW": "district", "NA": "region",
           "ZW": "province", "CD": "province", "MW": "district", "BI": "province", "CM": "region",
           "BJ": "department", "ZM": "province", "TD": "province", "GN": "region", "BF": "region", "SS": "state",
           "ET": "region", "MZ": "province", "GW": "region", "AO": "province", "SO": "region", "SD": "state",
           "DZ": "province", "EG": "governorate", "LY": "district", "MA": "region", "TN": "governorate"},
    "sw": {"KE": "kaunti", "UG": "wilaya", "TZ": "mkoa", "CD": "jimbo", "BI": "mkoa"},
    "fr": {"SN": "région", "CI": "district", "TG": "région", "RW": "province", "CD": "province", "BI": "province",
           "CM": "région", "BJ": "département", "TD": "province", "GN": "région", "BF": "région", "DZ": "wilaya",
           "MA": "région", "TN": "gouvernorat"},
}
AREA_DEFAULT = {"en": "area", "sw": "eneo", "fr": "région"}
# Country names as a sentence says them: Swahili, and French with its article (pour la Namibie, pour le Ghana).
COUNTRY_SAID: dict[str, dict[str, str]] = {
    "en": {},  # English says the country's own name, from countries.py
    "sw": {"KE": "Kenya", "TZ": "Tanzania", "UG": "Uganda", "RW": "Rwanda", "ZA": "Afrika Kusini", "BW": "Botswana",
           "NA": "Namibia", "ZW": "Zimbabwe", "NG": "Nigeria", "GH": "Ghana", "SN": "Senegal", "CI": "Côte d'Ivoire",
           "TG": "Togo", "CD": "Kongo DR", "MW": "Malawi", "BI": "Burundi", "CM": "Kameruni", "BJ": "Benin",
           "ZM": "Zambia", "TD": "Chad", "GN": "Guinea", "BF": "Burkina Faso", "SS": "Sudan Kusini",
           "ET": "Ethiopia", "MZ": "Msumbiji", "GW": "Guinea-Bissau", "AO": "Angola", "SO": "Somalia",
           "SD": "Sudan", "DZ": "Algeria", "EG": "Misri", "LY": "Libya", "MA": "Morocco", "TN": "Tunisia"},
    "fr": {"KE": "le Kenya", "TZ": "la Tanzanie", "UG": "l'Ouganda", "RW": "le Rwanda", "ZA": "l'Afrique du Sud",
           "BW": "le Botswana", "NA": "la Namibie", "ZW": "le Zimbabwe", "NG": "le Nigeria", "GH": "le Ghana",
           "SN": "le Sénégal", "CI": "la Côte d'Ivoire", "TG": "le Togo", "CD": "la République démocratique du Congo",
           "MW": "le Malawi", "BI": "le Burundi", "CM": "le Cameroun", "BJ": "le Bénin", "ZM": "la Zambie",
           "TD": "le Tchad", "GN": "la Guinée", "BF": "le Burkina Faso", "SS": "le Soudan du Sud",
           "ET": "l'Éthiopie", "MZ": "le Mozambique", "GW": "la Guinée-Bissau", "AO": "l'Angola",
           "SO": "la Somalie", "SD": "le Soudan", "DZ": "l'Algérie", "EG": "l'Égypte", "LY": "la Libye",
           "MA": "le Maroc", "TN": "la Tunisie"},
}


def country_said(code: str, lang: str) -> str:
    from ..countries import COUNTRIES
    return COUNTRY_SAID.get(lang, {}).get(code) or COUNTRIES[code].name


def french(text: str) -> str:
    """French elides de before a vowel: à 123 km d'Embu, not de Embu."""
    return re.sub(r"\bde (?=[AEIOUYÉÈÊÂÎaeiouyéèêâî])", "d'", text)


EXAMPLE_PLACE = {"KE": "Embu", "TZ": "Mwanza", "UG": "Gulu", "RW": "Kigali", "ZA": "Gauteng", "BW": "Central District",
                 "NA": "Khomas", "ZW": "Masvingo", "NG": "Kano", "GH": "Ashanti", "SN": "Thiès", "CI": "Abidjan",
                 "TG": "Kara", "CD": "Kinshasa", "MW": "Lilongwe", "BI": "Gitega", "CM": "Littoral", "BJ": "Borgou",
                 "ZM": "Lusaka", "TD": "Logone Oriental", "GN": "Kankan", "BF": "Kadiogo", "SS": "Central Equatoria",
                 "ET": "Amhara", "MZ": "Nampula", "GW": "Bafatá", "AO": "Huíla", "SO": "Banadir", "SD": "Khartoum",
                 "DZ": "Alger", "EG": "Assiut", "LY": "Tripoli", "MA": "Fez Meknes", "TN": "Sfax"}


def area_word(country: str | None, lang: str) -> str:
    default = AREA_DEFAULT.get(lang) or AREA_DEFAULT["en"]
    return AREA_WORD.get(lang, {}).get(country or "", AREA_WORD["en"].get(country or "", default) if lang == "en"
                                        else default)


def needs_place(service: str, country: str | None) -> Refusal:
    return Refusal(service, "needs_place", {
        lang: say(NEEDS_PLACE, lang, area=area_word(country, lang), example=EXAMPLE_PLACE.get(country or "", "Kano"))
        for lang in LANGS})


i18n.localize("services.base", globals(), ("DAYS", "MONTHS", "NEEDS_PLACE", "AREA_WORD", "AREA_DEFAULT", "COUNTRY_SAID"))
