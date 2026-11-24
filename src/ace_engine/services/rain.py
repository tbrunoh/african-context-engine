"""Rain this week: the chance of rain each day for the person's area, in plain words.

Built on the ECMWF ensemble (51 runs). A day is likely wet when at least 6 runs in 10 give 1 mm or more,
possible from 3 in 10, and unlikely below that. Heavy rain (20 mm or more) is mentioned when at least 3 runs
in 10 give it. The forecast is for the centre of the area, so the answer names the area and the forecast date.
"""
from __future__ import annotations

from datetime import date

from ..countries import COUNTRIES
from .base import (
    LANGS,
    Answer,
    Context,
    Query,
    Refusal,
    Result,
    all_langs,
    cite_snapshot,
    day_name,
    fit,
    needs_place,
    say,
    short_date,
)

LIKELY, POSSIBLE, HEAVY = 0.6, 0.3, 0.3

WORDS = {
    "likely": {"en": "likely", "sw": "inatarajiwa", "fr": "probable"},
    "possible": {"en": "possible", "sw": "huenda", "fr": "possible"},
    "dry": {"en": "mostly dry", "sw": "kavu zaidi", "fr": "plutôt sec"},
}
HEAD = {"en": "Rain near {place}:", "sw": "Mvua {place}:", "fr": "Pluie à {place} :"}
HEAVY_LINE = {"en": "Heavy rain (20 mm or more) possible {days}.", "sw": "Mvua kubwa (mm 20 au zaidi) huenda {days}.",
              "fr": "Fortes pluies (20 mm ou plus) possibles {days}."}
FOOT = {"en": "Chances from the ECMWF forecast of {date}.", "sw": "Uwezekano kutoka utabiri wa ECMWF wa {date}.",
        "fr": "Probabilités de la prévision ECMWF du {date}."}
SPAN = {"en": "{a} to {b}", "sw": "{a} hadi {b}", "fr": "{a} à {b}"}
AND = {"en": "and", "sw": "na", "fr": "et"}
STALE = {
    "en": "ACE has no current forecast for {place}. Check the {met} forecast.",
    "sw": "ACE haina utabiri wa sasa wa {place}. Angalia utabiri wa {met}.",
    "fr": "ACE n'a pas de prévision à jour pour {place}. Consultez la prévision de {met}.",
}
NEXT = {"en": "Plan field work for the drier days.", "sw": "Panga kazi za shambani siku zisizo na mvua.",
        "fr": "Prévoyez les travaux des champs pour les jours plus secs."}

MET_SERVICE = {"KE": "Kenya Meteorological Department", "TZ": "Tanzania Meteorological Authority",
               "UG": "Uganda Department of Meteorological Services", "RW": "Rwanda Meteorology Agency",
               "ZA": "South African Weather Service", "BW": "Botswana Meteorological Services",
               "NA": "Namibia Meteorological Service", "ZW": "Zimbabwe Meteorological Services Department",
               "NG": "Nigerian Meteorological Agency", "GH": "Ghana Meteorological Agency", "SN": "ANACIM",
               "CI": "SODEXAM", "TG": "Météo Togo"}


def classify(p_wet: float) -> str:
    return "likely" if p_wet >= LIKELY else "possible" if p_wet >= POSSIBLE else "dry"


def group(days: list[tuple[date, str]]) -> list[tuple[str, date, date]]:
    """Runs of consecutive days with the same class."""
    runs: list[tuple[str, date, date]] = []
    for d, cls in days:
        if runs and runs[-1][0] == cls:
            runs[-1] = (cls, runs[-1][1], d)
        else:
            runs.append((cls, d, d))
    return runs


def span(a: date, b: date, lang: str) -> str:
    return day_name(a, lang) if a == b else say(SPAN, lang, a=day_name(a, lang), b=day_name(b, lang))


def join_days(days: list[date], lang: str) -> str:
    names = [day_name(d, lang) for d in days]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {AND[lang]} {names[-1]}"


class RainService:
    id = "rain_this_week"
    title = {"en": "Rain this week", "sw": "Mvua wiki hii", "fr": "Pluie cette semaine"}
    countries = frozenset(COUNTRIES)
    connectors = ("open_meteo", "boundaries")

    def coverage(self, country: str, ctx: Context) -> tuple[bool, str]:
        snap = ctx.snapshots.get("weather", country)
        if snap is None:
            return False, "no forecast snapshot yet"
        return True, f"ECMWF ensemble for {len(snap.records)} areas"

    def answer(self, q: Query, ctx: Context) -> Result:
        if q.place is None:
            return needs_place(self.id, q.country)
        place, country = q.place, q.place.country
        snap = ctx.snapshots.get("weather", country)
        rec = next((r for r in (snap.records if snap else []) if r["code"] == place.code), None)
        met = MET_SERVICE.get(country, "national met service")
        if snap is None or rec is None or not snap.is_valid(q.now):
            return Refusal(self.id, "stale", all_langs(STALE, place=place.name, met=met),
                           [cite_snapshot(snap)] if snap else [])
        today = q.now.date()
        days = [(date.fromisoformat(d[0]), d) for d in rec["days"] if date.fromisoformat(d[0]) >= today][:7]
        if not days:
            return Refusal(self.id, "stale", all_langs(STALE, place=place.name, met=met), [cite_snapshot(snap)])
        runs = group([(d, classify(row[1])) for d, row in days])
        heavy = [d for d, row in days if row[3] >= HEAVY]
        run_date = date.fromisoformat(snap.retrieved_at[:10])
        text = {}
        for lang in LANGS:
            body = "; ".join(f"{WORDS[cls][lang]} {span(a, b, lang)}" for cls, a, b in runs)
            pieces = [f"{say(HEAD, lang, place=place.name)} {body}."]
            if heavy:
                pieces.append(say(HEAVY_LINE, lang, days=join_days(heavy, lang)))
            pieces.append(say(FOOT, lang, date=short_date(run_date, lang)))
            text[lang] = fit(pieces, q.max_chars)
        wet = sum(1 for _, row in days if row[1] >= LIKELY)
        return Answer(
            self.id, text, [cite_snapshot(snap)], confidence="medium",
            next_step=all_langs(NEXT) if wet else None, data_date=snap.data_date,
            data={"place": {"code": place.code, "name": place.name, "country": country},
                  "days": [{"date": d.isoformat(), "chance_of_rain": row[1], "median_mm": row[2],
                            "chance_of_heavy_rain": row[3], "outlook": classify(row[1])} for d, row in days],
                  "forecast_retrieved": snap.retrieved_at, "valid_until": snap.valid_until,
                  "model": snap.meta.get("model")})
