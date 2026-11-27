"""Places: the first level areas of every covered country, so a person can name where they are.

Most people on a basic phone cannot share a GPS position. They can say Embu,
Kano, Thiès or Mwanza. The gazetteer turns either a typed place name or a
position into one area of one country, read from the places snapshots built
from geoBoundaries. Uganda uses its districts, because its four regions are
too large to be useful; every other country uses its first level areas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .geo import distance_to_rings_km, in_bbox, in_polygons
from .snapshots import SnapshotStore
from .text import ETHIOPIC_PREFIXES, fold, tokens

# Arabic in, to, and, as, joined to the article: بالقاهرة is in Cairo.
ARABIC_PREFIXES = "بلوفك"

GENERIC_WORDS = frozenset(
    "county region state province district division municipality city town wilaya mkoa kaunti jimbo "
    "wilayani region departement département province etat".split())


@dataclass(frozen=True)
class Place:
    country: str
    code: str
    name: str
    level: str
    lat: float
    lon: float

    @property
    def point(self) -> tuple[float, float]:
        return self.lat, self.lon


def _key(name: str) -> str:
    return " ".join(t for t in tokens(name) if t not in GENERIC_WORDS)


class Gazetteer:
    def __init__(self, snapshots: SnapshotStore) -> None:
        self.snapshots = snapshots
        self._areas: dict[str, list[dict]] = {}

    def areas(self, country: str) -> list[dict]:
        country = country.upper()
        if country not in self._areas:
            snap = self.snapshots.get("places", country)
            records = [dict(r) for r in snap.records] if snap else []
            # Aliases added since the snapshot was built count at once, without waiting for the next refresh.
            from .connectors.boundaries import ALIASES
            for rec in records:
                for source, extra in ALIASES.get(country, {}).items():
                    if source == rec.get("name") or source in rec.get("aliases", ()):
                        rec["aliases"] = [*rec.get("aliases", ()), *(a for a in extra if a not in rec.get("aliases", ()))]
            self._areas[country] = records
        return self._areas[country]

    def has(self, country: str | None) -> bool:
        return bool(country) and bool(self.areas(country))

    @staticmethod
    def _place(country: str, rec: dict) -> Place:
        return Place(country.upper(), rec["code"], rec["name"], rec.get("level", "ADM1"),
                     rec["centroid"][0], rec["centroid"][1])

    def find(self, text: str, country: str | None) -> Place | None:
        """The area named in a message, longest name first, within the caller's country."""
        if not country or not text:
            return None
        words = tokens(text)
        # Also each word without a prefix that means in or at: Shona muHarare, isiZulu eThekwini spelt eThekwini or
        # ethekwini, Amharic በአዲስ አበባ (in Addis Ababa).
        # A Bantu prefix is set aside only when the name after it is capitalised, as in muHarare: kutanga is a word,
        # not Tanga.
        capped = {fold(m) for m in re.findall(r"\b(?:mu|ku|pa|kwa)([A-Z][\w']+)", text)}
        bare = [next((c for c in capped if w.endswith(c) and len(w) - len(c) <= 3), _bare(w)) for w in words]
        hays = (" " + " ".join(words) + " ", " " + " ".join(bare) + " ")
        best: tuple[int, dict] | None = None
        for rec in self.areas(country):
            for name in [rec["name"], *rec.get("aliases", [])]:
                key = _key(name)
                if key and any(f" {key} " in hay for hay in hays) and (best is None or len(key) > best[0]):
                    best = (len(key), rec)
        return self._place(country, best[1]) if best else None

    def by_code(self, country: str, code: str) -> Place | None:
        for rec in self.areas(country):
            if rec["code"] == code:
                return self._place(country, rec)
        return None

    def locate(self, lat: float, lon: float, country: str | None = None,
               max_km: float = 25.0) -> Place | None:
        """The area that contains a position; failing that, the area whose edge is nearest, within max_km."""
        from .countries import COUNTRIES

        codes = [country.upper()] if country else list(COUNTRIES)
        point = (lat, lon)
        nearest: tuple[float, str, dict] | None = None
        for code in codes:
            for rec in self.areas(code):
                if not in_bbox(point, rec["bbox"], pad=1.0):
                    continue
                if in_bbox(point, rec["bbox"], pad=0.01) and in_polygons(point, rec["rings"]):
                    return self._place(code, rec)
                d = distance_to_rings_km(point, rec["rings"])
                if nearest is None or d < nearest[0]:
                    nearest = (d, code, rec)
        if nearest and nearest[0] <= max_km:  # just outside every shape, for example on the coast
            return self._place(nearest[1], nearest[2])
        return None

    def rings(self, country: str, code: str) -> list:
        for rec in self.areas(country):
            if rec["code"] == code:
                return rec["rings"]
        return []

    def names(self, country: str) -> list[str]:
        return sorted(rec["name"] for rec in self.areas(country))

    def country_box(self, country: str) -> tuple[float, float, float, float] | None:
        """The bounding box of every area in a country: south, west, north, east."""
        boxes = [rec["bbox"] for rec in self.areas(country) if rec.get("bbox")]
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))

    def named_in(self, text: str, country: str) -> set[str]:
        """Codes of the areas a text names, by official name or alias, as whole words."""
        from .text import phrase_in, token_hay
        hay = token_hay(text)
        found: set[str] = set()
        for rec in self.areas(country):
            for name in (rec["name"], *rec.get("aliases", ())):
                if len(fold(name)) > 2 and phrase_in(hay, name):
                    found.add(rec["code"])
                    break
        return found


def _bare(word: str) -> str:
    """A word without an Arabic or Amharic prefix that means in or at: القاهرة for بالقاهرة, አዲስ for በአዲስ."""
    if len(word) > 3 and word[0] in ARABIC_PREFIXES and word[1:3] == "ال":
        return word[1:]
    if len(word) > 2 and word[0] in ETHIOPIC_PREFIXES:
        return word[1:]
    return word


def same_name(a: str, b: str) -> bool:
    return _key(a) == _key(b) or fold(a) == fold(b)
