"""Official warnings: whether the national alerting authority has a warning in force for the person's area.

ACE passes on the authority's own headline and instruction, in the language the authority wrote it, inside a
short frame in the person's language. It says there is no warning only when it checked the official feed in
the last six hours. When the feed is old or unreachable, it says it cannot tell, and names the authority.
"""
from __future__ import annotations

from ..connectors.cap import FEEDS, NO_FEED
from ..geo import in_bbox, in_polygons
from ..snapshots import parse_time, utcnow
from ..text import fold
from .base import LANGS, Answer, Context, Query, Refusal, Result, all_langs, cite_snapshot, fit, needs_place, say, short_date

MIRROR_MAX_DAYS = 30
NATIONWIDE = ("countrywide", "nationwide", "whole country", "entire country", "all regions", "all counties",
              "tout le pays", "ensemble du territoire", "nchi nzima")

FOUND = {"en": "Official warning for {place} from {authority}, until {until}:",
         "sw": "Tahadhari rasmi kwa {place} kutoka {authority}, hadi {until}:",
         "fr": "Alerte officielle pour {place} de {authority}, jusqu'au {until} :"}
MORE = {"en": "{n} more in force.", "sw": "Nyingine {n} zinaendelea.", "fr": "{n} autre(s) en vigueur."}
NONE = {"en": "No official warning from {authority} covers {place} right now (checked {checked}).",
        "sw": "Hakuna tahadhari rasmi kutoka {authority} kwa {place} kwa sasa (imekaguliwa {checked}).",
        "fr": "Aucune alerte officielle de {authority} ne couvre {place} en ce moment (vérifié le {checked})."}
STALE = {"en": "ACE could not check the {authority} warning feed recently, so it cannot tell if a warning is in force. "
               "Listen to {authority}.",
         "sw": "ACE haikuweza kukagua tahadhari za {authority} hivi karibuni, hivyo haiwezi kujua kama kuna tahadhari. "
               "Sikiliza {authority}.",
         "fr": "ACE n'a pas pu consulter récemment les alertes de {authority} et ne peut pas dire si une alerte est en "
               "vigueur. Écoutez {authority}."}
GAP = {"en": "{authority} does not publish an official warning feed that ACE can read, so ACE cannot check warnings "
             "there. Listen to {authority} on radio and TV.",
       "sw": "{authority} haichapishi tahadhari rasmi ambazo ACE inaweza kusoma, hivyo ACE haiwezi kukagua tahadhari "
             "huko. Sikiliza {authority} redioni na kwenye TV.",
       "fr": "{authority} ne publie pas de flux d'alertes officiel lisible par ACE, donc ACE ne peut pas vérifier les "
             "alertes. Écoutez {authority} à la radio et à la télévision."}


def applies(alert: dict, place) -> bool:
    """True when an alert's area covers the place: by its polygons, by naming it, or by covering the whole country."""
    point = place.point
    for ring in alert.get("polygons", []):
        lats, lons = [p[0] for p in ring], [p[1] for p in ring]
        if in_bbox(point, (min(lats), min(lons), max(lats), max(lons))) and in_polygons(point, [ring]):
            return True
    name = fold(place.name).replace("region", "").replace("county", "").strip()
    for desc in alert.get("area_desc", []):
        d = fold(desc)
        if any(w in d for w in NATIONWIDE) or (name and len(name) > 2 and name in d):
            return True
    return False


def when(value: str, lang: str) -> str:
    dt = parse_time(value)
    if dt is None:
        return value
    zone = " UTC" if dt.utcoffset() is not None and dt.utcoffset().total_seconds() == 0 else ""
    return f"{short_date(dt, lang)} {dt.strftime('%H:%M')}{zone}"


class WarningsService:
    id = "official_warnings"
    title = {"en": "Official warnings", "sw": "Tahadhari rasmi", "fr": "Alertes officielles"}
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
                place = {"en": "your area", "sw": "eneo lako", "fr": "votre zone"}
                checked = parse_time(snap.retrieved_at)
                text = {lang: fit([say(NONE, lang, authority=authority, place=place[lang],
                                       checked=when(snap.retrieved_at, lang) if checked else "")], q.max_chars)
                        for lang in LANGS}
                return Answer(self.id, text, [cite_snapshot(snap)], confidence="high", data_date=snap.retrieved_at,
                              data={"alerts": [], "country": country})
            return needs_place(self.id, country)
        mine = [a for a in live if applies(a, q.place)]
        if not mine:
            text = {lang: fit([say(NONE, lang, authority=authority, place=q.place.name,
                                   checked=when(snap.retrieved_at, lang))], q.max_chars) for lang in LANGS}
            return Answer(self.id, text, [cite_snapshot(snap)], confidence="high", data_date=snap.retrieved_at,
                          data={"alerts": [], "country": country, "place": q.place.name})
        mine.sort(key=lambda a: {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}.get(a.get("severity"), 4))
        top = mine[0]
        words = top.get("headline") or top.get("event")
        action = top.get("instruction") or top.get("description") or ""
        text = {}
        for lang in LANGS:
            pieces = [f"{say(FOUND, lang, place=q.place.name, authority=authority, until=when(top['expires'], lang))} "
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
