"""Official warnings: whether the national alerting authority has a warning in force for the person's area.

ACE passes on the authority's own headline and instruction, in the language the authority wrote it, inside a
short frame in the person's language. It says there is no warning only when it checked the official feed in
the last six hours. When the feed is old or unreachable, it says it cannot tell, and names the authority.
"""
from __future__ import annotations

import re

from .. import i18n
from ..connectors.cap import FEEDS, NO_FEED
from ..geo import in_bbox, in_polygons, ring_area_centroid
from ..snapshots import parse_time, utcnow
from ..text import fold
from .base import LANGS, Answer, Context, Query, Refusal, Result, all_langs, cite_snapshot, fit, needs_place, say, short_date

MIRROR_MAX_DAYS = 30
NATIONWIDE = ("countrywide", "nationwide", "whole country", "entire country", "all regions", "all counties",
              "tout le pays", "ensemble du territoire", "nchi nzima", "todo o pais", "todo o territorio", "kul al bilad",
              "جميع انحاء البلاد", "كل البلاد", "dalka oo dhan", "guutuu biyyaa", "መላው አገሪቱ")
# A polygon is treated as the authority's whole country, not a real footprint, when it spans this share of the
# country's bounding box. Some feeds attach a national outline to a local warning (a coastal storm in one town).
BROAD_SHARE = 0.8
MIN_RING_AREA = 1e-6  # square degrees: rings smaller than this are points or lines, not areas

NATIONAL = {"en": "Official warning for the whole country from {authority}, until {until}:",
            "sw": "Tahadhari rasmi kwa nchi nzima kutoka {authority}, hadi {until}:",
            "fr": "Alerte officielle pour tout le pays, jusqu'au {until} (source : {authority}) :"}
FOUND = {"en": "Official warning for {place} from {authority}, until {until}:",
         "sw": "Tahadhari rasmi kwa {place} kutoka {authority}, hadi {until}:",
         "fr": "Alerte officielle pour {place}, jusqu'au {until} (source : {authority}) :"}
MORE = {"en": "{n} more in force.", "sw": "Nyingine {n} zinaendelea.", "fr": "{n} autre(s) en vigueur."}
NONE = {"en": "No official warning from {authority} covers {place} right now (checked {checked}).",
        "sw": "Hakuna tahadhari rasmi kutoka {authority} kwa {place} kwa sasa (imekaguliwa {checked}).",
        "fr": "Aucune alerte officielle ne couvre {place} en ce moment (source : {authority}, vérifié le {checked})."}
STALE = {"en": "ACE could not check the {authority} warning feed recently, so it cannot tell if a warning is in force. "
               "Listen to official bulletins from {authority}.",
         "sw": "ACE haikuweza kukagua tahadhari za {authority} hivi karibuni, hivyo haiwezi kujua kama kuna tahadhari. "
               "Sikiliza {authority}.",
         "fr": "ACE n'a pas pu consulter récemment le flux d'alertes officiel (source : {authority}) et ne peut pas "
               "dire si une alerte est en vigueur. Écoutez les bulletins officiels à la radio."}
GAP = {"en": "{authority} does not publish an official warning feed that ACE can read, so ACE cannot check warnings "
             "there. Listen to official bulletins from {authority} on radio and TV.",
       "sw": "{authority} haichapishi tahadhari rasmi ambazo ACE inaweza kusoma, hivyo ACE haiwezi kukagua tahadhari "
             "huko. Sikiliza {authority} redioni na kwenye TV.",
       "fr": "{authority} ne publie pas de flux d'alertes officiel lisible par ACE, donc ACE ne peut pas vérifier les "
             "alertes. Écoutez les bulletins officiels à la radio et à la télévision."}


def tidy(text: str) -> str:
    """Keep the authority's words and drop only dashes, which read badly as one SMS line."""
    text = re.sub(r"\s*[\u2013\u2014]\s*", ". ", " ".join(text.split()))
    text = re.sub(r"([:.])\s*-\s*(?=\w)", r"\1 ", text)
    return re.sub(r"\s+-(?=\w)", "; ", text)


