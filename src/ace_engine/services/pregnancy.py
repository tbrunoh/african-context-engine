"""Pregnancy companion: when the next antenatal check is due, and when to go now.

Built on WHO's 2016 antenatal care schedule (eight contacts) and the V1 maternal danger signs pack. Any danger
sign in the message has already gone through the safety rail before this service runs, so this service
handles the routine question and always repeats the signs that mean go now, with the country's numbers.
"""
from __future__ import annotations

import re

from .. import i18n
from ..countries import COUNTRIES
from ..text import fold
from .base import LANGS, Answer, Context, Query, Refusal, Result, cite_fact, fit, say

CONTACTS = (12, 20, 26, 30, 34, 36, 38, 40)
WEEK_WORDS = i18n.phrases("services.pregnancy.WEEK_WORDS", ("weeks", "week", "wks", "wk", "semaines", "semaine", "sem",
                                                           "wiki"))
MONTH_WORDS = i18n.phrases("services.pregnancy.MONTH_WORDS", ("months", "month", "mois", "miezi", "mwezi"))


def _pattern(words: tuple[str, ...], digits: str) -> re.Pattern:
    """A number then the word (22 weeks, 22 ሳምንት), or the word then the number (wiki ya 22, torban 22)."""
    alt = "|".join(sorted({re.escape(fold(w)) for w in words}, key=len, reverse=True))
    return re.compile(rf"({digits})\s*(?:{alt})\b|(?<!\w)(?:{alt})\s*(?:\w{{1,3}}\s+)?({digits})(?!\d)")


_WEEKS = _pattern(WEEK_WORDS, r"\d{1,2}")
_MONTHS = _pattern(MONTH_WORDS, r"\d")

FIRST = {"en": "At {w} weeks, go for your first antenatal check now, before 12 weeks.",
         "sw": "Ukiwa na wiki {w}, nenda kliniki ya kwanza ya ujauzito sasa, kabla ya wiki 12.",
         "fr": "À {w} semaines, faites votre première visite prénatale maintenant, avant 12 semaines."}
DUE_NOW = {"en": "At {w} weeks, an antenatal check is due now. The next is at {next} weeks.",
           "sw": "Ukiwa na wiki {w}, kliniki ya ujauzito inastahili sasa. Inayofuata ni wiki ya {next}.",
           "fr": "À {w} semaines, une visite prénatale est prévue maintenant. La suivante est à {next} semaines."}
NEXT = {"en": "At {w} weeks, your next antenatal check is due at {next} weeks.",
        "sw": "Ukiwa na wiki {w}, kliniki yako ijayo ya ujauzito ni wiki ya {next}.",
        "fr": "À {w} semaines, votre prochaine visite prénatale est prévue à {next} semaines."}
LATE = {"en": "At {w} weeks you are past the last planned check at 40 weeks. See a health worker today.",
        "sw": "Ukiwa na wiki {w} umepita kliniki ya mwisho ya wiki 40. Muone mhudumu wa afya leo.",
        "fr": "À {w} semaines, vous avez dépassé la dernière visite prévue à 40 semaines. Voyez un agent de santé aujourd'hui."}
ASK = {"en": "How many weeks pregnant are you? Reply with a number, for example 22 weeks.",
       "sw": "Una ujauzito wa wiki ngapi? Jibu kwa namba, kwa mfano wiki 22.",
       "fr": "De combien de semaines êtes-vous enceinte ? Répondez par un nombre, par exemple 22 semaines."}
CALL = {"en": "Call {numbers}.", "sw": "Piga {numbers}.", "fr": "Appelez le {numbers}."}


def weeks_from(text: str) -> int | None:
    t = fold(text)
    m = _WEEKS.search(t)
    if m:
        w = int(m.group(1) or m.group(2))
        return w if 1 <= w <= 45 else None
    m = _MONTHS.search(t)
    if m:
        months = int(m.group(1) or m.group(2))
        return round(months * 4.35) if 1 <= months <= 10 else None
    return None


class PregnancyService:
    id = "pregnancy_companion"
    title = {"en": "Pregnancy companion", "sw": "Mwongozo wa ujauzito", "fr": "Suivi de grossesse",
             "pt": "Acompanhamento da gravidez", "ar": "متابعة الحمل", "am": "የእርግዝና ክትትል",
             "om": "Hordoffii ulfaa", "so": "Daryeelka uurka"}
    countries = frozenset(COUNTRIES)
    connectors = ()

    def coverage(self, country: str, ctx: Context) -> tuple[bool, str]:
        return True, "WHO antenatal schedule and danger signs; national numbers from the V1 packs"

    def _fact(self, ctx: Context, fact_id: str):
        return ctx.store.get(fact_id) if ctx.store is not None else None

    def answer(self, q: Query, ctx: Context) -> Result:
        bare = q.text.strip()
        weeks = q.params.get("weeks") or weeks_from(q.text) or (int(bare) if bare.isdigit() and 1 <= int(bare) <= 45
                                                                 else None)
        schedule = self._fact(ctx, "africa-antenatal-care/eight-contacts")
        danger = self._fact(ctx, "africa-maternal-danger-signs/go-now")
        country = q.place.country if q.place else q.country
        numbers = ", ".join(dict.fromkeys(c.number for c in ctx.contacts("maternal", country)))
        text = {}
        for lang in LANGS:
            if weeks is None:
                lead = say(ASK, lang)
            elif weeks < 12:
                lead = say(FIRST, lang, w=weeks)
            elif weeks > 40:
                lead = say(LATE, lang, w=weeks)
            elif weeks in CONTACTS:
                nxt = next((c for c in CONTACTS if c > weeks), None)
                lead = say(DUE_NOW, lang, w=weeks, next=nxt) if nxt else say(DUE_NOW, lang, w=weeks, next=40).split(". ")[0] + "."
            else:
                lead = say(NEXT, lang, w=weeks, next=next(c for c in CONTACTS if c > weeks))
            pieces = [lead]
            if danger is not None:
                pieces.append(danger.render(lang, short=True)[0] + (f" {say(CALL, lang, numbers=numbers)}" if numbers else ""))
            if schedule is not None:
                pieces.append(schedule.render(lang, short=True)[0])
            text[lang] = fit(pieces, q.max_chars)
        cites = [cite_fact(f) for f in (schedule, danger) if f is not None]
        if weeks is None:
            return Refusal(self.id, "needs_weeks", text, cites, data={"schedule_weeks": list(CONTACTS)})
        nxt = None if weeks is None or weeks > 40 else next((c for c in CONTACTS if c > weeks or (weeks < 12 and c == 12)), None)
        return Answer(self.id, text, cites, confidence="high", data_date="2016-11-07",
                      data={"weeks": weeks, "next_check_week": nxt, "schedule_weeks": list(CONTACTS),
                            "numbers": numbers.split(", ") if numbers else []})


i18n.localize("services.pregnancy", globals(), ("FIRST", "DUE_NOW", "NEXT", "LATE", "ASK", "CALL"))
