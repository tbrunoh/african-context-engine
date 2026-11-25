"""Nearest health facility: the public facilities closest to the person, with type and distance.

The source lists public facilities only, dates from 2019, and has no phone numbers, hours or services, so the
answer says exactly that and ends with the country's verified medical emergency number from the V1 packs. Where
no pack publishes one (Togo today), it tells the person to call the local emergency number and never guesses one.
"""
from __future__ import annotations

from ..countries import COUNTRIES
from ..geo import haversine_km, in_bbox, in_polygons
from ..text import fold
from .base import LANGS, Answer, Context, Query, Refusal, Result, cite_snapshot, fit, needs_place, say

HOSPITAL_WORDS = ("hospital", "hopital", "chu ", "chr ", "chd ", "chu", "chr", "referral")
MAX_KM = 60.0

NEAR = {"en": "Nearest public facilities:", "sw": "Vituo vya afya vya umma vilivyo karibu:",
        "fr": "Établissements publics les plus proches :"}
IN_AREA = {"en": "Public hospitals in {place}:", "sw": "Hospitali za umma {place}:", "fr": "Hôpitaux publics à {place} :"}
CAVEAT = {"en": "From a 2019 list of public facilities; check it is open before you travel.",
          "sw": "Kutoka orodha ya vituo vya umma ya 2019; hakikisha kiko wazi kabla ya kusafiri.",
          "fr": "D'après une liste de 2019 des établissements publics ; vérifiez qu'il est ouvert avant de partir."}
EMERGENCY = {"en": "Emergency: {numbers}.", "sw": "Dharura: {numbers}.", "fr": "Urgence : {numbers}."}
NO_NUMBER = {"en": "In an emergency, call your local emergency number.",
             "sw": "Ikiwa ni dharura, piga nambari ya dharura ya eneo lako.",
             "fr": "En cas d'urgence, appelez le numéro d'urgence local."}
NONE = {"en": "ACE found no public facility within {km} km in its 2019 list.",
        "sw": "ACE haikupata kituo cha umma ndani ya km {km} katika orodha yake ya 2019.",
        "fr": "ACE n'a trouvé aucun établissement public à moins de {km} km dans sa liste de 2019."}
GAP = {"en": "ACE has no facility list for this country yet.",
       "sw": "ACE bado haina orodha ya vituo kwa nchi hii.",
       "fr": "ACE n'a pas encore de liste d'établissements pour ce pays."}
KM = {"en": "{km} km", "sw": "km {km}", "fr": "{km} km"}


def emergency_numbers(ctx: Context, country: str) -> list[str]:
    """Medical emergency numbers first, then general ones. Empty when no pack publishes any: never a guess."""
    found = [c.number for c in ctx.contacts("health_urgent", country)]
    found += [c.number for c in ctx.contacts("emergency", country)]
    return list(dict.fromkeys(found))


def emergency_line(numbers: list[str], lang: str) -> str:
    return say(EMERGENCY, lang, numbers=", ".join(numbers)) if numbers else say(NO_NUMBER, lang)


def with_numbers(template: dict[str, str], numbers: list[str], **kw) -> dict[str, str]:
    return {lang: f"{say(template, lang, **kw)} {emergency_line(numbers, lang)}" for lang in LANGS}


# Larger hospitals first when ACE lists hospitals in an area: referral and teaching, then regional, then district.
TIERS = (("national", "universit", "teaching", "referral", "chu"),
         ("regional", "provincial", "central", "intermediate", "chr", "level 5"),
         ("general", "county", "district", "prefectoral", "chd", "level 4"))


def tier(kind: str) -> int:
    k = fold(kind)
    return next((i for i, words in enumerate(TIERS) if any(w in k for w in words)), len(TIERS))


def is_hospital(kind: str) -> bool:
    k = f" {fold(kind)} "
    return any(w in k for w in HOSPITAL_WORDS)


def label(f: list, km: float | None, lang: str) -> str:
    dist = "" if km is None else f", {say(KM, lang, km=f'{km:.0f}' if km >= 2 else f'{km:.1f}')}"
    return f"{f[0]} ({f[1].lower()}{dist})"


class FacilityService:
    id = "nearest_facility"
    title = {"en": "Nearest health facility", "sw": "Kituo cha afya kilicho karibu", "fr": "Centre de santé proche"}
    countries = frozenset(COUNTRIES)
    connectors = ("public_health_facilities",)

    def coverage(self, country: str, ctx: Context) -> tuple[bool, str]:
        snap = ctx.snapshots.get("facilities", country)
        return (True, f"{len(snap.records)} public facilities, 2019 list") if snap else (False, "no facility list")

    def answer(self, q: Query, ctx: Context) -> Result:
        country = (q.place.country if q.place else q.country) or ""
        numbers = emergency_numbers(ctx, country) if country else []
        snap = ctx.snapshots.get("facilities", country) if country else None
        if q.location is None and q.place is None:
            return needs_place(self.id, q.country)
        if snap is None:
            return Refusal(self.id, "gap", with_numbers(GAP, numbers))
        facilities = snap.records
        if q.location is not None:
            origin = (q.location.lat, q.location.lon)
            ranked = sorted(((haversine_km(origin, (f[4], f[5])), f) for f in facilities), key=lambda t: t[0])
            near = [t for t in ranked if t[0] <= MAX_KM][:3]
            hospital = next((t for t in ranked if is_hospital(t[1][1]) and t[0] <= MAX_KM), None)
            if hospital and hospital not in near:
                near = near[:2] + [hospital]
            if not near:
                return Refusal(self.id, "no_match", with_numbers(NONE, numbers, km=int(MAX_KM)), [cite_snapshot(snap)])
            head, items = NEAR, [(f, km) for km, f in near]
        else:
            rings = ctx.places.rings(country, q.place.code)
            inside = [f for f in facilities if rings and in_polygons((f[4], f[5]), rings)]
            hospitals = [f for f in inside if is_hospital(f[1])]
            if hospitals:
                head, items = IN_AREA, [(f, None) for f in sorted(hospitals, key=lambda f: (tier(f[1]), f[0]))[:3]]
            else:
                origin = q.place.point
                ranked = sorted(((haversine_km(origin, (f[4], f[5])), f) for f in facilities
                                 if in_bbox((f[4], f[5]), (origin[0] - 1, origin[1] - 1, origin[0] + 1, origin[1] + 1))),
                                key=lambda t: t[0])[:3]
                if not ranked:
                    return Refusal(self.id, "no_match", with_numbers(NONE, numbers, km=int(MAX_KM)),
                                   [cite_snapshot(snap)])
                head, items = NEAR, [(f, km) for km, f in ranked]
        text = {}
        for lang in LANGS:
            listing = "; ".join(label(f, km, lang) for f, km in items)
            place = q.place.name if q.place else ""
            text[lang] = fit([f"{say(head, lang, place=place)} {listing}.", emergency_line(numbers, lang),
                              say(CAVEAT, lang)], q.max_chars)
        return Answer(
            self.id, text, [cite_snapshot(snap)], confidence="medium", data_date=snap.data_date,
            data={"country": country, "facilities": [
                {"name": f[0], "type": f[1], "ownership": f[2], "admin1": f[3], "lat": f[4], "lon": f[5],
                 "distance_km": None if km is None else round(km, 1)} for f, km in items],
                "emergency_numbers": numbers})