YOUR_AREA = {"en": "your area", "sw": "eneo lako", "fr": "votre zone", "pt": "a sua zona", "ar": "منطقتك",
             "am": "አካባቢዎ", "om": "naannoo kee", "so": "deegaankaaga"}


def clean_rings(polygons: list) -> list:
    """Rings that are real areas. Feeds sometimes send a polygon that is one point repeated, or a line."""
    out = []
    for ring in polygons or []:
        distinct = {(round(p[0], 4), round(p[1], 4)) for p in ring}
        if len(ring) >= 4 and len(distinct) >= 3 and abs(ring_area_centroid(ring)[0]) >= MIN_RING_AREA:
            out.append(ring)
    return out


def _share(ring: list, box: tuple[float, float, float, float]) -> float:
    lats, lons = [p[0] for p in ring], [p[1] for p in ring]
    south, west, north, east = max(min(lats), box[0]), max(min(lons), box[1]), min(max(lats), box[2]), min(max(lons), box[3])
    if north <= south or east <= west:
        return 0.0
    whole = (box[2] - box[0]) * (box[3] - box[1])
    return (north - south) * (east - west) / whole if whole > 0 else 0.0


def scope(alert: dict, place, places=None) -> str | None:
    """How an alert reaches a place: "polygon", "named", "national", or None when it does not.

    Polygons decide first, unless every polygon spans most of the country while the alert names specific areas:
    then the names decide, because the outline is the country's and not the warning's. An alert with no usable
    polygon is matched by the areas it names; one that names no area and says nationwide, or names only the
    country, covers everyone.
    """
    point = place.point
    rings = clean_rings(alert.get("polygons", []))
    words = " ".join([*alert.get("area_desc", []), alert.get("headline") or ""])
    named = places.named_in(words, place.country) if places is not None else set()
    box = places.country_box(place.country) if places is not None else None
    broad = bool(rings) and box is not None and all(_share(r, box) >= BROAD_SHARE for r in rings)
    if rings and not (broad and named):
        for ring in rings:
            lats, lons = [p[0] for p in ring], [p[1] for p in ring]
            if in_bbox(point, (min(lats), min(lons), max(lats), max(lons))) and in_polygons(point, [ring]):
                return "national" if broad else "polygon"
    if named:
        return "named" if place.code in named else None
    name = fold(place.name).replace("region", "").replace("county", "").strip()
    for desc in alert.get("area_desc", []):
        d = fold(desc)
        if any(fold(w) in d for w in NATIONWIDE):
            return "national"
        if name and len(name) > 2 and name in d:
            return "named"
    if not rings and _names_country(alert, place.country):
        return "national"
    return None


def _names_country(alert: dict, country: str) -> bool:
    from ..countries import COUNTRIES
    from .base import country_said
    names = {fold(COUNTRIES[country].name)} | {fold(country_said(country, lang)) for lang in LANGS}
    names |= {n.removeprefix("le ").removeprefix("la ").removeprefix("l'") for n in names}
    return any(fold(d).strip(" ()[]'.") in names or any(n and n in fold(d) for n in names if len(n) > 3)
               for d in alert.get("area_desc", []))


def applies(alert: dict, place, places=None) -> bool:
    """True when an alert's area covers the place."""
    return scope(alert, place, places) is not None


def when(value: str, lang: str) -> str:
    dt = parse_time(value)
    if dt is None:
        return value
    zone = " UTC" if dt.utcoffset() is not None and dt.utcoffset().total_seconds() == 0 else ""
    return f"{short_date(dt, lang)} {dt.strftime('%H:%M')}{zone}"


class WarningsService:
    id = "official_warnings"
    title = {"en": "Official warnings", "sw": "Tahadhari rasmi", "fr": "Alertes officielles",
             "pt": "Avisos oficiais", "ar": "التحذيرات الرسمية", "am": "ኦፊሴላዊ ማስጠንቀቂያዎች",
             "om": "Akeekkachiisa seeraa", "so": "Digniinaha rasmiga ah"}
    countries = frozenset(FEEDS)
    connectors = ("cap",)

    def coverage(self, country: str, ctx: Context) -> tuple[bool, str]:
        if country in NO_FEED:
            return False, f"{NO_FEED[country]} lists no CAP feed in the WMO register"
        snap = ctx.snapshots.get("warnings", country)
        if snap is None:
            return False, "feed not reachable at the last refresh"
        if self._mirror_only(snap, utcnow()):
            return False, "only an out of date mirror of the feed was reachable at the last refresh"
        return True, f"{FEEDS[country][0]} CAP feed"

    @staticmethod
    def _mirror_only(snap, now) -> bool:
        newest = parse_time(snap.meta.get("newest_item"))
        return snap.meta.get("primary") is False and (newest is None or (now - newest).days > MIRROR_MAX_DAYS)

    def answer(self, q: Query, ctx: Context) -> Result:
        country = (q.place.country if q.place else q.country) or ""
        if country in NO_FEED:
            return Refusal(self.id, "gap", all_langs(GAP, authority=NO_FEED[country]))
        if country not in FEEDS:
            return needs_place(self.id, q.country)
        authority = FEEDS[country][0]
        snap = ctx.snapshots.get("warnings", country)
        mirror_only = snap is not None and self._mirror_only(snap, q.now)
        if snap is None or not snap.is_valid(q.now) or mirror_only:
            # Only a stale mirror was reachable: ACE cannot say that no warning is in force.
            return Refusal(self.id, "stale", all_langs(STALE, authority=authority),
                           [cite_snapshot(snap)] if snap else [])
        live = [a for a in snap.records if (parse_time(a.get("expires")) or q.now) > q.now]
        if q.place is None:
            if not live:
                place = YOUR_AREA
                checked = parse_time(snap.retrieved_at)
                text = {lang: fit([say(NONE, lang, authority=authority, place=place[lang],
                                       checked=when(snap.retrieved_at, lang) if checked else "")], q.max_chars)
                        for lang in LANGS}
                return Answer(self.id, text, [cite_snapshot(snap)], confidence="high", data_date=snap.retrieved_at,
                              data={"alerts": [], "country": country})
            return needs_place(self.id, country)
        scopes = {id(a): scope(a, q.place, ctx.places) for a in live}
        mine = [a for a in live if scopes[id(a)]]
        if not mine:
            text = {lang: fit([say(NONE, lang, authority=authority, place=q.place.name,
                                   checked=when(snap.retrieved_at, lang))], q.max_chars) for lang in LANGS}
            return Answer(self.id, text, [cite_snapshot(snap)], confidence="high", data_date=snap.retrieved_at,
                          data={"alerts": [], "country": country, "place": q.place.name})
        mine.sort(key=lambda a: {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}.get(a.get("severity"), 4))
        top = mine[0]
        words = top.get("headline") or top.get("event")
        action = tidy(top.get("instruction") or top.get("description") or "")
        text = {}
        for lang in LANGS:
            frame = NATIONAL if scopes[id(top)] == "national" else FOUND
            pieces = [f"{say(frame, lang, place=q.place.name, authority=authority, until=when(top['expires'], lang))} "
                      f"{words}.", action]
            if len(mine) > 1:
                pieces.append(say(MORE, lang, n=len(mine) - 1))
            text[lang] = fit(pieces, q.max_chars)
        return Answer(
            self.id, text, [cite_snapshot(snap, f"{authority}: {words}")], confidence="high",
            data_date=snap.retrieved_at,
            data={"country": country, "place": q.place.name, "alerts": [
                {k: a.get(k) for k in ("id", "event", "headline", "severity", "urgency", "certainty", "onset",
                                       "expires", "area_desc", "instruction", "language", "url")} for a in mine]})


i18n.localize("services.warnings", globals(), ("FOUND", "NATIONAL", "MORE", "NONE", "STALE", "GAP"))
